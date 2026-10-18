"""Auto-linking internal dinamis (HTML-safe, anti self-link, batas densitas).

Sumber istilah:
  * DB ``core.SeoKeyword`` (dikelola admin; cache 'seo:db_keywords' 600s,
    dibersihkan sinyal saat data berubah), dan
  * pillar kota dinamis — hanya kota ber-rute aktif agar target tak 404
    (cache 'seo:linkterms' 600s).

Aturan pemasangan tautan:
  * frasa terpanjang diprioritaskan (frasa multi-kata tak terpotong);
  * hanya PEMUNCULAN PERTAMA per istilah (bukan spam);
  * teks di dalam <a>...</a> dan tag HTML lain tidak disentuh;
  * anti self-link: halaman tidak menautkan ke dirinya sendiri;
  * batas densitas: maks 1 link per 250 kata, rentang 1-4 per blok konten
    (≈ 2-4 link per 1000 kata).
"""
import math
import re

from django import template
from django.core.cache import cache
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

TAG_RE = re.compile(r'(<[^>]+>)')
WORD_RE = re.compile(r'\w+', re.UNICODE)
MAX_LINKS = 4


def _db_terms():
    """Frasa->URL dari model SeoKeyword (cache 600s; sinyal memvalidasi)."""
    terms = cache.get('seo:db_keywords')
    if terms is None:
        from core.models import SeoKeyword
        terms = list(SeoKeyword.objects.filter(is_active=True)
                     .values_list('phrase', 'url'))
        cache.set('seo:db_keywords', terms, 600)
    return terms


def _city_terms():
    """Nama kota -> pillar, HANYA kota dengan rute aktif (target pasti hidup)."""
    terms = cache.get('seo:linkterms')
    if terms is None:
        from booking.models import City
        terms = [(c.name.lower(), f'/bus/rute/dari/{c.slug}/')
                 for c in City.objects.filter(
                     departures__schedules__isnull=False).distinct()]
        cache.set('seo:linkterms', terms, 600)
    return terms


def _all_terms():
    """Gabungan DB + kota, urut frasa TERPANJANG dulu; frasa unik."""
    seen, merged = set(), []
    for term, url in _db_terms() + _city_terms():
        key = term.casefold()
        if key and key not in seen:
            seen.add(key)
            merged.append((term, url))
    merged.sort(key=lambda t: len(t[0]), reverse=True)
    return merged


def _norm(path):
    """Normalisasi path utk perbandingan self-link."""
    if not path:
        return ''
    p = path.partition('?')[0].partition('#')[0]
    return p if p.endswith('/') else p + '/'


@register.filter
def auto_internal_link(value, request_path=None):
    """Tautkan istilah kunci pada pemunculan pertama — aman terhadap HTML.

    Pakai: ``{{ konten|auto_internal_link:request.path }}`` — argumen
    mencegah self-link (halaman menautkan ke dirinya sendiri).
    """
    if not value:
        return value
    text = escape(str(value))
    terms = _all_terms()
    if not terms:
        return mark_safe(text)

    self_path = _norm(request_path)
    words = len(WORD_RE.findall(TAG_RE.sub(' ', text)))
    budget = max(1, min(MAX_LINKS, math.ceil(words / 250)))  # densitas
    used = set()
    inside_a = 0
    out = []
    for part in TAG_RE.split(text):
        if part.startswith('<'):
            if re.match(r'<a\b', part, re.I):
                inside_a += 1
            elif re.match(r'</a\b', part, re.I):
                inside_a = max(0, inside_a - 1)
            out.append(part)
            continue
        if inside_a or budget <= 0:
            out.append(part)
            continue
        for term, url in terms:
            if term in used or budget <= 0:
                continue
            # Output validation: hanya path internal absolut. Data DB yang
            # disusupi (mis. javascript:) tidak boleh masuk atribut href.
            if (not url or not url.startswith('/') or url.startswith('//')
                    or ':' in url.split('?', 1)[0]):
                continue
            if _norm(url) == self_path or url == '/':
                continue  # anti self-link
            m = re.search(re.escape(term), part, re.IGNORECASE)
            if m:
                safe_url = escape(url)
                part = (part[:m.start()] +
                        f'<a class="ilink" href="{safe_url}">{m.group(0)}</a>' +
                        part[m.end():])
                used.add(term)
                budget -= 1
        out.append(part)
    return mark_safe(''.join(out))
