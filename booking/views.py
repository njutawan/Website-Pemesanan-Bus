"""View alur pemesanan tiket bus:
cari jadwal → pilih kursi → isi data → booking dibuat → upload bukti bayar.
"""
from datetime import date as date_cls

from django.conf import settings

from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.generic import FormView, TemplateView, View

from booking.forms import PassengerForm, SearchForm
from booking.models import (
    Booking, BookingSeat, Route, Schedule,
    available_seat_count, expire_stale_bookings, taken_seat_ids,
)
from core.forms import PaymentProofForm


class SearchView(View):
    """Halaman /bus/ — form pencarian + daftar hasil jadwal."""
    template_name = 'booking/search.html'

    def get(self, request):
        expire_stale_bookings()
        form = SearchForm(request.GET or None)
        schedules = []
        searched = False
        search_date = None
        passengers = 1
        if request.GET and form.is_valid():
            searched = True
            search_date = form.cleaned_data['date']
            passengers = form.cleaned_data['passengers']
            for s in (
                Schedule.objects
                .select_related('route__origin', 'route__destination', 'bus')
                .filter(
                    route__origin=form.cleaned_data['origin'],
                    route__destination=form.cleaned_data['destination'],
                    is_active=True,
                )
                .order_by('departure_time')
            ):
                s.available = available_seat_count(s, search_date)
                s.enough = s.available >= passengers
                schedules.append(s)
        return render(request, self.template_name, {
            'form': form,
            'schedules': schedules,
            'searched': searched,
            'search_date': search_date,
            'passengers': passengers,
        })


class SeatSelectionView(TemplateView):
    """Langkah 2: denah kursi interaktif untuk jadwal+tanggal terpilih."""
    template_name = 'booking/seats.html'

    def get(self, request, schedule_id):
        expire_stale_bookings()
        schedule = get_object_or_404(
            Schedule.objects.select_related('bus', 'route'), pk=schedule_id, is_active=True)

        try:
            travel_date = date_cls.fromisoformat(request.GET.get('date') or '')
        except ValueError:
            messages.error(request, _('Tanggal perjalanan tidak valid.'))
            return redirect('booking:search')
        if travel_date < timezone.localdate():
            messages.error(request, _('Tanggal perjalanan tidak boleh di masa lalu.'))
            return redirect('booking:search')

        try:
            passengers = min(max(int(request.GET.get('passengers', 1)), 1), 6)
        except ValueError:
            passengers = 1

        taken = taken_seat_ids(schedule, travel_date)
        seats = schedule.bus.seats.all()
        for seat in seats:
            seat.is_taken = seat.id in taken

        return render(request, self.template_name, {
            'schedule': schedule,
            'travel_date': travel_date,
            'passengers': passengers,
            'seats': seats,
            'taken_count': len(taken),
            'step': 2,
        })


class CreateBookingView(View):
    """Langkah 3: tampilkan form data pemesan (GET) lalu buat booking (POST)."""
    template_name = 'booking/passenger.html'

    def _resolve(self, request, schedule_id):
        """Validasi jadwal+tanggal+kursi dari GET maupun POST."""
        schedule = get_object_or_404(
            Schedule.objects.select_related('bus', 'route'), pk=schedule_id, is_active=True)
        raw_date = request.GET.get('date') or request.POST.get('date') or ''
        try:
            travel_date = date_cls.fromisoformat(raw_date)
        except ValueError:
            raise ValidationError(_('Tanggal perjalanan tidak valid.'))
        if travel_date < timezone.localdate():
            raise ValidationError(_('Tanggal perjalanan tidak boleh di masa lalu.'))

        raw_seats = request.GET.get('seats') or request.POST.get('seats') or ''
        labels = [s.strip().upper() for s in raw_seats.split(',') if s.strip()]
        if not labels or len(labels) > 6:
            raise ValidationError(_('Pilih minimal 1 kursi (maksimal 6).'))
        seat_objs = list(schedule.bus.seats.filter(label__in=labels))
        if len(seat_objs) != len(labels):
            raise ValidationError(_('Ada kursi yang tidak ditemukan pada bus ini.'))
        return schedule, travel_date, seat_objs

    def get(self, request, schedule_id):
        try:
            schedule, travel_date, seat_objs = self._resolve(request, schedule_id)
        except ValidationError as e:
            messages.error(request, ''.join(e.messages))
            return redirect('booking:search')

        taken = taken_seat_ids(schedule, travel_date)
        if any(s.id in taken for s in seat_objs):
            messages.error(
                request,
                _('Maaf, beberapa kursi yang Anda pilih baru saja diambil. Silakan pilih ulang.'))
            return redirect('booking:seats', schedule_id)

        form = PassengerForm()
        return self._render(request, schedule, travel_date, seat_objs, form)

    def post(self, request, schedule_id):
        try:
            schedule, travel_date, seat_objs = self._resolve(request, schedule_id)
        except ValidationError as e:
            messages.error(request, ''.join(e.messages))
            return redirect('booking:search')

        form = PassengerForm(request.POST)
        if not form.is_valid():
            return self._render(request, schedule, travel_date, seat_objs, form, status=400)

        # Kunci baris jadwal & periksa ulang ketersediaan secara atomik (anti tabrakan)
        with transaction.atomic():
            locked = Schedule.objects.select_for_update().get(pk=schedule.pk)
            taken = taken_seat_ids(locked, travel_date)
            if any(s.id in taken for s in seat_objs):
                form.add_error(
                    None,
                    _('Maaf, beberapa kursi baru saja diambil orang lain. Silakan pilih ulang.'))
                return self._render(
                    request, locked, travel_date, seat_objs, form, status=409)

            booking = Booking.objects.create(
                schedule=locked,
                travel_date=travel_date,
                contact_name=form.cleaned_data['contact_name'],
                contact_phone=form.cleaned_data['contact_phone'],
                contact_email=form.cleaned_data['contact_email'],
                seats_qty=len(seat_objs),
                total_price=locked.price * len(seat_objs),
            )
            BookingSeat.objects.bulk_create(
                [BookingSeat(booking=booking, seat=s) for s in seat_objs])

        messages.success(
            request, _('Booking berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.'))
        return redirect('booking:detail', code=booking.code)

    def _render(self, request, schedule, travel_date, seats, form, status=200):
        return render(request, self.template_name, {
            'schedule': schedule,
            'travel_date': travel_date,
            'seats': seats,
            'total': schedule.price * len(seats),
            'form': form,
            'seats_csv': ','.join(s.label for s in seats),
            'step': 3,
        }, status=status)


@method_decorator(never_cache, name='dispatch')
class BookingDetailView(TemplateView):
    """Langkah 4: detail booking + instruksi pembayaran + upload bukti + e-tiket."""
    template_name = 'booking/detail.html'

    def get(self, request, code):
        expire_stale_bookings()
        booking = get_object_or_404(
            Booking.objects.select_related(
                'schedule__bus', 'schedule__route__origin',
                'schedule__route__destination'),
            code__iexact=code)
        return render(request, self.template_name, {
            'booking': booking,
            'seats': [i.seat for i in booking.seat_items.select_related('seat')],
            'proof_form': PaymentProofForm(initial={'payment_method': 'bca'}),
            'is_new': request.GET.get('baru') == '1',
            'step': 4,
        })


class UploadProofView(View):
    """Pelanggan mengirim bukti transfer/QRIS → admin memverifikasi di panel admin."""

    def post(self, request, code):
        booking = get_object_or_404(Booking, code__iexact=code)
        if booking.status != Booking.Status.PENDING:
            messages.error(request, _('Booking ini sudah tidak bisa menerima unggahan bukti.'))
            return redirect('booking:detail', code=booking.code)
        if booking.is_payment_overdue:
            messages.error(request, _('Batas waktu pembayaran sudah lewat.'))
            return redirect('booking:detail', code=booking.code)

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
        return redirect('booking:detail', code=booking.code)


class CheckBookingView(FormView):
    """Cek status booking lewat kode (dipakai dari navbar/footer)."""
    template_name = 'booking/check.html'

    def get(self, request):
        return render(request, self.template_name, {'code': request.GET.get('kode', '')})

    def post(self, request):
        code = (request.POST.get('code') or '').strip()
        if code and Booking.objects.filter(code__iexact=code).exists():
            return redirect('booking:detail', code=code)
        return render(request, self.template_name,
                      {'code': code, 'not_found': bool(code)}, status=404 if code else 200)


class RouteDetailView(TemplateView):
    """Halaman SEO per rute: /bus/rute/jember-surabaya/ — daftar jadwal + harga."""
    template_name = 'booking/route_detail.html'

    def get(self, request, slug):
        route = get_object_or_404(
            Route.objects.select_related('origin', 'destination'), slug=slug)
        # Daftar jadwal jarang berubah — cache per rute (queryset -> list).
        schedules = cache.get_or_set(
            f'route:{slug}:schedules',
            lambda: list(
                Schedule.objects.filter(route=route, is_active=True)
                .select_related('bus')
                .order_by('departure_time')
            ),
            getattr(settings, 'CACHE_TTL_DEFAULT', 600) // 2,
        )
        return render(request, self.template_name, {
            'route': route,
            'schedules': schedules,
            'today': timezone.localdate(),
        })
