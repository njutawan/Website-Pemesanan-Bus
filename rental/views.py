"""View rental: katalog mobil, detail, form sewa, upload bukti bayar."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView, View

from core.forms import PaymentProofForm
from core.seo import HOME_CRUMB, breadcrumb_items, breadcrumb_schema
from rental.forms import RentalForm
from rental.models import RentalBooking, Vehicle


class VehicleListView(TemplateView):
    """Katalog mobil rental dengan filter kategori (?kategori=MPV)."""
    template_name = 'rental/index.html'

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
        booking = RentalBooking.objects.create(
            vehicle=vehicle,
            pickup_date=cleaned['pickup_date'],
            return_date=cleaned['return_date'],
            pickup_location=cleaned['pickup_location'],
            with_driver=cleaned['with_driver'],
            contact_name=cleaned['contact_name'],
            contact_phone=cleaned['contact_phone'],
            contact_email=cleaned['contact_email'],
            days=cleaned['days'],
            total_price=self.calc_total(vehicle, cleaned['days'], cleaned['with_driver']),
        )
        messages.success(
            request, _('Pesanan sewa berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.'))
        return redirect('rental:detail_booking', code=booking.code)


@method_decorator(never_cache, name='dispatch')
class RentalDetailView(TemplateView):
    """Detail pesanan sewa + instruksi pembayaran + upload bukti."""
    template_name = 'rental/detail_booking.html'

    def get(self, request, code):
        booking = get_object_or_404(
            RentalBooking.objects.select_related('vehicle'), code__iexact=code)
        return render(request, self.template_name, {
            'booking': booking,
            'proof_form': PaymentProofForm(initial={'payment_method': 'bca'}),
            'is_new': request.GET.get('baru') == '1',
        })


class UploadRentalProofView(View):
    """Upload bukti transfer/QRIS untuk sewa (diverifikasi admin)."""

    def post(self, request, code):
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
            messages.success(
                request,
                _('Bukti pembayaran terkirim. Tim kami verifikasi maksimal 15 menit.'))
        else:
            for errs in form.errors.values():
                for err in errs:
                    messages.error(request, err)
        return redirect('rental:detail_booking', code=booking.code)
