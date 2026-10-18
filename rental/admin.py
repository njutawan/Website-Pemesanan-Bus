"""Admin rental mobil: verifikasi 1-klik, filter bukti, ekspor CSV."""
import csv

from django.contrib import admin, messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from rental.models import RentalBooking, Vehicle
from core.admin import admin_site


class RentalProofFilter(admin.SimpleListFilter):
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


@admin.register(Vehicle, site=admin_site)
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


@admin.register(RentalBooking, site=admin_site)
class RentalBookingAdmin(admin.ModelAdmin):
    change_form_template = 'admin/rental/rentalbooking_change_form.html'
    list_display = (
        'code', 'vehicle', 'pickup_date', 'return_date', 'days', 'with_driver',
        'contact_name', 'total_price', 'status', 'has_proof', 'payment_method')
    list_filter = ('status', 'with_driver', 'vehicle__category', RentalProofFilter)
    search_fields = ('code', 'contact_name', 'contact_phone')
    autocomplete_fields = ('vehicle',)
    list_select_related = ('vehicle',)
    readonly_fields = ('code', 'created_at', 'updated_at', 'proof_preview')
    actions = ('confirm_payments', 'cancel_bookings', 'export_csv')
    date_hierarchy = 'pickup_date'
    list_per_page = 25
    save_on_top = True

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

    @admin.display(description=_('bukti'), boolean=True)
    def has_proof(self, obj):
        return bool(obj.payment_proof)

    @admin.display(description=_('bukti'))
    def proof_preview(self, obj):
        if obj.payment_proof:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width:280px;'
                'border-radius:8px;border:1px solid #ddd"/></a>',
                obj.payment_proof.url, obj.payment_proof.url)
        return _('(belum ada)')

    def response_change(self, request, obj):
        """Tombol 'Konfirmasi pembayaran sewa ini' di halaman edit."""
        if '_confirm' in request.POST:
            if obj.status == RentalBooking.Status.PENDING:
                obj.mark_confirmed()
                self.message_user(
                    request, _('Pesanan sewa %s dikonfirmasi.') % obj.code,
                    messages.SUCCESS)
            else:
                self.message_user(
                    request, _('Pesanan sewa tidak berstatus menunggu pembayaran.'),
                    messages.WARNING)
            return HttpResponseRedirect(request.path_info)
        return super().response_change(request, obj)

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

    @admin.action(description=_('Ekspor CSV yang dipilih'))
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="sewa-nusantara.csv"'
        response.write('\ufeff')
        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            'Kode', 'Mobil', 'Ambil', 'Kembali', 'Hari', 'Sopir', 'Lokasi',
            'Nama', 'WhatsApp', 'Total', 'Status', 'Metode', 'Dibuat'])
        for b in queryset.select_related('vehicle'):
            writer.writerow([
                b.code, b.vehicle.name,
                b.pickup_date.strftime('%Y-%m-%d'),
                b.return_date.strftime('%Y-%m-%d'),
                b.days, 'Ya' if b.with_driver else 'Tidak', b.pickup_location,
                b.contact_name, b.contact_phone, int(b.total_price),
                b.get_status_display(), b.payment_method or '-',
                b.created_at.strftime('%Y-%m-%d %H:%M'),
            ])
        return response
