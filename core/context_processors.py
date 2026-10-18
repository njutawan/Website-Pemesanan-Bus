"""Context processor: pengaturan situs, hreflang, dan metadata SEO halaman."""
from django.conf import settings
from django.core.cache import cache

from core.models import PageMeta
from django.urls import translate_url
from django.utils.translation import get_language

from core.pakasir import is_enabled as pakasir_enabled

PAGE_META_CACHE_KEY = 'seo:pagemeta:all'


def site_settings(request):
    """Exposes business configuration (site name, contact, payment methods)."""
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_TAGLINE': settings.SITE_TAGLINE,
        'WHATSAPP_NUMBER': settings.WHATSAPP_NUMBER,
        'CONTACT': {
            'email': settings.CONTACT_EMAIL,
            'phone': settings.CONTACT_PHONE,
            'address': settings.CONTACT_ADDRESS,
            'hours': settings.CONTACT_HOURS,
        },
        'PAYMENT_METHODS': settings.PAYMENT_METHODS,
        'PAYMENT_DETAILS': settings.PAYMENT_DETAILS,
        'PAYMENT_TIMEOUT_HOURS': settings.PAYMENT_TIMEOUT_HOURS,
        'MAX_SEATS_PER_BOOKING': settings.MAX_SEATS_PER_BOOKING,
        'PAKASIR_ENABLED': pakasir_enabled(),
    }


def language_alternates(request):
    """
    Untuk SEO: hreflang + tombol ganti bahasa.

    Mengembalikan URL halaman yang sama dalam bahasa lain
    (menghormati pola URL i18n: "/" = ID, "/en/" = EN).
    """
    alternates = []
    current = get_language() or 'id'
    for code, _name in settings.LANGUAGES:
        if code == current:
            url = request.path
        else:
            try:
                url = translate_url(request.path, code)
            except Exception:
                url = None
        alternates.append({'code': code, 'url': url or request.path})
    return {'LANGUAGE_ALTERNATES': alternates, 'CURRENT_LANGUAGE': current}


def _cached_page_metas():
    """Seluruh PageMeta sebagai ``{path: PageMeta}`` dari cache (1 query/TTL).

    Context processor berjalan di SETIAP request untuk path apapun
    (termasuk URL dinamis berkode booking), jadi query per-path akan
    selalu menembak DB. Tabel PageMeta kecil (metadata per halaman
    statis), sehingga memuat semuanya sekali per TTL jauh lebih murah:
    request berikutnya — untuk path manapun, termasuk yang tidak punya
    PageMeta — 0 query. Perubahan via admin tetap langsung segar karena
    sinyal post_save/post_delete PageMeta menghapus cache (core.apps).
    """
    return cache.get_or_set(
        PAGE_META_CACHE_KEY,
        lambda: {pm.path: pm for pm in PageMeta.objects.all()},
        getattr(settings, 'CACHE_TTL_DEFAULT', 600))


def seo(request):
    """
    Metadata halaman (model PageMeta dari /admin/) untuk title,
    description, Open Graph, dan noindex.

    Pencocokan: path persis dulu; bila tidak ada dan path berprefiks
    '/en/', coba path tanpa prefiks (baris tanpa prefiks berlaku untuk
    kedua bahasa). Tidak ada -> templat memakai default.
    """
    page_metas = _cached_page_metas()
    pm = page_metas.get(request.path)
    if pm is None and request.path.startswith('/en/'):
        pm = page_metas.get(request.path[3:])
    ctx = {'page_meta': pm}
    if pm and pm.og_image:
        ctx['page_meta_og_image'] = request.build_absolute_uri(pm.og_image.url)
    return ctx
