"""Klien Pakasir API v2 (QRIS) — server-side saja, tanpa dependensi eksternal.

Dokumentasi resmi: https://pakasir.com/p/create-transaction (v2).
API v1 berhenti 20 Oktober 2026, jadi modul ini HANYA memakai v2.

Prinsip keamanan:
- Host dikunci ke ``settings.PAKASIR_BASE_URL`` (https://app.pakasir.com);
  tidak ada URL yang bisa dikendalikan pengguna → tidak ada SSRF.
- API key hanya dikirim lewat header ``X-Api-Key`` (v1 menaruhnya di query
  string sehingga bocor ke access log). Tidak pernah ditulis ke log,
  URL, template, atau pesan error.
- Redirect HTTP tidak diikuti (http.client tidak mengikuti redirect),
  respons dibatasi ukurannya, dan timeout eksplisit.
- ``create_payment`` bersifat *find or create* di sisi Pakasir: memanggil
  ulang dengan order_id + amount yang sama tidak menggandakan transaksi.
"""
from __future__ import annotations

import http.client
import json
import re
import ssl
from urllib.parse import quote, urlencode, urlsplit

from django.conf import settings

ORDER_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
TXN_ID_RE = re.compile(r'^[A-Za-z0-9_-]{4,64}$')
SLUG_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
MAX_RESPONSE_BYTES = 64 * 1024
STATUSES = {'pending', 'completed', 'canceled'}


class PakasirError(Exception):
    """Kegagalan konfigurasi/jaringan/protokol — pesan aman untuk log & UI."""

    def __init__(self, message: str, *, code: str = 'error'):
        super().__init__(message)
        self.code = code


def is_configured() -> bool:
    """Provider dipilih, tetapi kredensial mungkin belum lengkap."""
    return (getattr(settings, 'PAYMENT_GATEWAY_PROVIDER', '') or '').lower() == 'pakasir'


def is_enabled() -> bool:
    """True hanya bila seluruh kredensial inti tersedia (fail-closed)."""
    return bool(
        is_configured()
        and getattr(settings, 'PAKASIR_SLUG', '')
        and getattr(settings, 'PAKASIR_API_KEY', '')
        and getattr(settings, 'PAKASIR_WEBHOOK_SECRET', '')
    )


def _clean_error_text(text: str) -> str:
    """Buang API key/kredensial dari pesan error sebelum dilog."""
    text = (text or '').strip().replace('\n', ' ')[:300]
    key = getattr(settings, 'PAKASIR_API_KEY', '') or ''
    if key and key in text:
        text = text.replace(key, '[REDACTED]')
    text = re.sub(r'(?i)(api[_-]?key=)[^&\s]+', r'\1[REDACTED]', text)
    return text


class PakasirClient:
    """Klien kecil untuk endpoint v2 yang dipakai situs ini."""

    def __init__(self, *, slug: str | None = None, api_key: str | None = None,
                 timeout: int | None = None):
        self.slug = (slug if slug is not None
                     else getattr(settings, 'PAKASIR_SLUG', '')).strip()
        self.api_key = (api_key if api_key is not None
                        else getattr(settings, 'PAKASIR_API_KEY', '')).strip()
        self.timeout = max(1, min(int(
            timeout if timeout is not None
            else getattr(settings, 'PAKASIR_TIMEOUT_SECONDS', 8)), 30))
        self.base_url = getattr(
            settings, 'PAKASIR_BASE_URL', 'https://app.pakasir.com')
        if not SLUG_RE.match(self.slug):
            raise PakasirError('Slug proyek Pakasir tidak valid.', code='config')
        if not self.api_key or len(self.api_key) < 16:
            raise PakasirError('API key Pakasir belum diisi/tidak valid.',
                               code='config')
        parts = urlsplit(self.base_url)
        if parts.scheme != 'https' or parts.hostname != 'app.pakasir.com':
            raise PakasirError('Base URL Pakasir tidak diizinkan.', code='config')

    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        if not path.startswith('/api/v2/'):
            raise PakasirError('Path API Pakasir tidak valid.', code='config')
        payload = None
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'NusantaraTrans/1.0 (+Django)',
            'X-Api-Key': self.api_key,
        }
        if body is not None:
            payload = json.dumps(body, separators=(',', ':')).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(
            'app.pakasir.com', timeout=self.timeout, context=context)
        try:
            try:
                conn.request(method, path, body=payload, headers=headers)
                response = conn.getresponse()
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            except (OSError, http.client.HTTPException) as exc:
                raise PakasirError(
                    f'Pakasir tidak dapat dihubungi: {exc.__class__.__name__}.',
                    code='network')
        finally:
            conn.close()

        if len(raw) > MAX_RESPONSE_BYTES:
            raise PakasirError('Respons Pakasir terlalu besar.', code='protocol')
        if response.status not in (200, 201):
            detail = ''
            try:
                parsed = json.loads(raw.decode('utf-8'))
                if isinstance(parsed, dict):
                    detail = _clean_error_text(str(
                        parsed.get('message') or parsed.get('error') or ''))
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            suffix = f' — {detail}' if detail else ''
            raise PakasirError(
                f'Pakasir menolak permintaan (HTTP {response.status}){suffix}.',
                code='http')
        try:
            data = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise PakasirError('Respons Pakasir bukan JSON valid.',
                               code='protocol')
        if not isinstance(data, dict):
            raise PakasirError('Respons Pakasir tidak dikenali.',
                               code='protocol')
        return data

    # ------------------------------------------------------------------
    def create_payment(self, order_id: str, amount: int) -> dict:
        """Buat (atau ambil) transaksi payment link QRIS.

        Mengembalikan dict tervalidasi: txn_id, order_id, amount,
        payment_url, is_sandbox, expired_at (bila ada).
        """
        if not ORDER_ID_RE.match(str(order_id or '')):
            raise PakasirError('order_id tidak valid.', code='input')
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise PakasirError('Nominal tidak valid.', code='input')
        minimum = int(getattr(settings, 'PAKASIR_MIN_AMOUNT', 500))
        maximum = int(getattr(settings, 'PAKASIR_MAX_AMOUNT', 50_000_000))
        if amount < minimum or amount > maximum:
            raise PakasirError(
                f'Nominal di luar batas Pakasir ({minimum}–{maximum}).',
                code='input')

        method = getattr(settings, 'PAKASIR_METHOD', 'payment_link')
        data = self._request(
            'POST',
            f'/api/v2/create-transaction/{quote(self.slug, safe="")}'
            f'/{quote(str(order_id), safe="")}',
            {'method': method, 'amount': amount},
        )
        txn_id = str(data.get('txn_id') or '')
        if not TXN_ID_RE.match(txn_id):
            raise PakasirError('txn_id Pakasir tidak valid.', code='protocol')
        # Respons metode `payment_link` hanya berisi txn_id + payment_link;
        # field lain (amount/order_id/is_sandbox) tidak selalu ada. Bila ada,
        # WAJIB cocok. Pencocokan final tetap dilakukan saat settlement
        # lewat transaction-status API sebelum status booking diubah.
        if data.get('order_id') and str(data['order_id']) != str(order_id):
            raise PakasirError('order_id pada respons tidak cocok.',
                               code='protocol')
        returned_amount = amount
        if data.get('amount') is not None:
            try:
                returned_amount = int(data.get('amount'))
            except (TypeError, ValueError):
                raise PakasirError('Nominal respons tidak valid.',
                                   code='protocol')
            if returned_amount != amount:
                raise PakasirError('Nominal pada respons tidak cocok.',
                                   code='protocol')

        payment_link = str(data.get('payment_link') or '')
        if not self._is_official_link(payment_link):
            raise PakasirError('Payment link Pakasir tidak valid.',
                               code='protocol')
        sandbox = bool(getattr(settings, 'PAKASIR_SANDBOX', False))
        if 'is_sandbox' in data:
            sandbox = bool(data.get('is_sandbox'))
        if sandbox != bool(getattr(settings, 'PAKASIR_SANDBOX', False)):
            raise PakasirError(
                'Mode sandbox Pakasir tidak sesuai konfigurasi.',
                code='sandbox')
        return {
            'txn_id': txn_id,
            'order_id': str(order_id),
            'amount': returned_amount,
            'payment_url': payment_link,
            'is_sandbox': sandbox,
            'expired_at': data.get('expired_at') or '',
            'fee': int(data.get('fee') or 0),
            'total_payment': int(data.get('total_payment') or 0),
        }

    # ------------------------------------------------------------------
    def get_status(self, txn_id: str) -> dict:
        """Status transaksi terbaru (pending/completed/canceled)."""
        if not TXN_ID_RE.match(str(txn_id or '')):
            raise PakasirError('txn_id tidak valid.', code='input')
        data = self._request(
            'GET',
            f'/api/v2/transaction-status/{quote(self.slug, safe="")}'
            f'/{quote(str(txn_id), safe="")}',
        )
        status = str(data.get('status') or '').lower()
        if status not in STATUSES:
            raise PakasirError('Status transaksi tidak dikenali.',
                               code='protocol')
        if str(data.get('txn_id') or '') != str(txn_id):
            raise PakasirError('txn_id pada respons tidak cocok.',
                               code='protocol')
        try:
            amount = int(data.get('amount'))
        except (TypeError, ValueError):
            raise PakasirError('Nominal respons tidak valid.', code='protocol')
        sandbox = bool(getattr(settings, 'PAKASIR_SANDBOX', False))
        if 'is_sandbox' in data:
            sandbox = bool(data.get('is_sandbox'))
        return {
            'txn_id': str(txn_id),
            'order_id': str(data.get('order_id') or ''),
            'amount': amount,
            'status': status,
            'is_sandbox': sandbox,
            'completed_at': data.get('completed_at') or '',
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _is_official_link(url: str) -> bool:
        parts = urlsplit(url)
        return (
            parts.scheme == 'https'
            and parts.hostname == 'app.pakasir.com'
            and parts.path.startswith('/pay-v2/')
            and not parts.username and not parts.password
        )

    @staticmethod
    def hosted_url(payment_url: str, *, redirect_url: str = '') -> str:
        """Tambahkan `qris_only=1` (+ redirect internal) ke payment link."""
        if not PakasirClient._is_official_link(payment_url):
            raise PakasirError('Payment link Pakasir tidak valid.',
                               code='protocol')
        params = {'qris_only': '1'}
        if redirect_url:
            parts = urlsplit(redirect_url)
            if parts.scheme in {'http', 'https'} and parts.hostname:
                params['redirect'] = redirect_url
        sep = '&' if '?' in payment_url else '?'
        return f'{payment_url}{sep}{urlencode(params)}'


def webhook_secret_matches(received: str) -> bool:
    """Perbandingan constant-time header X-Secret."""
    import hmac

    expected = getattr(settings, 'PAKASIR_WEBHOOK_SECRET', '') or ''
    received = received or ''
    if not expected or not received:
        return False
    return hmac.compare_digest(
        expected.encode('utf-8'), received[:512].encode('utf-8'))
