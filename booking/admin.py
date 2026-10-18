"""Admin booking: verifikasi pembayaran manual, ekspor CSV, dasbor terhubung."""
import csv

from django.contrib import admin, messages
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from booking.models import (
    Booking, BookingSeat, Bus, City, Route, Schedule, Seat,
)
from core.admin import admin_site
from core.audit import log_event
from core.validators import csv_safe


class ProofStatusFilter(admin.SimpleListFilter):
    """Filter bukti pembayaran: sudah unggah / belum unggah."""
    title = _('bukti pembayaran')
    parameter_name = 'proof'

    def lookups(self, request, model_admin):
        return [('1', _('Sudah unggah')), ('0', _('Belum unggah'))]

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(payment_proof__isnull=False).exclude(payment_proof='')
        if self.value() == '0':
            return queryset.filter(Q(payment_proof__isnull=True) | Q(payment_proof=''))
        return queryset


@admin.register(City, site=admin_site)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'is_popular')
    list_editable = ('is_popular',)
    search_fields = ('name', 'province')
    prepopulated_fields = {'slug': ('name',)}


class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 0
    fields = ('bus', 'departure_time', 'arrival_time', 'price', 'is_active')
    autocomplete_fields = ('bus',)


@admin.register(Route, site=admin_site)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'distance_km', 'duration_display', 'n_schedules')
    inlines = [ScheduleInline]
    search_fields = ('origin__name', 'destination__name')
    list_filter = ('origin',)
    list_select_related = ('origin', 'destination')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(Count('schedules', distinct=True))

    @admin.display(description=_('jadwal aktif'), ordering='schedules__count')
    def n_schedules(self, obj):
        return obj.schedules__count


@admin.register(Bus, site=admin_site)
class BusAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'plate_number', 'bus_class', 'total_seats', 'is_active')
    list_filter = ('bus_class', 'is_active')
    search_fields = ('name', 'code', 'plate_number')


@admin.register(Seat, site=admin_site)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('bus', 'label', 'row', 'col')
    list_filter = ('bus',)
    search_fields = ('label',)
    list_select_related = ('bus',)


@admin.register(Schedule, site=admin_site)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'route', 'bus', 'departure_time', 'arrival_time',
        'duration_display', 'price', 'is_active')
    list_filter = ('is_active', 'bus__bus_class')
    search_fields = ('route__origin__name', 'route__destination__name', 'bus__code')
    autocomplete_fields = ('route', 'bus')
    list_select_related = ('route__origin', 'route__destination', 'bus')


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    fields = ('seat',)
    readonly_fields = ('seat',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking, site=admin_site)
class BookingAdmin(admin.ModelAdmin):
    change_form_template = 'admin/booking/booking_change_form.html'
    list_display = (
        'code', 'route_display', 'travel_date', 'contact_name',
        'seats_qty', 'total_price', 'status', 'has_proof', 'created_at')
    list_filter = ('status', 'payment_method', 'travel_date', ProofStatusFilter)
    search_fields = ('code', 'contact_name', 'contact_phone')
    autocomplete_fields = ('schedule',)
    list_select_related = (
        'schedule__route__origin', 'schedule__route__destination', 'schedule__bus')
    readonly_fields = (
        'code', 'created_at', 'updated_at', 'payment_deadline_display',
        'proof_preview')
    inlines = [BookingSeatInline]
    actions = ('confirm_payments', 'cancel_bookings', 'export_csv')
    date_hierarchy = 'travel_date'
    list_per_page = 25
    save_on_top = True

    fieldsets = (
        (_('Booking'), {
            'fields': ('code', 'schedule', 'travel_date', 'status',
                       'contact_name', 'contact_phone', 'contact_email'),
        }),
        (_('Pembayaran'), {
            'fields': ('total_price', 'payment_method', 'payment_proof',
                       'proof_preview', 'paid_at', 'payment_deadline_display'),
        }),
        (_('Catatan admin'), {'fields': ('admin_note',)}),
        (_('Waktu'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description=_('rute'), ordering='schedule__route')
    def route_display(self, obj):
        return f'{obj.schedule.route.origin.name} → {obj.schedule.route.destination.name}'

    @admin.display(description=_('bukti'), boolean=True)
    def has_proof(self, obj):
        return bool(obj.payment_proof)

    @admin.display(description=_('batas bayar'))
    def payment_deadline_display(self, obj):
        return timezone_deadline(obj)

    @admin.display(description=_('bukti'))
    def proof_preview(self, obj):
        from django.utils.html import format_html
        if obj.payment_proof:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width:280px;'
                'border-radius:8px;border:1px solid #ddd"/></a>',
                obj.payment_proof.url, obj.payment_proof.url)
        return _('(belum ada)')

    def response_change(self, request, obj):
        """Tombol 'Konfirmasi pembayaran ini' di halaman edit (1-klik verifikasi)."""
        if '_confirm' in request.POST:
            if obj.status == Booking.Status.PENDING:
                obj.mark_confirmed()
                log_event('PAYMENT_CONFIRMED', request=request, target=obj.code,
                          metadata={'channel': 'bus'})
                self.message_user(
                    request, _('Booking %s dikonfirmasi.') % obj.code,
                    messages.SUCCESS)
            else:
                self.message_user(
                    request, _('Booking tidak berstatus menunggu pembayaran.'),
                    messages.WARNING)
            return HttpResponseRedirect(request.path_info)
        return super().response_change(request, obj)

    @admin.action(description=_('Konfirmasi pembayaran yang dipilih'))
    def confirm_payments(self, request, queryset):
        count = 0
        for booking in queryset.filter(status=Booking.Status.PENDING):
            booking.mark_confirmed()
            log_event('PAYMENT_CONFIRMED', request=request, target=booking.code,
                      metadata={'channel': 'bus', 'batch': True})
            count += 1
        self.message_user(request, f'{count} booking dikonfirmasi.')

    @admin.action(description=_('Batalkan booking yang dipilih'))
    def cancel_bookings(self, request, queryset):
        count = queryset.filter(status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]) \
            .update(status=Booking.Status.CANCELLED)
        log_event('PAYMENT_CANCELLED', request=request, success=True,
                  metadata={'channel': 'bus', 'count': count, 'batch': True})
        self.message_user(request, f'{count} booking dibatalkan.')

    @admin.action(description=_('Ekspor CSV yang dipilih'))
    def export_csv(self, request, queryset):
        """Ekspor untuk Excel Indonesia (delimiter ';' + BOM UTF-8)."""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="booking-nusantara.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Kode', 'Rute', 'Tanggal', 'Jam', 'Bus', 'Kursi', 'Nama', 'WhatsApp',
            'Email', 'Total', 'Status', 'Metode', 'Dibayar Pada', 'Dibuat'])
        for b in queryset.select_related(
                'schedule__route__origin', 'schedule__route__destination',
                'schedule__bus').prefetch_related('seat_items__seat'):
            seats = ','.join(i.seat.label for i in b.seat_items.all())
            writer.writerow([
                b.code,
                f'{b.schedule.route.origin.name} → {b.schedule.route.destination.name}',
                b.travel_date.strftime('%Y-%m-%d'),
                b.schedule.departure_time.strftime('%H:%M'),
                b.schedule.bus.name, seats,
                csv_safe(b.contact_name), csv_safe(b.contact_phone),
                csv_safe(b.contact_email), int(b.total_price),
                b.get_status_display(), b.payment_method or '-',
                timezone_local(b.paid_at), timezone_local(b.created_at),
            ])
        log_event('EXPORT', request=request, success=True,
                  metadata={'channel': 'bus', 'rows': queryset.count()})
        return response


def timezone_deadline(obj):
    from django.utils import timezone as tz
    return tz.localtime(obj.payment_deadline).strftime('%d %b %Y %H:%M')


def timezone_local(dt):
    from django.utils import timezone as tz
    if not dt:
        return '-'
    return tz.localtime(dt).strftime('%Y-%m-%d %H:%M')
