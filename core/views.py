"""Halaman statis utama: beranda, tentang, kontak, robots.txt."""
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Min
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from booking.forms import SearchForm
from core.seo import HOME_CRUMB, breadcrumb_items, breadcrumb_schema, local_business_schema
from booking.models import Booking, Bus, City, Route, Schedule
from rental.models import RentalBooking, Vehicle

TTL = getattr(settings, 'CACHE_TTL_DEFAULT', 600)


def get_home_data():
    """Data beranda di-cache (queryset -> list agar aman disimpan).

    Mengurangi 6+ query per request menjadi 0 saat cache hangat —
    menjaga TTFB. TTL mengikuti CACHE_TTL_DEFAULT (default 10 menit).
    """

    def build():
        routes = list(
            Route.objects
            .annotate(n_schedules=Count('schedules', distinct=True),
                      min_price=Min('schedules__price'))
            .filter(n_schedules__gt=0)
            .select_related('origin', 'destination')
            .order_by('origin__name', 'destination__name')[:6])
        vehicles = list(Vehicle.objects.filter(is_available=True)[:3])
        stats = {
            'cities': City.objects.count(),
            'routes': Route.objects.count(),
            'buses': Bus.objects.count(),
            'vehicles': Vehicle.objects.count(),
        }
        return routes, vehicles, stats

    return cache.get_or_set('home:data', build, TTL)


class HomeView(TemplateView):
    """Beranda: hero + form pencarian, rute populer, armada, rental, cara pesan."""
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        routes, vehicles, stats = get_home_data()
        ctx.update(
            form=SearchForm(),  # kartu pencarian di hero — wajib ada!
            popular_routes=routes,
            featured_vehicles=vehicles,
            bus_classes=Bus.BusClass.choices,
            stats=stats,
            schema_local_business=local_business_schema(self.request),
        )
        return ctx


class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schema_breadcrumbs'] = breadcrumb_schema(
            self.request, breadcrumb_items(HOME_CRUMB, (_('Tentang'), None)))
        return ctx


class ContactView(TemplateView):
    template_name = 'contact.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schema_breadcrumbs'] = breadcrumb_schema(
            self.request, breadcrumb_items(HOME_CRUMB, (_('Kontak'), None)))
        return ctx


class RobotsView(TemplateView):
    template_name = 'robots.txt'
    content_type = 'text/plain'

    def get_context_data(self, **kwargs):
        return {'sitemap_url': self.request.build_absolute_uri('/sitemap.xml')}


def csrf_failure(request, reason='', template_name='csrf_failure.html'):
    """Halaman ramah saat verifikasi CSRF gagal (mis. cookie diblokir iframe)."""
    return render(request, 'csrf_failure.html', status=403)


def error_404(request, exception=None):
    """Halaman 404 branded (status tetap 404 untuk SEO)."""
    return render(request, '404.html', status=404)


def error_500(request):
    """Halaman 500 branded (hanya aktif saat DEBUG=False)."""
    return render(request, '500.html', status=500)
