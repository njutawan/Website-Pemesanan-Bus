"""Sitemap XML untuk SEO: halaman statis, rute bus, dan armada rental."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from booking.models import Route
from rental.models import Vehicle


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'weekly'

    def items(self):
        return ['home', 'about', 'contact', 'rental:index']

    def location(self, item):
        return reverse(item)


class RouteSitemap(Sitemap):
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return Route.objects.all()

    def location(self, obj):
        return reverse('booking:route_detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


class VehicleSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return Vehicle.objects.filter(is_available=True)

    def location(self, obj):
        return reverse('rental:detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    'static': StaticViewSitemap,
    'routes': RouteSitemap,
    'vehicles': VehicleSitemap,
}
