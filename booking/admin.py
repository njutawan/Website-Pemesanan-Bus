"""Admin booking: verifikasi pembayaran manual (aksi konfirmasi/batalkan)."""
from django.contrib import admin
from django.db.models import Count
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from booking.models import (
    Booking, BookingSeat, Bus, City, Route, Schedule, Seat,
)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'is_popular')
    list_editable = ('is_popular',)
    search_fields = ('name', 'province')
    prepopulated_fields = {'slug': ('name',)}


class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 0
    fields = ('bus', 'departure_time', 'arrival_time', 'price', 'is_active')


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'distance_km', 'duration_display', 'n_schedules')
    inlines = [ScheduleInline]
    search_fields = ('origin__name', 'destination__name')
    list_filter = ('origin',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(Count('schedules', distinct=True))

    @admin.display(description=_('jadwal aktif'), ordering='schedules__count')
    def n_schedules(self, obj):
        return obj.schedules__count


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'plate_number', 'bus_class', 'total_seats', 'is_active')
    list_filter = ('bus_class', 'is_active')
    search_fields = ('name', 'code', 'plate_number')


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('bus', 'label', 'row', 'col')
    list_filter = ('bus',)
    search_fields = ('label',)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        'route', 'bus', 'departure_time', 'arrival_time',
        'duration_display', 'price', 'is_active')
    list_filter = ('is_active', 'bus__bus_class')
    search_fields = ('route__origin__name', 'route__destination__name')


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    fields = ('seat',)
    readonly_fields = ('seat',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'route_display', 'travel_date', 'contact_name',
        'seats_qty', 'total_price', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'travel_date')
    search_fields = ('code', 'contact_name', 'contact_phone')
    readonly_fields = (
        'code', 'created_at', 'updated_at', 'payment_deadline_display',
        'proof_preview')
    inlines = [BookingSeatInline]
    actions = ('confirm_payments', 'cancel_bookings')
    date_hierarchy = 'travel_date'

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

    @admin.display(description=_('batas bayar'))
    def payment_deadline_display(self, obj):
        return timezone.localtime(obj.payment_deadline).strftime('%d %b %Y %H:%M')

    @admin.display(description=_('bukti'))
    def proof_preview(self, obj):
        if obj.payment_proof:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width:280px;'
                'border-radius:8px;border:1px solid #ddd"/></a>',
                obj.payment_proof.url, obj.payment_proof.url)
        return _('(belum ada)')

    @admin.action(description=_('Konfirmasi pembayaran yang dipilih'))
    def confirm_payments(self, request, queryset):
        count = 0
        for booking in queryset.filter(status=Booking.Status.PENDING):
            booking.mark_confirmed()
            count += 1
        self.message_user(request, f'{count} booking dikonfirmasi.')

    @admin.action(description=_('Batalkan booking yang dipilih'))
    def cancel_bookings(self, request, queryset):
        count = queryset.filter(status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED]) \
            .update(status=Booking.Status.CANCELLED)
        self.message_user(request, f'{count} booking dibatalkan.')
