"""Sitemap XML (django.contrib.sitemaps): statis, rute bus, armada rental.

Berbasis query model — rute/mobil baru otomatis terdaftar, lengkap
lastmod (field updated_at), changefreq, dan priority per URL.
"""
from django.contrib.sitemaps import Sitemap
from django.db.models import Max
from django.urls import reverse

from booking.models import City, Route
from rental.models import Vehicle


class StaticViewSitemap(Sitemap):
    """Halaman statis; tiap URL membawa priority & changefreq sendiri."""

    def items(self):
        return [
            ('home', 1.0, 'daily'),
            ('booking:search', 0.9, 'daily'),
            ('booking:route_hub', 0.8, 'weekly'),
            ('booking:check', 0.4, 'monthly'),
            ('rental:index', 0.9, 'daily'),
            ('about', 0.5, 'monthly'),
            ('contact', 0.5, 'monthly'),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class RouteSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return Route.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


class CityRouteSitemap(Sitemap):
    """Pillar per kota asal (silo kategori)."""
    priority = 0.7
    changefreq = 'weekly'

    def items(self):
        # related_name FK Route.origin = 'departures'
        return City.objects.filter(departures__schedules__isnull=False).distinct()

    def location(self, obj):
        return reverse('booking:city_routes', kwargs={'city_slug': obj.slug})

    def lastmod(self, obj):
        # City tidak punya updated_at -> pakai rute terbaru miliknya
        return obj.departures.aggregate(m=Max('updated_at'))['m']


class VehicleSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return Vehicle.objects.filter(is_available=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    'static': StaticViewSitemap,
    'cities': CityRouteSitemap,
    'routes': RouteSitemap,
    'vehicles': VehicleSitemap,
}
