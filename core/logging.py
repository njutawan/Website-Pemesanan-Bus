"""Filter logging: jangan pernah bocorkan secret/PII ke log.

Dipakai oleh semua handler console di ``settings.LOGGING``. Filter bekerja
pada pesan jadi (``record.getMessage()``) *dan* argumen, lalu mengganti nilai
sensitif sebelum ditulis. Tujuannya pertahanan berlapis: kode yang tidak
sengaja melakukan ``logger.info('token=%s', token)`` tetap tidak membocorkan
token ke stdout/Gunicorn/journald.
"""
import logging
import re

# key=value / key: value untuk nama kunci yang sensitif.
_SECRET_KV_RE = re.compile(
    r'(?i)\b(password|passwd|pwd|secret(?:_key)?|token|access[_-]?token|'
    r'refresh[_-]?token|api[_-]?key|apikey|authorization|auth|'
    r'csrfmiddlewaretoken|sessionid|session[_-]?id|cookie|'
    r'card[_-]?number|pan|cvv|cvc|private[_-]?key|client[_-]?secret)'
    r'\s*[=:]\s*("(?:[^"]*)"|\'(?:[^\']*)\'|'
    r'(?:Bearer|Basic)\s+[^\s,;&]+|[^\s,;&]+)',
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+')
_BASIC_RE = re.compile(r'(?i)\bBasic\s+[A-Za-z0-9+/=]{8,}')
_DSN_RE = re.compile(
    r'(?i)\b(postgres(?:ql)?|redis|rediss|mysql|amqp)://'
    r'[^:\s/@]+:[^@\s/]+@')
_DJANGO_INSECURE_RE = re.compile(r'django-insecure-[A-Za-z0-9_\-]+')
_EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
_PHONE_RE = re.compile(r'(?<!\d)(?:\+62|62|0)8\d{7,12}(?!\d)')
_CARD_RE = re.compile(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)')
# Kode booking adalah bearer token pemilik halaman; jangan pernah
# muncul utuh di log (path 500, pesan error, dsb.).
_PUBLIC_CODE_RE = re.compile(r'\b((?:NT|SEWA)-)[A-Za-z0-9]{4,20}\b')


def redact_text(text: str) -> str:
    """Saring satu string dari pola rahasia yang umum."""
    if not text:
        return text
    text = _SECRET_KV_RE.sub(lambda m: f'{m.group(1)}=[REDACTED]', text)
    text = _BEARER_RE.sub('Bearer [REDACTED]', text)
    text = _BASIC_RE.sub('Basic [REDACTED]', text)
    text = _DSN_RE.sub(lambda m: f'{m.group(1)}://[REDACTED]:[REDACTED]@', text)
    text = _DJANGO_INSECURE_RE.sub('django-insecure-[REDACTED]', text)
    text = _EMAIL_RE.sub('[EMAIL]', text)
    text = _PHONE_RE.sub('[PHONE]', text)
    text = _CARD_RE.sub('[CARD]', text)
    text = _PUBLIC_CODE_RE.sub(lambda m: f'{m.group(1)}[REDACTED]', text)
    return text


class RedactSecretsFilter(logging.Filter):
    """Filter logging yang menyamarkan secret/PII pada pesan akhir."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        safe = redact_text(message)
        if safe != message:
            # Ganti pesan; args dikosongkan agar tidak diformat ulang.
            record.msg = safe
            record.args = ()
        # Exception text (traceback) juga bisa memuat DSN/kredensial.
        # Format lebih dulu bila belum ada: formatter akan memakai exc_text
        # ini, sehingga traceback tidak lolos tanpa penyaringan.
        if record.exc_info and not record.exc_text:
            try:
                record.exc_text = redact_text(
                    logging.Formatter().formatException(record.exc_info))
            except Exception:
                pass
        if record.exc_text:
            record.exc_text = redact_text(record.exc_text)
        return True
