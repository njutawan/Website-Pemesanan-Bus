"""Sitemap XML (django.contrib.sitemaps): statis, rute bus, armada rental.

Berbasis query model — rute/mobil baru otomatis terdaftar, lengkap
lastmod (field updated_at), changefreq, dan priority per URL.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from booking.models import Route
from rental.models import Vehicle


class StaticViewSitemap(Sitemap):
    """Halaman statis; tiap URL membawa priority & changefreq sendiri."""

    def items(self):
        return [
            ('home', 1.0, 'daily'),
            ('booking:search', 0.9, 'daily'),
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
    'routes': RouteSitemap,
    'vehicles': VehicleSitemap,
}
