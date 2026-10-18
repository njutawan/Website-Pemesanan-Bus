"""
Admin kustom Nusantara Trans: AdminSite + dasbor operasional.

Semua ModelAdmin (booking & rental) terdaftar pada `admin_site` ini, dan
halaman indeks /admin/ diganti menjadi dasbor: statistik, grafik 14 hari,
antrean verifikasi pembayaran, okupansi keberangkatan hari ini, dan
aktivitas terbaru.
"""
from datetime import timedelta

from django.contrib import admin
from django.contrib.redirects.admin import RedirectAdmin as DjangoRedirectAdmin
from django.contrib.redirects.models import Redirect
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from booking.models import Booking, BookingSeat
from core.models import PageMeta, SeoKeyword
from rental.models import RentalBooking


class NusantaraAdminSite(admin.AdminSite):
    site_header = _('Nusantara Trans — Panel Operasional')
    site_title = _('Nusantara Trans Admin')
    index_title = _('Dasbor')

    def index(self, request, extra_context=None):
        extra = build_dashboard_context()
        if extra_context:
            extra.update(extra_context)
        return super().index(request, extra_context=extra)


admin_site = NusantaraAdminSite(name='admin')


@admin.register(PageMeta, site=admin_site)
class PageMetaAdmin(admin.ModelAdmin):
    """Metadata SEO per halaman: title, description, OG image, noindex."""

    list_display = ('path', 'title', 'noindex', 'updated_at')
    list_editable = ('noindex',)
    search_fields = ('path', 'title', 'description')
    list_filter = ('noindex',)
    fieldsets = (
        (None, {'fields': ('path',),
                'description': _("Cocokkan persis dengan URL. '/bus/' berlaku untuk ID & EN; '/en/bus/' khusus EN. Halaman detail (rute/mobil) memakai judul objek.")}),
        (_('Konten SEO'), {'fields': ('title', 'description', 'og_image')}),
        (_('Indeks'), {'fields': ('noindex',)}),
    )


# Manajemen redirect — muncul di panel admin: /admin/ → "Redirects".
# Isi "old path" (URL lama) & "new path" (URL baru). Middleware bawaan
# memancarkan 301 permanen (terbaik untuk SEO) hanya untuk URL yang 404.
admin_site.register(Redirect, DjangoRedirectAdmin)


def build_dashboard_context() -> dict:
    """Kumpulkan semua data dasbor (ringan: query kecil, indeks menyala)."""
    today = timezone.localdate()
    since14 = today - timedelta(days=13)
    since30 = today - timedelta(days=30)
    month_start = today.replace(day=1)

    bk = Booking.objects.all()
    rt = RentalBooking.objects.all()

    # ---- Antrean verifikasi pembayaran (booking pending, terlama dulu) ----
    pending_qs = bk.filter(status=Booking.Status.PENDING).select_related(
        'schedule__route__origin', 'schedule__route__destination', 'schedule__bus')
    pending_list = list(pending_qs.order_by('created_at')[:10])
    for p in pending_list:
        p.has_proof_flag = bool(p.payment_proof)
        p.deadline_str = timezone.localtime(p.payment_deadline).strftime('%d %b %H:%M')
    n_pending_proof = (
        pending_qs.filter(payment_proof__isnull=False).exclude(payment_proof='').count())
    n_pending_noproof = pending_qs.count() - n_pending_proof

    # ---- Pendapatan bulan ini (semua layanan, status terkonfirmasi) ----
    revenue_month = (
        bk.filter(status=Booking.Status.CONFIRMED, paid_at__date__gte=month_start)
        .aggregate(s=Sum('total_price'))['s'] or 0) + (
        rt.filter(
            status__in=[RentalBooking.Status.CONFIRMED, RentalBooking.Status.COMPLETED],
            paid_at__date__gte=month_start)
        .aggregate(s=Sum('total_price'))['s'] or 0)

    # ---- Okupansi keberangkatan hari ini ----
    occ_rows = (
        BookingSeat.objects
        .filter(booking__travel_date=today,
                booking__status__in=Booking.LOCKING_STATUSES)
        .select_related('booking__schedule__bus',
                        'booking__schedule__route__origin',
                        'booking__schedule__route__destination'))
    occ = {}
    for item in occ_rows:
        entry = occ.setdefault(
            item.booking.schedule_id, {'schedule': item.booking.schedule, 'sold': 0})
        entry['sold'] += 1
    departures = sorted(occ.values(), key=lambda e: e['schedule'].departure_time)[:8]
    for e in departures:
        e['total'] = e['schedule'].bus.total_seats
        e['pct'] = int(round(e['sold'] * 100 / e['total'])) if e['total'] else 0
        e['full'] = e['sold'] >= e['total']

    # ---- Grafik 14 hari: booking baru & pendapatan terkonfirmasi ----
    per_day = {
        row['d']: row
        for row in (bk.annotate(d=TruncDate('created_at')).values('d')
                    .annotate(n=Count('id'),
                              rev=Sum('total_price',
                                      filter=Q(status=Booking.Status.CONFIRMED)))
                    .filter(d__gte=since14))
    }
    chart_days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    chart = {
        'labels': [d.strftime('%d/%m') for d in chart_days],
        'counts': [per_day.get(d, {'n': 0})['n'] for d in chart_days],
        'revenue': [int(per_day.get(d, {'rev': 0})['rev'] or 0) for d in chart_days],
    }

    status_donut = [
        {'label': str(Booking.Status.PENDING.label),
         'n': bk.filter(status=Booking.Status.PENDING).count(), 'color': '#f77f00'},
        {'label': str(Booking.Status.CONFIRMED.label),
         'n': bk.filter(status=Booking.Status.CONFIRMED).count(), 'color': '#198754'},
        {'label': str(Booking.Status.EXPIRED.label),
         'n': bk.filter(status=Booking.Status.EXPIRED).count(), 'color': '#adb5bd'},
        {'label': str(Booking.Status.CANCELLED.label),
         'n': bk.filter(status=Booking.Status.CANCELLED).count(), 'color': '#dc3545'},
    ]

    # ---- Rute terpopuler 30 hari ----
    top_routes = list(
        bk.filter(created_at__date__gte=since30)
        .values('schedule__route__origin__name', 'schedule__route__destination__name')
        .annotate(n=Count('id')).order_by('-n')[:5])

    return {
        'dash': {
            'bookings_today': bk.filter(created_at__date=today).count(),
            'n_pending_proof': n_pending_proof,
            'n_pending_noproof': n_pending_noproof,
            'n_rental_pending': rt.filter(status=RentalBooking.Status.PENDING).count(),
            'revenue_month': revenue_month,
            'departures': departures,
            'pending_list': pending_list,
            'chart': chart,
            'status_donut': status_donut,
            'recent_bookings': (
                bk.select_related('schedule__route__origin',
                                  'schedule__route__destination', 'schedule__bus')
                .order_by('-created_at')[:8]),
            'recent_rentals': (
                rt.select_related('vehicle').order_by('-created_at')[:5]),
            'top_routes': top_routes,
        },
    }


@admin.register(SeoKeyword, site=admin_site)
class SeoKeywordAdmin(admin.ModelAdmin):
    """Kata kunci auto-link: perubahan otomatis menghapus cache peta."""

    list_display = ('phrase', 'url', 'is_active', 'updated')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('phrase', 'url')
    ordering = ('phrase',)
