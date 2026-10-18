"""Halaman statis utama: beranda, tentang, kontak, robots.txt."""
from django.conf import settings
from django.db.models import Count, Min
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from booking.models import Booking, Bus, City, Route, Schedule
from rental.models import RentalBooking, Vehicle


class HomeView(TemplateView):
    """Beranda: hero + form pencarian, rute populer, armada, rental, cara pesan."""
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        routes = (
            Route.objects
            .annotate(n_schedules=Count('schedules', distinct=True),
                      min_price=Min('schedules__price'))
            .filter(n_schedules__gt=0)
            .select_related('origin', 'destination')
            .order_by('origin__name', 'destination__name')
        )
        ctx.update(
            popular_routes=routes[:6],
            featured_vehicles=Vehicle.objects.filter(is_available=True)[:3],
            bus_classes=Bus.BusClass.choices,
            stats={
                'cities': City.objects.count(),
                'routes': Route.objects.count(),
                'buses': Bus.objects.count(),
                'vehicles': Vehicle.objects.count(),
            },
        )
        return ctx


class AboutView(TemplateView):
    template_name = 'about.html'


class ContactView(TemplateView):
    template_name = 'contact.html'


class RobotsView(TemplateView):
    template_name = 'robots.txt'
    content_type = 'text/plain'

    def get_context_data(self, **kwargs):
        return {'sitemap_url': self.request.build_absolute_uri('/sitemap.xml')}


def csrf_failure(request, reason='', template_name='csrf_failure.html'):
    """Halaman ramah saat verifikasi CSRF gagal (mis. cookie diblokir iframe)."""
    return render(request, 'csrf_failure.html', status=403)
