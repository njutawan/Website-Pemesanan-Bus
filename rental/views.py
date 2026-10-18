"""View rental: katalog mobil, detail, form sewa, upload bukti bayar."""
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, View

from core.audit import log_event
from core.forms import PaymentProofForm
from core.private_media import grant_private_media_access
from core.validators import clean_public_code
from core.seo import HOME_CRUMB, breadcrumb_items, breadcrumb_schema
from rental.forms import RentalForm
from rental.models import RentalBooking, Vehicle, has_overlapping_rental


class VehicleListView(TemplateView):
    """Katalog mobil rental dengan filter kategori (?kategori=MPV)."""
    template_name = 'rental/index.html'

    @method_decorator(cache_page(60 * 15))
    def get(self, request):
        category = request.GET.get('kategori', '')
        qs = Vehicle.objects.filter(is_available=True)
        if category in Vehicle.Category.values:
            qs = qs.filter(category=category)
        return render(request, self.template_name, {
            'vehicles': qs,
            'categories': Vehicle.Category.choices,
            'active_category': category,
            'schema_breadcrumbs': breadcrumb_schema(request, breadcrumb_items(
                HOME_CRUMB, (_('Rental Mobil'), None))),
        })


class VehicleDetailView(TemplateView):
    """Detail mobil + tombol sewa."""
    template_name = 'rental/detail.html'

    def get(self, request, slug):
        vehicle = get_object_or_404(Vehicle, slug=slug, is_available=True)
        others = Vehicle.objects.filter(is_available=True).exclude(pk=vehicle.pk)[:3]
        url = request.build_absolute_uri(vehicle.get_absolute_url())
        return render(request, self.template_name, {
            'vehicle': vehicle, 'other_vehicles': others,
            'schema_breadcrumbs': breadcrumb_schema(request, breadcrumb_items(
                HOME_CRUMB, (_('Rental Mobil'), '/rental/'), (vehicle.name, None))),
            'schema_product': {
                '@context': 'https://schema.org',
                '@type': 'Product',
                'name': vehicle.name,
                'image': request.build_absolute_uri(vehicle.image.url),
                'description': vehicle.description or _(
                    'Sewa %(name)s harian dengan harga terbaik.') % {'name': vehicle.name},
                'brand': {'@type': 'Brand', 'name': settings.SITE_NAME},
                'url': url,
                'offers': {
                    '@type': 'Offer',
                    'priceCurrency': 'IDR',
                    'price': str(vehicle.price_per_day),
                    'availability': ('https://schema.org/InStock' if vehicle.is_available
                                     else 'https://schema.org/OutOfStock'),
                    'url': url,
                },
            },
        })


class CreateRentalView(View):
    """Form sewa (GET) → buat RentalBooking (POST) → halaman bayar."""
    template_name = 'rental/form.html'

    def get_vehicle(self, slug):
        return get_object_or_404(Vehicle, slug=slug, is_available=True)

    @staticmethod
    def calc_total(vehicle, days, with_driver):
        total = vehicle.price_per_day * days
        if with_driver:
            total += vehicle.driver_fee_per_day * days
        return total

    def get(self, request, slug):
        vehicle = self.get_vehicle(slug)
        form = RentalForm(initial={
            'pickup_date': None,
            'return_date': None,
        })
        return render(request, self.template_name, {
            'vehicle': vehicle, 'form': form,
        })

    def post(self, request, slug):
        vehicle = self.get_vehicle(slug)
        form = RentalForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name,
                          {'vehicle': vehicle, 'form': form}, status=400)

        cleaned = form.cleaned_data
        # Kunci baris unit lalu periksa overlap & buat booking secara atomik:
        # dua request bersamaan untuk unit yang sama tidak bisa sama-sama
        # lolos cek dan berakhir sebagai double-booking.
        with transaction.atomic():
            locked = get_object_or_404(
                Vehicle.objects.select_for_update(),
                pk=vehicle.pk, is_available=True)
            if has_overlapping_rental(
                    locked, cleaned['pickup_date'], cleaned['return_date']):
                form.add_error(
                    None,
                    _('Maaf, unit ini sudah dipesan pada tanggal yang tumpang tindih. Silakan pilih tanggal atau unit lain.'))
                return render(request, self.template_name,
                              {'vehicle': locked, 'form': form}, status=409)

            booking = RentalBooking.objects.create(
                vehicle=locked,
                pickup_date=cleaned['pickup_date'],
                return_date=cleaned['return_date'],
                pickup_location=cleaned['pickup_location'],
                with_driver=cleaned['with_driver'],
                contact_name=cleaned['contact_name'],
                contact_phone=cleaned['contact_phone'],
                contact_email=cleaned['contact_email'],
                days=cleaned['days'],
                total_price=self.calc_total(
                    locked, cleaned['days'], cleaned['with_driver']),
            )
        log_event(
            'BOOKING_CREATED', request=request, target=booking.code,
            metadata={
                'channel': 'rental',
                'vehicle_id': locked.pk,
                'days': cleaned['days'],
                'with_driver': bool(cleaned['with_driver']),
            })
        messages.success(
            request, _('Pesanan sewa berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.'))
        detail_url = reverse(
            'rental:detail_booking', kwargs={'code': booking.code})
        return redirect(f'{detail_url}?{urlencode({"baru": 1})}')


@method_decorator(never_cache, name='dispatch')
class RentalDetailView(TemplateView):
    """Detail pesanan sewa + instruksi pembayaran + upload bukti."""
    template_name = 'rental/detail_booking.html'

    def get(self, request, code):
        try:
            code = clean_public_code(code)
        except ValidationError:
            raise Http404('Pesanan tidak ditemukan.')
        booking = get_object_or_404(
            RentalBooking.objects.select_related('vehicle'), code__iexact=code)
        # Kode sewa adalah kredensial pemilik halaman ini: izinkan sesi ini
        # memuat thumbnail buktinya sendiri dari media privat.
        grant_private_media_access(
            request, booking.payment_proof.name if booking.payment_proof else None)
        return render(request, self.template_name, {
            'booking': booking,
            'proof_form': PaymentProofForm(initial={'payment_method': 'bca'}),
            'is_new': request.GET.get('baru') == '1',
        })


class UploadRentalProofView(View):
    """Upload bukti transfer/QRIS untuk sewa (diverifikasi admin)."""

    def post(self, request, code):
        try:
            code = clean_public_code(code)
        except ValidationError:
            raise Http404('Pesanan tidak ditemukan.')
        booking = get_object_or_404(RentalBooking, code__iexact=code)
        if booking.status != RentalBooking.Status.PENDING:
            messages.error(request, _('Pesanan ini sudah tidak bisa menerima unggahan bukti.'))
            return redirect('rental:detail_booking', code=booking.code)
        if booking.is_payment_overdue:
            messages.error(request, _('Batas waktu pembayaran sudah lewat.'))
            return redirect('rental:detail_booking', code=booking.code)

        form = PaymentProofForm(request.POST, request.FILES)
        if form.is_valid():
            booking.payment_method = form.cleaned_data['payment_method']
            booking.payment_proof = form.cleaned_data['payment_proof']
            booking.save(update_fields=['payment_method', 'payment_proof', 'updated_at'])
            grant_private_media_access(request, booking.payment_proof.name)
            log_event(
                'PROOF_UPLOADED', request=request, target=booking.code,
                metadata={'channel': 'rental',
                          'method': booking.payment_method})
            messages.success(
                request,
                _('Bukti pembayaran terkirim. Tim kami verifikasi maksimal 15 menit.'))
        else:
            for errs in form.errors.values():
                for err in errs:
                    messages.error(request, err)
        return redirect('rental:detail_booking', code=booking.code)
