"""Template tag util: format Rupiah, durasi, akses dict, JSON-LD schema."""
import json

from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def to_idr(value):
    """1234500 -> 'Rp 1.234.500' (format Indonesia)."""
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return value
    return f'Rp {amount:,}'.replace(',', '.')


@register.filter
def dur(minutes):
    """165 -> '2j 45m' (ID) / '2h 45m' (EN)."""
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        return minutes
    h, m = divmod(minutes, 60)
    if minutes >= 24 * 60:
        d, h = divmod(h, 24)
        return (_('{}d {}h') if m == 0 else _('{}d {}h {}m')).format(d, h, m)
    return (_('{}h') if m == 0 else _('{}h {}m')).format(h, m)


@register.filter
def get_item(dictionary, key):
    """{{ mydict|get_item:key }} — akses dict by key dari template."""
    if dictionary is None:
        return None
    return dictionary.get(key)


STATUS_CLASS = {
    'PENDING': 'warn',
    'CONFIRMED': 'ok',
    'EXPIRED': 'muted',
    'CANCELLED': 'bad',
    'COMPLETED': 'ok',
}


@register.filter
def status_class(status):
    """'PENDING' -> 'warn' — kelas warna badge status untuk dasbor admin."""
    return STATUS_CLASS.get(status, 'muted')


@register.filter
def webp_url(url):
    """/media/a.jpg -> /media/a.webp — URL varian WebP dari gambar media."""
    if not url or not isinstance(url, str):
        return url
    head, sep, ext = url.rpartition('.')
    if len(ext) > 5 or not head:
        return url
    return f'{head}.webp'


@register.simple_tag
def nav_active(request, *prefixes):
    """{% nav_active request 'booking:' %} -> 'active' bila halaman cocok."""
    view = getattr(getattr(request, 'resolver_match', None), 'view_name', '') or ''
    for p in prefixes:
        if view == p or view.startswith(p):
            return 'active'
    return ''


@register.filter
def jsonld(value):
    """Dump dict Python -> JSON aman utk <script type="application/ld+json">.

    Meng-escape '</', '<', '>', '&' serta U+2028/2029 (pola sama dengan
    filter json_script bawaan Django) agar struktur data tidak bisa
    "keluar" dari tag script.
    """
    if value is None:
        return ''
    text = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    escapes = (
        ('<', r'\u003c'), ('>', r'\u003e'), ('&', r'\u0026'),
        ("'", r'\u0027'),
    )
    for old, new in escapes:
        text = text.replace(old, new)
    text = text.replace('\u2028', r'\u2028').replace('\u2029', r'\u2029')
    return mark_safe(text)
