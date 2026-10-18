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


def clean_text(value, *, max_length=None, allow_newlines=False):
    """Sanitasi teks bebas: buang karakter kontrol & rapikan spasi.

    Dipakai sebelum data pengguna disimpan/ditampilkan. Escaping HTML tetap
    dilakukan template (autoescape); fungsi ini mencegah karakter kontrol,
    NUL, dan spasi berlebih yang bisa merusak log/CSV/atribut.
    """
    text = '' if value is None else str(value)
    # Buang NUL & karakter kontrol C0/C1 kecuali tab/newline (bila diizinkan).
    allowed = {'\t', '\n', '\r'} if allow_newlines else set()
    text = ''.join(
        ch for ch in text
        if ch in allowed or (ord(ch) >= 32 and ord(ch) != 127
                             and not (0x80 <= ord(ch) <= 0x9f))
    )
    text = ' '.join(text.split()) if not allow_newlines else text.strip()
    if max_length is not None and len(text) > max_length:
        raise ValidationError(
            _('Teks terlalu panjang (maksimal %(max)s karakter).')
            % {'max': max_length})
    return text


def validate_image_upload(file_obj, *, max_bytes=None):
    """Validasi berkas gambar unggahan (admin & publik).

    * ukuran berkas <= MAX_UPLOAD_SIZE (default 6 MB),
    * ekstensi dalam MEDIA_ALLOWED_EXTENSIONS,
    * isi benar-benar gambar (Pillow verify) dan bukan decompression bomb,
    * nama berkas dipangkas, tanpa path.
    """
    from pathlib import Path

    name = Path(getattr(file_obj, 'name', '') or '').name
    if not name:
        raise ValidationError(_('Nama berkas tidak valid.'))
    max_bytes = int(max_bytes if max_bytes is not None else getattr(
        settings, 'MAX_UPLOAD_SIZE', 6 * 1024 * 1024))
    size = int(getattr(file_obj, 'size', 0) or 0)
    if size <= 0:
        raise ValidationError(_('Berkas kosong tidak diterima.'))
    if size > max_bytes:
        raise ValidationError(
            _('Ukuran berkas maksimal %(mb)s MB.')
            % {'mb': max_bytes // (1024 * 1024)})
    suffix = Path(name).suffix.lower()
    allowed = tuple(getattr(
        settings, 'MEDIA_ALLOWED_EXTENSIONS', ('.jpg', '.jpeg', '.png', '.webp')))
    if suffix not in allowed:
        raise ValidationError(_('Format berkas harus JPG, PNG, atau WebP.'))
    try:
        from PIL import Image
        file_obj.seek(0)
        with Image.open(file_obj) as image:
            image.verify()
            fmt = (image.format or '').upper()
            width, height = image.size
        file_obj.seek(0)
    except Exception:
        raise ValidationError(_('Berkas gambar tidak valid.'))
    if fmt not in {'JPEG', 'PNG', 'WEBP'}:
        raise ValidationError(_('Format gambar tidak didukung.'))
    max_pixels = int(getattr(settings, 'IMAGE_MAX_PIXELS', 25_000_000))
    if width < 1 or height < 1 or width * height > max_pixels:
        raise ValidationError(_('Dimensi gambar terlalu besar.'))
    return file_obj


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
