"""Audit keamanan terpusat — aman terhadap data sensitif.

Semua penulisan audit melewati modul ini agar:

* password/token/cookie **tidak pernah** masuk DB maupun log;
* email, nomor telepon, nama, dan URL bukti pembayaran disamarkan;
* kode booking (kredensial pemilik booking) hanya disimpan sebagian;
* kegagalan menulis audit tidak pernah menggagalkan request pengguna.

Tabel ``core.AuditLog`` hanya dapat dibaca superuser lewat /admin/.
"""
import logging

from django.conf import settings

from core.logging import redact_text

logger = logging.getLogger('audit')

_SENSITIVE_KEY_RE = None  # diisi lazy agar import ringan


def _sensitive_key(key):
    global _SENSITIVE_KEY_RE
    if _SENSITIVE_KEY_RE is None:
        import re
        _SENSITIVE_KEY_RE = re.compile(
            r'(?i)(password|passwd|pwd|secret|token|api[_-]?key|cookie|'
            r'session|authorization|email|phone|telp|whatsapp|name|address|'
            r'proof|card|cvv|cvc|nik|ktp)')
    return bool(_SENSITIVE_KEY_RE.search(str(key or '')))


def mask_email(value):
    text = str(value or '')
    if '@' not in text:
        return text
    local, _, domain = text.partition('@')
    keep = local[:1] if local else ''
    return f'{keep}***@{domain}'


def mask_phone(value):
    text = str(value or '')
    digits = ''.join(ch for ch in text if ch.isdigit())
    if len(digits) < 6:
        return '[PHONE]'
    return f'***{digits[-3:]}'


def mask_target(value):
    """Samarkan target audit: kode booking/email/telepon/path sensitif."""
    text = str(value or '').strip()
    if not text:
        return ''
    if '@' in text:
        return mask_email(text)[:120]
    digits = ''.join(ch for ch in text if ch.isdigit())
    if len(digits) >= 9 and digits == text.replace('+', '').replace('-', '').replace(' ', ''):
        return mask_phone(text)[:120]
    # Kode booking NT-XXXXXXXX / SEWA-XXXXXXXX: simpan prefiks saja.
    head, sep, tail = text.partition('-')
    if sep and 2 <= len(head) <= 6 and tail.isalnum() and len(tail) >= 4:
        return f'{head}-{tail[:2]}****'[:120]
    if 'payment_proofs/' in text or 'rental_proofs/' in text:
        return '[PRIVATE_FILE]'
    return redact_text(text)[:120]


def _sanitize(value, key='', depth=0):
    """Rekursif: buang nilai sensitif, batasi panjang & kedalaman."""
    if depth > 2:
        return '[TRUNCATED]'
    if isinstance(value, dict):
        return {str(k)[:40]: _sanitize(v, k, depth + 1)
                for k, v in list(value.items())[:20]}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v, key, depth + 1) for v in list(value)[:20]]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    text = str(value)
    if _sensitive_key(key):
        return '[REDACTED]'
    if 'payment_proofs/' in text or 'rental_proofs/' in text:
        return '[PRIVATE_FILE]'
    return redact_text(text)[:120]


def log_event(action, *, request=None, actor=None, target='', success=True,
              metadata=None):
    """Tulis satu event audit. Aman dipanggil dari middleware/view/signal."""
    if actor is None and request is not None:
        user = getattr(request, 'user', None)
        if getattr(user, 'is_authenticated', False):
            actor = user
    ip = None
    user_agent = ''
    if request is not None:
        from core.middleware import get_client_ip
        ip = get_client_ip(request)
        user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:255]
    safe_target = mask_target(target)
    safe_meta = _sanitize(metadata or {})
    actor_id = getattr(actor, 'pk', None)
    actor_label = getattr(actor, 'get_username', lambda: '')() if actor else ''
    # Log konsol: tanpa metadata detail, hanya korelasi yang aman.
    logger.info(
        'AUDIT action=%s success=%s actor=%s ip=%s target=%s',
        action, bool(success), actor_id, ip, safe_target,
    )
    try:
        from core.models import AuditLog
        AuditLog.objects.create(
            actor_id=actor_id,
            action=action,
            success=bool(success),
            target=safe_target,
            ip=ip,
            user_agent=user_agent,
            metadata=safe_meta,
        )
    except Exception:
        # Audit tidak boleh menjatuhkan request; kegagalan sudah terlihat di
        # log console (AUDIT action=...).
        logger.warning('AUDIT_DB_WRITE_FAILED action=%s', action)


def purge_old_events(days=None):
    """Hapus audit lebih lama dari retensi (dipanggil cron terjadwal)."""
    from datetime import timedelta

    from django.utils import timezone
    from core.models import AuditLog
    days = int(days if days is not None else getattr(
        settings, 'AUDIT_RETENTION_DAYS', 180))
    cutoff = timezone.now() - timedelta(days=max(days, 1))
    deleted, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
