"""Helper SEO: schema JSON-LD dibangun di context view, dirender templat."""
from django.utils.translation import gettext_lazy as _

# butir breadcrumb: (nama, path-atau-None) — None = halaman saat ini
HOME_CRUMB = (_('Beranda'), '/')


def breadcrumb_items(*crumbs):
    """((nama, path|None), ...) -> list dict {'name','url'} utk templat/schema."""
    return [{'name': str(n), 'url': u} for n, u in crumbs]


def breadcrumb_schema(request, items):
    """List breadcrumb -> dict schema.org/BreadcrumbList (URL absolut)."""
    elements = []
    for i, it in enumerate(items, start=1):
        el = {'@type': 'ListItem', 'position': i, 'name': it['name']}
        if it.get('url'):
            el['item'] = request.build_absolute_uri(it['url'])
        elements.append(el)
    return {'@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': elements}


def local_business_schema(request):
    """Schema Organization+LocalBusiness untuk beranda (nama, logo, kontak, jam)."""
    from django.conf import settings
    return {
        '@context': 'https://schema.org',
        '@type': ['Organization', 'LocalBusiness'],
        '@id': request.build_absolute_uri('/#organization'),
        'name': settings.SITE_NAME,
        'url': request.build_absolute_uri('/'),
        'logo': request.build_absolute_uri(settings.STATIC_URL + 'img/logo.png'),
        'image': request.build_absolute_uri(settings.STATIC_URL + 'img/hero-bus.jpg'),
        'description': settings.SITE_TAGLINE,
        'telephone': settings.CONTACT_PHONE,
        'email': settings.CONTACT_EMAIL,
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': settings.CONTACT_ADDRESS,
            'addressCountry': 'ID',
        },
        'openingHoursSpecification': [{
            '@type': 'OpeningHoursSpecification',
            'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                          'Friday', 'Saturday', 'Sunday'],
            'opens': '07:00',
            'closes': '21:00',
        }],
        'contactPoint': [{
            '@type': 'ContactPoint',
            'contactType': 'customer service',
            'telephone': settings.CONTACT_PHONE,
            'email': settings.CONTACT_EMAIL,
            'availableLanguage': ['id', 'en'],
        }],
    }
