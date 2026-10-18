"""Template tag util: format Rupiah, durasi, akses dict."""
from django import template
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
