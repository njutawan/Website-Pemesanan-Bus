"""Verifikasi webhook pembayaran (provider-agnostik, tanpa panggilan keluar).

Situs ini memakai Pakasir API v2 untuk QRIS online (lihat
``core/payment_service.py``) dan transfer manual sebagai fallback. Modul ini
menyediakan helper HMAC generik untuk provider lain di masa depan
(midtrans/Xendit/dll.) dengan kontrak yang aman:

1. Endpoint webhook WAJIB membaca **raw body** (``request.body``), bukan
   ``request.POST`` yang sudah diparse.
2. Signature header berformat ``t=<unix>,v1=<hex_hmac_sha256>``; HMAC
   dihitung atas ``b"<t>." + raw_body`` dengan ``PAYMENT_WEBHOOK_SECRET``.
3. Tolak timestamp di luar toleransi (replay) dan gunakan
   ``hmac.compare_digest`` (anti timing attack).
4. Klaim ``event_id`` lewat :func:`claim_webhook_event` agar event yang sama
   tidak diproses dua kali (idempotensi).
5. JANGAN pernah mengambil harga/status dari payload untuk membuat booking;
   payload hanya boleh memverifikasi pembayaran booking yang sudah ada.
"""
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Optional

from django.conf import settings
from django.core.cache import cache


class WebhookVerificationError(ValueError):
    """Signature/timestamp/format webhook tidak valid."""


@dataclass(frozen=True)
class WebhookSignature:
    timestamp: int
    signatures: tuple


def parse_signature_header(header: str) -> WebhookSignature:
    if not header or not isinstance(header, str):
        raise WebhookVerificationError('Header signature kosong.')
    timestamp = None
    signatures = []
    for part in header.split(','):
        key, _, value = part.strip().partition('=')
        if key == 't':
            try:
                timestamp = int(value)
            except (TypeError, ValueError):
                raise WebhookVerificationError('Timestamp tidak valid.')
        elif key in {'v1', 'sha256'}:
            value = value.strip().lower()
            if value:
                signatures.append(value)
    if timestamp is None or not signatures:
        raise WebhookVerificationError('Header signature tidak lengkap.')
    return WebhookSignature(timestamp=timestamp, signatures=tuple(signatures))


def verify_webhook_signature(payload: bytes, signature_header: str, *,
                             secret: Optional[str] = None,
                             tolerance: Optional[int] = None,
                             now: Optional[int] = None) -> bool:
    """True hanya bila HMAC valid dan timestamp masih dalam toleransi."""
    secret = secret if secret is not None else getattr(
        settings, 'PAYMENT_WEBHOOK_SECRET', '')
    if not secret:
        return False
    try:
        parsed = parse_signature_header(signature_header)
    except WebhookVerificationError:
        return False
    tolerance = int(tolerance if tolerance is not None else getattr(
        settings, 'PAYMENT_WEBHOOK_TOLERANCE_SECONDS', 300))
    current = int(now if now is not None else time.time())
    if abs(current - parsed.timestamp) > tolerance:
        return False
    signed = str(parsed.timestamp).encode('ascii') + b'.' + (payload or b'')
    expected = hmac.new(
        str(secret).encode('utf-8'), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate)
               for candidate in parsed.signatures)


def parse_event(payload: bytes) -> dict:
    """Parse JSON event dengan batas ukuran & tipe yang jelas."""
    if not payload or len(payload) > 256 * 1024:
        raise WebhookVerificationError('Payload webhook tidak wajar.')
    try:
        event = json.loads(payload.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise WebhookVerificationError('Payload webhook bukan JSON valid.')
    if not isinstance(event, dict):
        raise WebhookVerificationError('Payload webhook harus objek JSON.')
    return event


def claim_webhook_event(event_id: str, *, ttl: int = 24 * 60 * 60) -> bool:
    """True bila event baru; False bila sudah pernah diproses (idempoten)."""
    if not event_id or len(str(event_id)) > 200:
        return False
    try:
        return bool(cache.add(f'webhook:event:{event_id}', 1, timeout=ttl))
    except Exception:
        # Cache mati: jangan mengklaim idempoten (fail-closed) karena
        # memproses event ganda bisa menggandakan status pembayaran.
        return False
