"""Util konversi gambar unggahan -> WebP (Core Web Vitals / LCP).

Setiap gambar publik yang diunggah (foto mobil, og:image) otomatis:
* diputar sesuai EXIF (foto HP),
* diubah ke RGB bila perlu,
* di-resize ke lebar maksimum (LANCZOS),
* disimpan ulang sebagai WebP (kualitas 82, method 6) — asli dihapus.

Konversi lewat storage API Django (bukan path disk) sehingga tetap bekerja
bila kelak storage diganti (mis. S3). GIF animasi & WebP dilewati.

Bukti pembayaran SENGAJA tidak dikonversi: itu dokumen bukti legal —
disimpan apa adanya, hanya tampil sebagai thumbnail kecil di admin.
"""
import io

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

SKIP_EXTS = {'webp', 'gif'}


def convert_to_webp(file_field, max_width=1200, quality=82):
    """Konversi berkas pada FileField/ImageField ke WebP.

    Return nama berkas baru (string) bila berhasil, None bila dilewati/
    gagal. Berkas asli dihapus dari storage.
    """
    name = file_field.name or ''
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    if not name or ext in SKIP_EXTS or not file_field:
        return None
    try:
        img = Image.open(file_field)
        img = ImageOps.exif_transpose(img)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        if img.width > max_width:
            height = max(1, round(img.height * max_width / img.width))
            img = img.resize((max_width, height), Image.LANCZOS)
    except Exception:
        return None  # berkas rusak/bukan gambar — biarkan apa adanya

    buf = io.BytesIO()
    img.save(buf, 'WEBP', quality=quality, method=6)
    new_name = f'{name.rsplit(".", 1)[0]}.webp'
    storage = file_field.storage
    if storage.exists(new_name):
        storage.delete(new_name)
    storage.save(new_name, ContentFile(buf.getvalue()))
    storage.delete(name)
    return new_name
