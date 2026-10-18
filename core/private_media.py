"""Penyajian berkas ``MEDIA_ROOT`` dengan kontrol akses.

Media proyek terbagi dua:

* **Publik** — foto armada rental (``vehicles/``) dan gambar Open Graph
  (``meta/``). Kontennya memang untuk pengunjung & crawler, jadi boleh
  dilayani tanpa login (di produksi Nginx melayaninya langsung).
* **Privat** — bukti pembayaran bus (``payment_proofs/``) dan rental
  (``rental_proofs/``). Isinya data pribadi (nama pengirim, nomor
  rekening/e-wallet), jadi URL-nya saja tidak boleh cukup untuk
  mengunduhnya. Yang boleh mengakses hanya:

  1. **staf/admin** (``user.is_staff``) — untuk verifikasi pembayaran; dan
  2. **sesi pemilik bukti** — sesi yang sudah membuka halaman detail
     booking/sewa (kode booking berperan sebagai kredensial pemilik)
     atau yang baru mengunggah bukti tersebut, melalui
     :func:`grant_private_media_access`. Izin disimpan per sesi dan per
     path persis, jadi sesi satu booking tidak membuka bukti milik
     booking lain.

Direktori upload lain yang belum dikenal diperlakukan sebagai privat
(default-deny) agar ``upload_to`` baru tidak otomatis terekspos publik.
Respons privat diberi ``Cache-Control: private, no-store``.

Di produksi, ``deploy/nginx.conf`` mem-proxy awalan privat di atas ke
view ini alih-alih menyajikannya dari disk, sehingga kontrol akses yang
sama berlaku ada/tidaknya Nginx dan apapun nilai ``DEBUG``.
"""
import posixpath
from urllib.parse import unquote

from django.conf import settings
from django.http import Http404
from django.views.static import serve as static_serve

PUBLIC_MEDIA_PREFIXES = ('vehicles/', 'meta/')
PRIVATE_MEDIA_PREFIXES = ('payment_proofs/', 'rental_proofs/')
PRIVATE_MEDIA_SESSION_KEY = 'private_media_paths'
_MAX_SESSION_GRANTS = 20


def _normalize_media_path(path):
    """Normalisasi path persis seperti ``django.views.static.serve``.

    Otorisasi wajib menilai path hasil normalisasi yang sama agar alias
    seperti ``vehicles/../payment_proofs/x.jpg`` tidak bisa menyelundup
    melewati pemeriksaan awalan.
    """
    normalized = posixpath.normpath(unquote(str(path or ''))).lstrip('/')
    return '' if normalized == '.' else normalized


def grant_private_media_access(request, file_name):
    """Izinkan sesi request ini memuat satu berkas media privat tertentu."""
    if not file_name:
        return
    normalized = _normalize_media_path(file_name)
    if not normalized.startswith(PRIVATE_MEDIA_PREFIXES):
        return
    session = getattr(request, 'session', None)
    if session is None:
        return
    paths = list(session.get(PRIVATE_MEDIA_SESSION_KEY, []))
    if normalized in paths:
        return
    paths.append(normalized)
    session[PRIVATE_MEDIA_SESSION_KEY] = paths[-_MAX_SESSION_GRANTS:]


def _can_access_private_media(request, normalized_path):
    user = getattr(request, 'user', None)
    if bool(getattr(user, 'is_staff', False)):
        return True
    session = getattr(request, 'session', None)
    if session is None:
        return False
    return normalized_path in session.get(PRIVATE_MEDIA_SESSION_KEY, [])


def serve_media(request, path):
    """Sajikan berkas media publik bebas; berkas privat hanya yang berhak.

    Penolakan berupa 404 (bukan 403) agar keberadaan berkas privat tidak
    terkonfirmasi bagi pihak yang tidak berhak.
    """
    normalized = _normalize_media_path(path)
    if not normalized:
        raise Http404('Berkas tidak ditemukan.')

    is_public = normalized.startswith(PUBLIC_MEDIA_PREFIXES)
    if not is_public and not _can_access_private_media(request, normalized):
        raise Http404('Berkas tidak ditemukan.')

    response = static_serve(
        request, normalized, document_root=settings.MEDIA_ROOT)
    if not is_public:
        response.headers['Cache-Control'] = 'private, no-store'
    return response
