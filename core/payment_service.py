"""Orkestrasi pembayaran Pakasir: buat link, sinkronkan status, settlement.

Alur aman:
1. Pelanggan menekan "Bayar QRIS" → ``start_payment`` membuat baris
   ``PaymentTransaction`` dengan ``order_id`` acak dan nominal dari database
   (bukan dari klien), lalu memanggil Pakasir API v2.
2. Pakasir mengirim webhook ``X-Secret`` saat pembayaran berhasil.
3. ``handle_webhook`` memverifikasi secret, mencocokkan order_id/nominal,
   lalu **memanggil ulang** transaction-status API. Status booking baru
   berubah setelah API mengonfirmasi ``completed`` untuk nominal yang sama.
4. ``sync_transaction`` memberi jalur cadangan bila webhook tidak sampai
   (pelanggan menekan "Cek status"); dibatasi 1 panggilan / 4 detik /
   transaksi sesuai rate limit Pakasir.
"""
from __future__ import annotations

import secrets
from datetime import timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.audit import log_event
from core.models import PaymentTransaction
from core.pakasir import (
    ORDER_ID_RE, TXN_ID_RE, PakasirClient, PakasirError, is_enabled,
)

MAX_ATTEMPTS_PER_BOOKING = 5
SYNC_COOLDOWN_SECONDS = 4


class PaymentError(Exception):
    """Kesalahan yang aman ditampilkan ke pengguna."""


class WebhookError(Exception):
    """Webhook ditolak; ``http_status`` menentukan balasan ke Pakasir."""

    def __init__(self, message: str, *, http_status: int = 400, code: str = 'invalid'):
        super().__init__(message)
        self.http_status = http_status
        self.code = code


# ---------------------------------------------------------------------------
# Resolusi booking (bus/rental) tanpa import melingkar saat app loading
# ---------------------------------------------------------------------------
def get_booking(kind: str, code: str, *, for_update: bool = False):
    if kind == PaymentTransaction.Kind.BUS:
        from booking.models import Booking
        model = Booking
    elif kind == PaymentTransaction.Kind.RENTAL:
        from rental.models import RentalBooking
        model = RentalBooking
    else:
        raise PaymentError('Jenis booking tidak dikenal.')
    qs = model.objects
    if for_update:
        qs = qs.select_for_update()
    return qs.get(code__iexact=code)


def booking_detail_url(kind: str, code: str) -> str:
    if kind == PaymentTransaction.Kind.BUS:
        return reverse('booking:detail', kwargs={'code': code})
    return reverse('rental:detail_booking', kwargs={'code': code})


def latest_transaction(kind: str, code: str):
    return (
        PaymentTransaction.objects
        .filter(kind=kind, booking_code=code)
        .exclude(status=PaymentTransaction.Status.FAILED)
        .order_by('-created_at')
        .first()
    )


def active_transaction(kind: str, code: str):
    """Transaksi PENDING yang masih berlaku (untuk tombol lanjutkan)."""
    txn = latest_transaction(kind, code)
    if txn and txn.is_pending_valid and txn.payment_url:
        return txn
    return None


# ---------------------------------------------------------------------------
# Pembuatan link pembayaran
# ---------------------------------------------------------------------------
def start_payment(kind: str, code: str) -> PaymentTransaction:
    if not is_enabled():
        raise PaymentError('Pembayaran QRIS online belum tersedia.')

    booking = get_booking(kind, code)
    if booking.status != booking.Status.PENDING:
        raise PaymentError('Booking ini sudah tidak menunggu pembayaran.')
    if booking.is_payment_overdue:
        raise PaymentError('Batas waktu pembayaran sudah lewat.')

    existing = active_transaction(kind, code)
    if existing:
        return existing

    attempts = PaymentTransaction.objects.filter(
        kind=kind, booking_code=code).count()
    if attempts >= MAX_ATTEMPTS_PER_BOOKING:
        raise PaymentError(
            'Terlalu banyak percobaan pembayaran untuk booking ini. '
            'Hubungi CS untuk dibantu.')

    lock_key = f'pay:start:{kind}:{code}'
    if not cache.add(lock_key, 1, timeout=15):
        existing = active_transaction(kind, code)
        if existing:
            return existing
        raise PaymentError('Pembuatan pembayaran sedang diproses. Coba lagi.')

    amount = int(booking.total_price)
    minimum = int(getattr(settings, 'PAKASIR_MIN_AMOUNT', 500))
    maximum = int(getattr(settings, 'PAKASIR_MAX_AMOUNT', 50_000_000))
    if amount < minimum or amount > maximum:
        raise PaymentError(
            'Nominal booking di luar batas pembayaran QRIS online. '
            'Silakan transfer manual.')

    order_id = f'{code}-{secrets.token_hex(2).upper()}'
    if not ORDER_ID_RE.match(order_id):
        raise PaymentError('Gagal membuat ID pembayaran.')

    txn = PaymentTransaction.objects.create(
        provider=PaymentTransaction.Provider.PAKASIR,
        order_id=order_id,
        kind=kind,
        booking_code=code,
        amount=amount,
        is_sandbox=bool(getattr(settings, 'PAKASIR_SANDBOX', False)),
        expires_at=booking.payment_deadline,
    )

    try:
        result = PakasirClient().create_payment(order_id, amount)
    except PakasirError as exc:
        txn.status = PaymentTransaction.Status.FAILED
        txn.last_event = {'error': exc.code}
        txn.save(update_fields=['status', 'last_event', 'updated_at'])
        raise PaymentError(
            'Gagal membuat pembayaran QRIS. Coba lagi atau gunakan '
            'transfer manual.')

    if bool(result.get('is_sandbox')) != bool(
            getattr(settings, 'PAKASIR_SANDBOX', False)):
        txn.status = PaymentTransaction.Status.FAILED
        txn.last_event = {'error': 'sandbox_mismatch'}
        txn.save(update_fields=['status', 'last_event', 'updated_at'])
        raise PaymentError('Konfigurasi mode pembayaran tidak sesuai.')

    txn.txn_id = result['txn_id']
    txn.payment_url = result['payment_url']
    txn.fee = int(result.get('fee') or 0)
    txn.total_payment = int(result.get('total_payment') or 0)
    txn.is_sandbox = bool(result.get('is_sandbox', txn.is_sandbox))
    expiry = _parse_dt(result.get('expired_at'))
    if expiry is not None and expiry < timezone.now():
        txn.status = PaymentTransaction.Status.EXPIRED
        txn.save(update_fields=[
            'txn_id', 'payment_url', 'fee', 'total_payment', 'is_sandbox',
            'status', 'updated_at'])
        raise PaymentError('Link pembayaran langsung kedaluwarsa. Coba lagi.')
    txn.save(update_fields=[
        'txn_id', 'payment_url', 'fee', 'total_payment', 'is_sandbox',
        'updated_at'])

    log_event(
        'PAYMENT_LINK_CREATED', target=booking.code,
        metadata={'provider': 'pakasir', 'kind': kind, 'amount': amount})
    return txn


# ---------------------------------------------------------------------------
# Sinkronisasi status (fallback bila webhook telat)
# ---------------------------------------------------------------------------
def sync_transaction(txn: PaymentTransaction) -> PaymentTransaction:
    if txn.status != PaymentTransaction.Status.PENDING or not txn.txn_id:
        return txn
    cooldown_key = f'pay:sync:{txn.txn_id}'
    if not cache.add(cooldown_key, 1, timeout=SYNC_COOLDOWN_SECONDS):
        raise PaymentError(
            'Status baru saja diperiksa. Tunggu beberapa detik lagi.')
    try:
        status = PakasirClient().get_status(txn.txn_id)
    except PakasirError as exc:
        raise PaymentError(
            'Status pembayaran belum dapat diperiksa. Coba lagi nanti.'
            if exc.code != 'config' else
            'Pembayaran QRIS online belum dikonfigurasi.')
    _check_status_identity(txn, status)

    if status['status'] == 'completed':
        _settle(txn, status)
    elif status['status'] == 'canceled':
        txn.status = PaymentTransaction.Status.CANCELED
        txn.last_event = _safe_event(status)
        txn.save(update_fields=['status', 'last_event', 'updated_at'])
    else:
        txn.last_event = _safe_event(status)
        txn.save(update_fields=['last_event', 'updated_at'])
    txn.refresh_from_db()
    return txn


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------
def handle_webhook(payload: dict) -> PaymentTransaction:
    event = _validate_webhook_payload(payload)
    txn = PaymentTransaction.objects.filter(order_id=event['order_id']).first()
    if txn is None:
        raise WebhookError('order_id tidak dikenal.', http_status=404,
                           code='unknown_order')
    if txn.provider != PaymentTransaction.Provider.PAKASIR:
        raise WebhookError('Provider tidak sesuai.', http_status=400)

    if txn.txn_id and txn.txn_id != event['txn_id']:
        raise WebhookError('txn_id tidak cocok.', http_status=400,
                           code='txn_mismatch')
    if int(txn.amount) != event['amount']:
        _flag_review(txn, event)
        raise WebhookError('Nominal tidak cocok.', http_status=400,
                           code='amount_mismatch')
    if event['is_sandbox'] is not None and bool(event['is_sandbox']) != bool(
            txn.is_sandbox):
        raise WebhookError('Mode sandbox tidak cocok.', http_status=400,
                           code='sandbox_mismatch')
    if event['status'] != 'completed':
        raise WebhookError('Status webhook tidak didukung.', http_status=400,
                           code='status')

    # Defense in depth: jangan percaya body webhook (bisa dipalsukan bila
    # secret bocor). Konfirmasi ulang ke API dengan API key server-side.
    try:
        status = PakasirClient().get_status(event['txn_id'])
    except PakasirError:
        # Minta Pakasir mengirim ulang nanti; jangan pernah settle tanpa
        # konfirmasi API.
        raise WebhookError('Konfirmasi status gagal; coba lagi.',
                           http_status=503, code='retry')

    try:
        _check_status_identity(txn, status)
    except PaymentError as exc:
        raise WebhookError(str(exc), http_status=400, code='verify_failed')
    if status['status'] != 'completed':
        raise WebhookError('Transaksi belum lunas menurut API.',
                           http_status=409, code='not_completed')

    _settle(txn, status)
    txn.refresh_from_db()
    return txn


def _validate_webhook_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise WebhookError('Body harus objek JSON.', http_status=400)
    order_id = payload.get('order_id')
    txn_id = payload.get('txn_id')
    if not isinstance(order_id, str) or not ORDER_ID_RE.match(order_id):
        raise WebhookError('order_id tidak valid.', http_status=400)
    if not isinstance(txn_id, str) or not TXN_ID_RE.match(txn_id):
        raise WebhookError('txn_id tidak valid.', http_status=400)
    amount = payload.get('amount')
    if isinstance(amount, bool):
        raise WebhookError('amount tidak valid.', http_status=400)
    if isinstance(amount, str) and amount.isdigit():
        amount = int(amount)
    if not isinstance(amount, int) or amount <= 0:
        raise WebhookError('amount tidak valid.', http_status=400)
    status = payload.get('status')
    if not isinstance(status, str):
        raise WebhookError('status tidak valid.', http_status=400)
    sandbox = payload.get('is_sandbox', None)
    if sandbox is not None and not isinstance(sandbox, bool):
        raise WebhookError('is_sandbox tidak valid.', http_status=400)
    return {
        'order_id': order_id,
        'txn_id': txn_id,
        'amount': amount,
        'status': status.strip().lower(),
        'is_sandbox': sandbox,
    }


def _check_status_identity(txn: PaymentTransaction, status: dict) -> None:
    if str(status.get('order_id') or '') != txn.order_id:
        raise PaymentError('order_id dari API tidak cocok.')
    if int(status.get('amount') or 0) != int(txn.amount):
        _flag_review(txn, status)
        raise PaymentError('Nominal dari API tidak cocok.')
    if bool(status.get('is_sandbox')) != bool(
            getattr(settings, 'PAKASIR_SANDBOX', False)):
        raise PaymentError('Mode sandbox dari API tidak cocok.')


# ---------------------------------------------------------------------------
# Settlement atomik
# ---------------------------------------------------------------------------
def _settle(txn: PaymentTransaction, event: dict) -> None:
    """Tandai lunas + konfirmasi booking, idempoten dan aman dari race."""
    with transaction.atomic():
        locked = PaymentTransaction.objects.select_for_update().get(pk=txn.pk)
        if locked.status == PaymentTransaction.Status.COMPLETED:
            return
        booking = get_booking(locked.kind, locked.booking_code, for_update=True)

        if int(booking.total_price) != int(locked.amount):
            _mark_paid_needs_review(locked, event, reason='amount_drift')
            return
        if booking.status in {
                booking.Status.CANCELLED, booking.Status.EXPIRED}:
            # Uang masuk setelah kursi dilepas: jangan konfirmasi otomatis.
            _mark_paid_needs_review(locked, event, reason='booking_inactive')
            return
        if booking.is_payment_overdue:
            # Batas bayar lokal (PAYMENT_TIMEOUT_HOURS) sudah lewat walau cron
            # belum sempat menandai EXPIRED — tinjau manual, jangan auto.
            _mark_paid_needs_review(locked, event, reason='booking_overdue')
            return

        now = timezone.now()
        if booking.status == booking.Status.PENDING:
            booking.status = booking.Status.CONFIRMED
            booking.paid_at = now
            booking.payment_method = getattr(
                settings, 'PAYMENT_METHOD_PAKASIR', 'pakasir_qris')
            booking.save(update_fields=[
                'status', 'paid_at', 'payment_method', 'updated_at'])
            log_event(
                'PAYMENT_RECEIVED', target=booking.code,
                metadata={
                    'provider': 'pakasir',
                    'kind': locked.kind,
                    'amount': int(locked.amount),
                    'gateway_status': 'completed',
                })
        if not locked.txn_id and event.get('txn_id'):
            locked.txn_id = str(event['txn_id'])[:64]
        locked.status = PaymentTransaction.Status.COMPLETED
        locked.paid_at = now
        locked.needs_review = False
        locked.last_event = _safe_event(event)
        locked.save(update_fields=[
            'txn_id', 'status', 'paid_at', 'needs_review', 'last_event',
            'updated_at'])


def _mark_paid_needs_review(txn: PaymentTransaction, event: dict,
                            *, reason: str) -> None:
    txn.status = PaymentTransaction.Status.COMPLETED
    txn.paid_at = timezone.now()
    txn.needs_review = True
    txn.last_event = _safe_event(event, reason=reason)
    txn.save(update_fields=[
        'status', 'paid_at', 'needs_review', 'last_event', 'updated_at'])
    log_event(
        'PAYMENT_UNMATCHED', success=False, target=txn.booking_code,
        metadata={'provider': 'pakasir', 'kind': txn.kind,
                  'amount': int(txn.amount), 'reason': reason})


def _flag_review(txn: PaymentTransaction, event: dict) -> None:
    txn.last_event = _safe_event(event, reason='amount_mismatch')
    txn.needs_review = True
    txn.save(update_fields=['needs_review', 'last_event', 'updated_at'])


# ---------------------------------------------------------------------------
# Utilitas
# ---------------------------------------------------------------------------
def _parse_dt(value):
    if not value or not isinstance(value, str) or len(value) > 64:
        return None
    parsed = parse_datetime(value.replace('Z', '+00:00'))
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def _safe_event(event: dict, *, reason: str = '') -> dict:
    """Simpan hanya field primitif yang aman (tanpa data sensitif)."""
    safe = {}
    for key in ('txn_id', 'order_id', 'amount', 'status', 'is_sandbox',
                'completed_at'):
        value = event.get(key)
        if isinstance(value, (str, int, bool)) and len(str(value)) <= 128:
            safe[key] = value
    if reason:
        safe['reason'] = reason
    return safe


def payment_page_context(kind: str, code: str, request, booking) -> dict:
    """Konteks template untuk panel pembayaran online."""
    txn = latest_transaction(kind, code)
    link = ''
    if txn and txn.payment_url and txn.status == PaymentTransaction.Status.PENDING:
        try:
            redirect_url = request.build_absolute_uri(
                booking_detail_url(kind, code))
            link = PakasirClient.hosted_url(
                txn.payment_url, redirect_url=redirect_url)
        except PakasirError:
            link = txn.payment_url
    return {
        'pakasir_enabled': is_enabled(),
        'pakasir_txn': txn,
        'pakasir_payment_link': link,
        'pakasir_min_amount': int(getattr(
            settings, 'PAKASIR_MIN_AMOUNT', 500)),
    }


def payment_expiry_label(txn) -> str:
    if not txn or not txn.expires_at:
        return ''
    remaining = txn.expires_at - timezone.now()
    if remaining <= timedelta(0):
        return 'kedaluwarsa'
    minutes = int(remaining.total_seconds() // 60)
    if minutes < 60:
        return f'{minutes} menit'
    return f'{minutes // 60} jam {minutes % 60} menit'
