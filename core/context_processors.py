"""Context processor: pengaturan situs, hreflang, dan metadata SEO halaman."""
from django.conf import settings

from core.models import PageMeta
from django.urls import translate_url
from django.utils.translation import get_language


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


def seo(request):
    """
    Metadata halaman (model PageMeta dari /admin/) untuk title,
    description, Open Graph, dan noindex.

    Pencocokan: path persis dulu; bila tidak ada dan path berprefiks
    '/en/', coba path tanpa prefiks (baris tanpa prefiks berlaku untuk
    kedua bahasa). Tidak ada -> templat memakai default.
    """
    pm = PageMeta.objects.filter(path=request.path).first()
    if pm is None and request.path.startswith('/en/'):
        pm = PageMeta.objects.filter(path=request.path[3:]).first()
    ctx = {'page_meta': pm}
    if pm and pm.og_image:
        ctx['page_meta_og_image'] = request.build_absolute_uri(pm.og_image.url)
    return ctx
