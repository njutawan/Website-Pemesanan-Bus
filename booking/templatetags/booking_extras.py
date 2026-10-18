"""Template tag util: format Rupiah, durasi, akses dict, JSON-LD, in-text link."""
import json
import re

from django import template
from django.core.cache import cache
from django.utils.html import escape
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


TAG_RE = re.compile(r'(<[^>]+>)')


def _link_terms():
    """Peta istilah -> URL (cache 10 menit): frasa layanan + nama kota aktif."""
    terms = cache.get('seo:linkterms')
    if terms is None:
        from booking.models import City
        terms = [
            ('tiket bus', '/bus/'),
            ('rental mobil', '/rental/'),
            ('sewa mobil', '/rental/'),
        ]
        # hanya kota dgn rute aktif — target pillar pasti hidup (bukan 404)
        for c in City.objects.filter(departures__schedules__isnull=False).distinct():
            terms.append((c.name.lower(), f'/bus/rute/dari/{c.slug}/'))
        terms.sort(key=lambda t: len(t[0]), reverse=True)  # frasa panjang dulu
        cache.set('seo:linkterms', terms, 600)
    return terms


@register.filter
def autolink(value):
    """Tautkan istilah kunci pada PEMUNCULAN PERTAMA (in-text contextual link).

    * Teks di-escape dulu (aman terhadap HTML tersemat).
    * Hanya teks DI LUAR tag yang diproses; tidak menautkan di dalam teks
      anchor <a>...</a> yang sudah ada.
    * Setiap istilah ditautkan maksimal satu kali per nilai.
    * Untuk field teks polos (jawaban FAQ, deskripsi) — bukan blok HTML.
    """
    if not value:
        return value
    terms = _link_terms()
    used = set()
    inside_a = 0
    out = []
    for part in TAG_RE.split(escape(str(value))):
        if part.startswith('<'):
            if re.match(r'<a\b', part, re.I):
                inside_a += 1
            elif re.match(r'</a\b', part, re.I):
                inside_a = max(0, inside_a - 1)
            out.append(part)
            continue
        if inside_a:
            out.append(part)
            continue
        for term, url in terms:
            if term in used:
                continue
            m = re.search(re.escape(term), part, re.IGNORECASE)
            if m:
                part = (part[:m.start()] +
                        f'<a href="{url}">{m.group(0)}</a>' +
                        part[m.end():])
                used.add(term)
        out.append(part)
    return mark_safe(''.join(out))


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
