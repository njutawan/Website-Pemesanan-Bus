"""Admin rental mobil."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from rental.models import RentalBooking, Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'year', 'seats', 'price_per_day',
                    'driver_fee_per_day', 'thumb', 'is_available')
    list_filter = ('category', 'transmission', 'is_available')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description=_('foto'))
    def thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:120px;border-radius:6px"/>', obj.image.url)
        return '—'


@admin.register(RentalBooking)
class RentalBookingAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'vehicle', 'pickup_date', 'return_date', 'days', 'with_driver',
        'contact_name', 'total_price', 'status', 'payment_method')
    list_filter = ('status', 'with_driver', 'vehicle__category')
    search_fields = ('code', 'contact_name', 'contact_phone')
    readonly_fields = ('code', 'created_at', 'updated_at', 'proof_preview')
    actions = ('confirm_payments', 'cancel_bookings')
    date_hierarchy = 'pickup_date'

    fieldsets = (
        (_('Pesanan'), {
            'fields': ('code', 'vehicle', 'pickup_date', 'return_date',
                       'pickup_location', 'with_driver', 'days',
                       'contact_name', 'contact_phone', 'contact_email'),
        }),
        (_('Pembayaran'), {
            'fields': ('total_price', 'payment_method', 'payment_proof',
                       'proof_preview', 'paid_at'),
        }),
        (_('Catatan admin'), {'fields': ('admin_note',)}),
    )

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
        for booking in queryset.filter(status=RentalBooking.Status.PENDING):
            booking.mark_confirmed()
            count += 1
        self.message_user(request, f'{count} pesanan sewa dikonfirmasi.')

    @admin.action(description=_('Batalkan pesanan yang dipilih'))
    def cancel_bookings(self, request, queryset):
        count = queryset.filter(
            status__in=[RentalBooking.Status.PENDING, RentalBooking.Status.CONFIRMED]
        ).update(status=RentalBooking.Status.CANCELLED)
        self.message_user(request, f'{count} pesanan dibatalkan.')
