"""Validator bersama: kode publik, tanggal, label kursi, dan output CSV."""
import re
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

PUBLIC_CODE_RE = re.compile(r'^[A-Za-z0-9-]{4,20}$')
SEAT_LABEL_RE = re.compile(r'^[A-Z0-9]{1,4}$')
_CSV_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def clean_phone(value):
    """Nomor telepon/WhatsApp: 9–16 digit, boleh diawali '+'."""
    phone = re.sub(r'[\s\-]', '', (value or '').strip())
    if not re.fullmatch(r'\+?\d{9,16}', phone):
        raise ValidationError(
            _('Nomor telepon tidak valid. Contoh: 081234567890'))
    return phone


def clean_public_code(value):
    """Kode booking/sewa: 4–20 karakter alfanumerik + strip.

    Mencegah input raksasa / karakter kontrol menyentuh query DB.
    """
    code = (value or '').strip()
    if not PUBLIC_CODE_RE.fullmatch(code):
        raise ValidationError(_('Kode tidak valid.'))
    return code


def validate_travel_date(value, *, max_days=None):
    """Tanggal tidak di masa lalu dan tidak lebih dari batas horizon."""
    today = timezone.localdate()
    if value < today:
        raise ValidationError(_('Tanggal tidak boleh di masa lalu.'))
    max_days = int(max_days if max_days is not None else getattr(
        settings, 'MAX_TRAVEL_DATE_DAYS', 365))
    if value > today + timedelta(days=max_days):
        raise ValidationError(
            _('Tanggal terlalu jauh. Maksimal %(days)s hari ke depan.')
            % {'days': max_days})
    return value


def clean_seat_labels(raw, *, max_seats):
    """Parse CSV label kursi: batasi panjang, format, dan duplikat."""
    raw = (raw or '').strip()
    if len(raw) > 120:
        raise ValidationError(_('Daftar kursi terlalu panjang.'))
    labels = [part.strip().upper() for part in raw.split(',') if part.strip()]
    if not labels:
        raise ValidationError(_('Pilih minimal 1 kursi.'))
    if len(labels) > max_seats:
        raise ValidationError(
            _('Pilih minimal 1 kursi (maksimal %(max)s).') % {'max': max_seats})
    if len(set(labels)) != len(labels):
        raise ValidationError(_('Kursi yang sama dipilih lebih dari sekali.'))
    for label in labels:
        if not SEAT_LABEL_RE.fullmatch(label):
            raise ValidationError(_('Label kursi tidak valid.'))
    return labels


def csv_safe(value):
    """Cegah CSV formula injection saat data pengguna diekspor ke Excel.

    Sel yang diawali =, +, -, @, TAB, atau CR dapat dieksekusi Excel/
    LibreOffice sebagai formula. Beri prefiks apostrof agar diperlakukan
    sebagai teks.
    """
    text = '' if value is None else str(value)
    # Excel/LibreOffice mengabaikan spasi di awal sel; periksa versi tanpa
    # spasi agar " =cmd" tidak lolos sebagai formula.
    if text.lstrip(' \t\r\n').startswith(_CSV_FORMULA_PREFIXES):
        return "'" + text
    # Newline di dalam sel juga bisa membingungkan parser; ganti dengan spasi.
    return text.replace('\r', ' ').replace('\n', ' ')
