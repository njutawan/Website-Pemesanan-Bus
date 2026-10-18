"""View pembayaran QRIS Pakasir: buat link, cek status, dan webhook.

Webhook adalah satu-satunya endpoint publik yang `csrf_exempt`; keasliannya
dijaga oleh header ``X-Secret`` + verifikasi ulang ke API Pakasir. Tidak ada
API key yang pernah dikirim ke browser.
"""
from __future__ import annotations

import json
import logging

from django.core.exceptions import (
    ObjectDoesNotExist, ValidationError as DjangoValidationError,
)
from django.http import (
    Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse,
)
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core import payment_service
from core.audit import log_event
from core.models import PaymentTransaction
from core.pakasir import PakasirClient, PakasirError, is_configured, is_enabled
from core.validators import clean_public_code

logger = logging.getLogger('core')

WEBHOOK_MAX_BYTES = 16 * 1024


def _safe_code(raw: str) -> str:
    try:
        return clean_public_code(raw)
    except DjangoValidationError:
        raise Http404('Kode booking tidak valid.')


def _redirect_to_detail(kind: str, code: str):
    return redirect(payment_service.booking_detail_url(kind, code))


def _get_booking_or_404(kind: str, code: str):
    try:
        return payment_service.get_booking(kind, code)
    except payment_service.PaymentError:
        raise Http404('Jenis booking tidak dikenal.')
    except ObjectDoesNotExist:
        raise Http404('Booking tidak ditemukan.')


@require_POST
def create_payment(request, kind, code):
    """Buat (atau pakai ulang) link pembayaran Pakasir lalu redirect."""
    if not is_enabled():
        raise Http404('Pembayaran QRIS online tidak aktif.')
    code = _safe_code(code)
    booking = _get_booking_or_404(kind, code)
    try:
        txn = payment_service.start_payment(kind, booking.code)
        link = PakasirClient.hosted_url(
            txn.payment_url,
            redirect_url=request.build_absolute_uri(
                payment_service.booking_detail_url(kind, booking.code)),
        )
    except (payment_service.PaymentError, PakasirError):
        from django.contrib import messages
        messages.error(
            request,
            _('Pembayaran QRIS online gagal dibuat. Silakan coba lagi atau gunakan transfer manual di bawah.'))
        return _redirect_to_detail(kind, booking.code)
    return redirect(link)


@require_POST
def payment_status(request, kind, code):
    """Sinkronkan status ke Pakasir (cadangan bila webhook telat)."""
    from django.contrib import messages

    if not is_enabled():
        raise Http404('Pembayaran QRIS online tidak aktif.')
    code = _safe_code(code)
    booking = _get_booking_or_404(kind, code)

    if booking.status != booking.Status.PENDING:
        messages.info(request, _('Booking ini sudah tidak menunggu pembayaran.'))
        return _redirect_to_detail(kind, booking.code)

    txn = payment_service.latest_transaction(kind, booking.code)
    if txn is None or not txn.txn_id:
        messages.info(request, _('Belum ada transaksi QRIS untuk booking ini.'))
        return _redirect_to_detail(kind, booking.code)

    try:
        txn = payment_service.sync_transaction(txn)
    except payment_service.PaymentError as exc:
        messages.warning(request, str(exc))
        return _redirect_to_detail(kind, booking.code)

    if txn.status == PaymentTransaction.Status.COMPLETED:
        if txn.needs_review:
            messages.warning(
                request,
                _('Pembayaran diterima, tetapi perlu ditinjau admin. Tim kami akan menghubungi Anda.'))
        else:
            messages.success(request, _('Pembayaran berhasil dikonfirmasi!'))
    elif txn.status == PaymentTransaction.Status.CANCELED:
        messages.warning(
            request,
            _('Transaksi QRIS ini dibatalkan/kedaluwarsa. Silakan buat pembayaran baru.'))
    else:
        messages.info(
            request,
            _('Pembayaran belum diterima. Jika sudah membayar, tunggu beberapa saat lalu cek lagi.'))
    return _redirect_to_detail(kind, booking.code)


@csrf_exempt
def pakasir_webhook(request):
    """Terima webhook Pakasir. Balas 200 agar Pakasir tidak retry."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not is_configured():
        raise Http404('Webhook tidak aktif.')

    received = request.headers.get('X-Secret', '')
    from core.pakasir import webhook_secret_matches
    if not webhook_secret_matches(received):
        log_event(
            'WEBHOOK_REJECTED', request=request, success=False,
            metadata={'provider': 'pakasir', 'reason': 'secret'})
        return JsonResponse({'error': 'unauthorized'}, status=401)

    # Content-Type tidak dijadikan gerbang: contoh resmi Pakasir memakai
    # `curl --data` (form-urlencoded) walau body-nya JSON. Keaslian webhook
    # ditentukan oleh X-Secret + verifikasi ulang ke API, bukan header ini.
    try:
        raw = request.body
    except Exception:
        return JsonResponse({'error': 'body-too-large'}, status=413)
    if not raw or len(raw) > WEBHOOK_MAX_BYTES:
        return JsonResponse({'error': 'invalid-size'}, status=400)
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'error': 'invalid-json'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'invalid-json'}, status=400)

    try:
        payment_service.handle_webhook(payload)
    except payment_service.WebhookError as exc:
        log_event(
            'WEBHOOK_REJECTED', request=request, success=False,
            metadata={'provider': 'pakasir', 'reason': exc.code})
        return JsonResponse({'error': exc.code}, status=exc.http_status)
    except Exception:
        # Jangan pernah membocorkan detail internal ke pengirim webhook.
        logger.exception('PAKASIR_WEBHOOK_UNEXPECTED')
        return JsonResponse({'error': 'server-error'}, status=500)
    return JsonResponse({'status': 'ok'})
