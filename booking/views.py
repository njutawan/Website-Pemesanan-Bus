"""View alur pemesanan tiket bus:
cari jadwal → pilih kursi → isi data → booking dibuat → upload bukti bayar.
"""
from datetime import date as date_cls
from urllib.parse import urlencode

from django.conf import settings

from django.contrib import messages
from collections import Counter

from django.core.cache import cache
from django.db.models import Count, Min
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page, never_cache
from django.urls import reverse
from django.views.generic import FormView, RedirectView, TemplateView, View

from booking.forms import PassengerForm, SearchForm
from booking.templatetags.booking_extras import to_idr
from core.seo import HOME_CRUMB, breadcrumb_items, breadcrumb_schema, local_business_schema
from django.http import Http404

from booking.models import (
    Booking, BookingSeat, City, Route, Schedule,
    taken_seat_counts, taken_seat_ids,
)
from core.audit import log_event
from core.forms import PaymentProofForm
from core.private_media import grant_private_media_access
from core.validators import (
    clean_public_code, clean_seat_labels, validate_travel_date,
)


def cached_route_catalog():
    """Semua rute aktif + jumlah jadwal & harga termurah — satu sumber utk
    hub /bus/rute/, saran populer /bus/, dan link sibling antar rute.
    Dihitung 1x per TTL cache (0 query saat hangat)."""
    return cache.get_or_set(
        'hub:routes',
        lambda: list(
            Route.objects
            .annotate(n_schedules=Count('schedules', distinct=True),
                      min_price=Min('schedules__price'))
            .filter(n_schedules__gt=0)
            .select_related('origin', 'destination')
            .order_by('origin__name', 'destination__name')),
        getattr(settings, 'CACHE_TTL_DEFAULT', 600))


def cached_origin_cities():
    """Kategori (kota asal) utk grid homepage: city + jumlah rute aktif.
    0 query saat cache hangat; masukannya katalog rute yang sama."""
    return cache.get_or_set(
        'hub:origin_cities',
        lambda: [
            {'city': c, 'n': n}
            for c, n in Counter(r.origin for r in cached_route_catalog()).items()
        ],
        getattr(settings, 'CACHE_TTL_DEFAULT', 600))


class SearchView(View):
    """Halaman /bus/ — form pencarian + daftar hasil jadwal."""
    template_name = 'booking/search.html'

    def get(self, request):
        form = SearchForm(request.GET or None)
        schedules = []
        searched = False
        search_date = None
        passengers = 1
        if request.GET and form.is_valid():
            searched = True
            search_date = form.cleaned_data['date']
            passengers = form.cleaned_data['passengers']
            schedules = list(
                Schedule.objects
                .select_related('route__origin', 'route__destination', 'bus')
                .annotate(bus_seat_count=Count('bus__seats'))
                .filter(
                    route__origin=form.cleaned_data['origin'],
                    route__destination=form.cleaned_data['destination'],
                    is_active=True,
                )
                .order_by('departure_time')
            )
            # Ketersediaan semua jadwal dalam 1 query agregat + total kursi
            # dari annotate di atas (anti N+1: tanpa query per jadwal).
            taken_counts = taken_seat_counts(
                [s.id for s in schedules], search_date)
            for s in schedules:
                s.available = max(
                    s.bus_total_seats - taken_counts.get(s.id, 0), 0)
                s.enough = s.available >= passengers
        ctx = {
            'form': form,
            'schedules': schedules,
            'searched': searched,
            'search_date': search_date,
            'passengers': passengers,
            'schema_breadcrumbs': breadcrumb_schema(request, breadcrumb_items(
                HOME_CRUMB, (_('Tiket Bus'), None))),
        }
        if not searched:
            # Saran rute populer — dari katalog bersama (cache 10 menit).
            ctx['popular_routes'] = cached_route_catalog()[:6]
        return render(request, self.template_name, ctx)


class SeatSelectionView(TemplateView):
    """Langkah 2: denah kursi interaktif untuk jadwal+tanggal terpilih."""
    template_name = 'booking/seats.html'

    def get(self, request, schedule_id):
        schedule = get_object_or_404(
            Schedule.objects.select_related('bus', 'route'), pk=schedule_id, is_active=True)

        try:
            travel_date = date_cls.fromisoformat(request.GET.get('date') or '')
            validate_travel_date(travel_date)
        except (ValueError, TypeError):
            messages.error(request, _('Tanggal perjalanan tidak valid.'))
            return redirect('booking:search')
        except ValidationError as exc:
            messages.error(request, ''.join(exc.messages))
            return redirect('booking:search')

        try:
            passengers = min(
                max(int(request.GET.get('passengers', 1)), 1),
                settings.MAX_SEATS_PER_BOOKING)
        except (ValueError, TypeError):
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
        if len(str(raw_date)) > 20:
            raise ValidationError(_('Tanggal perjalanan tidak valid.'))
        try:
            travel_date = date_cls.fromisoformat(raw_date)
        except (ValueError, TypeError):
            raise ValidationError(_('Tanggal perjalanan tidak valid.'))
        validate_travel_date(travel_date)

        raw_seats = request.GET.get('seats') or request.POST.get('seats') or ''
        labels = clean_seat_labels(
            raw_seats, max_seats=settings.MAX_SEATS_PER_BOOKING)
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
            # Teruskan tanggal & jumlah penumpang — tanpa query string ini
            # SeatSelectionView gagal mem-parsing tanggal kosong dan
            # mengusir user kembali ke pencarian, kehilangan pilihannya.
            seats_url = reverse('booking:seats', args=[schedule_id])
            query = urlencode({
                'date': travel_date.isoformat(),
                'passengers': len(seat_objs),
            })
            return redirect(f'{seats_url}?{query}')

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

        log_event(
            'BOOKING_CREATED', request=request, target=booking.code,
            metadata={
                'schedule_id': locked.pk,
                'travel_date': travel_date.isoformat(),
                'seats': len(seat_objs),
            })
        messages.success(
            request, _('Booking berhasil dibuat! Selesaikan pembayaran sebelum batas waktu.'))
        detail_url = reverse('booking:detail', kwargs={'code': booking.code})
        return redirect(f'{detail_url}?{urlencode({"baru": 1})}')

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
        try:
            code = clean_public_code(code)
        except ValidationError:
            raise Http404('Booking tidak ditemukan.')
        booking = get_object_or_404(
            Booking.objects.select_related(
                'schedule__bus', 'schedule__route__origin',
                'schedule__route__destination'),
            code__iexact=code)
        # Kode booking adalah kredensial pemilik halaman ini: izinkan sesi
        # ini memuat thumbnail buktinya sendiri dari media privat.
        grant_private_media_access(
            request, booking.payment_proof.name if booking.payment_proof else None)
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
        try:
            code = clean_public_code(code)
        except ValidationError:
            raise Http404('Booking tidak ditemukan.')
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
            grant_private_media_access(request, booking.payment_proof.name)
            log_event(
                'PROOF_UPLOADED', request=request, target=booking.code,
                metadata={'channel': 'bus',
                          'method': booking.payment_method})
            messages.success(
                request,
                _('Bukti pembayaran terkirim. Tim kami verifikasi maksimal 15 menit.'))
        else:
            for errs in form.errors.values():
                for err in errs:
                    messages.error(request, err)
        return redirect('booking:detail', code=booking.code)


class RouteHubView(TemplateView):
    """Hub internal linking: indeks SEMUA rute, dikelompokkan per kota asal.

    Setiap halaman rute menerima link dari sini (kedalaman 2 klik dari
    beranda) — memastikan equity PageRank menyebar rata ke seluruh rute,
    bukan hanya yang kebetulan tampil di beranda/footer.
    """
    template_name = 'booking/route_hub.html'

    def get(self, request):
        return render(request, self.template_name, {
            'routes': cached_route_catalog(),
            'schema_breadcrumbs': breadcrumb_schema(request, breadcrumb_items(
                HOME_CRUMB, (_('Tiket Bus'), '/bus/'), (_('Semua Rute'), None))),
        })

class RouteDetailRedirectView(RedirectView):
    """URL rute lama (/bus/rute/jember-surabaya/) -> 301 permanen ke URL
    hierarkis baru (/bus/rute/dari/jember/surabaya/) — equity tidak hilang.
    """
    permanent = True

    def get_redirect_url(self, slug):
        route = get_object_or_404(
            Route.objects.select_related('origin', 'destination'), slug=slug)
        return route.get_absolute_url()


class CityRoutePillarView(TemplateView):
    """Pillar per silo: SEMUA rute dari satu kota asal (kategori).

    Simpul tengah piramida silo: menerima downward link dari hub global,
    menautkan turun ke seluruh rute kota ini, dan menyandingkan pillar
    kota lain (link antar-KATEGORI — bukan antar-artikel).
    """
    template_name = 'booking/city_routes.html'

    def get(self, request, city_slug):
        city = get_object_or_404(City, slug=city_slug)
        routes = [r for r in cached_route_catalog() if r.origin_id == city.pk]
        if not routes:
            # Kota tanpa rute aktif: jangan halaman kosong (soft-404 untuk bot)
            raise Http404('Kota ini belum memiliki rute aktif.')
        kota_lain, terlihat = [], {city.pk}
        for r in cached_route_catalog():
            o = r.origin
            if o.pk not in terlihat:
                terlihat.add(o.pk)
                kota_lain.append(o)
        return render(request, self.template_name, {
            'city': city,
            'routes': routes,
            'other_cities': kota_lain,
            'schema_breadcrumbs': breadcrumb_schema(request, breadcrumb_items(
                HOME_CRUMB, (_('Tiket Bus'), '/bus/'), (_('Semua Rute'), '/bus/rute/'),
                (_('Dari %(kota)s') % {'kota': city.name}, None))),
        })

class CheckBookingView(FormView):
    """Cek status booking lewat kode (dipakai dari navbar/footer)."""
    template_name = 'booking/check.html'

    def get(self, request):
        code = (request.GET.get('kode') or '').strip()[:20]
        return render(request, self.template_name, {
            'code': code,
            'schema_breadcrumbs': breadcrumb_schema(request, breadcrumb_items(
                HOME_CRUMB, (_('Cek Booking'), None))),
        })

    def post(self, request):
        raw_code = (request.POST.get('code') or '').strip()
        try:
            code = clean_public_code(raw_code)
        except ValidationError:
            return render(request, self.template_name,
                          {'code': raw_code[:20], 'not_found': True},
                          status=404 if raw_code else 200)
        if Booking.objects.filter(code__iexact=code).exists():
            return redirect('booking:detail', code=code)
        return render(request, self.template_name,
                      {'code': code, 'not_found': True}, status=404)


class RouteDetailView(TemplateView):
    """Halaman SEO per rute — URL hierarkis sesuai silo:
    /bus/rute/dari/jember/surabaya/ (kategori -> artikel).
    """
    template_name = 'booking/route_detail.html'

    @method_decorator(cache_page(60 * 15))
    def get(self, request, city_slug, dest_slug):
        route = get_object_or_404(
            Route.objects.select_related('origin', 'destination'),
            origin__slug=city_slug, destination__slug=dest_slug)
        # Daftar jadwal jarang berubah — cache per rute (queryset -> list).
        schedules = cache.get_or_set(
            f'route:{route.slug}:schedules',
            lambda: list(
                Schedule.objects.filter(route=route, is_active=True)
                .select_related('bus', 'route__origin', 'route__destination')
                .annotate(bus_seat_count=Count('bus__seats'))
                .order_by('departure_time')
            ),
            getattr(settings, 'CACHE_TTL_DEFAULT', 600) // 2,
        )
        # Internal linking: rute se-kota asal (sibling) — PageRank mengalir
        # antar halaman rute; maks 4 agar equity tidak terlalu terpecah.
        silo = [r for r in cached_route_catalog() if r.origin_id == route.origin_id]
        sibling_routes = [r for r in silo if r.pk != route.pk][:4]
        # Prev/next dalam silo (urut kota tujuan) — artikel lama tetap dirayap.
        _pos = next((i for i, r in enumerate(silo) if r.pk == route.pk), None)
        prev_route = silo[_pos - 1] if _pos is not None and _pos > 0 else None
        next_route = (silo[_pos + 1]
                      if _pos is not None and _pos + 1 < len(silo) else None)

        origin, dest = route.origin.name, route.destination.name
        crumb = breadcrumb_items(
            HOME_CRUMB, (_('Tiket Bus'), '/bus/'), (_('Semua Rute'), '/bus/rute/'),
            (_('Dari %(kota)s') % {'kota': origin},
             reverse('booking:city_routes', kwargs={'city_slug': route.origin.slug})),
            (f'{origin} → {dest}', None))

        # FAQ nyata (tampil di halaman + FAQPage JSON-LD) dari data rute.
        faq = [{'q': _('Berapa lama perjalanan bus dari %(origin)s ke %(destination)s?') % {
                    'origin': origin, 'destination': dest},
                'a': _('Perjalanan bus dari %(origin)s ke %(destination)s memakan waktu sekitar %(durasi)s, tergantung kondisi lalu lintas dan cuaca.') % {
                    'origin': origin, 'destination': dest,
                    'durasi': route.duration_display}}]
        prices = [s.price for s in schedules]
        if prices:
            faq.append({'q': _('Berapa harga tiket bus %(origin)s ke %(destination)s?') % {
                            'origin': origin, 'destination': dest},
                        'a': _('Harga tiket mulai dari %(harga)s per kursi, tergantung kelas bus dan fasilitasnya.') % {
                            'harga': to_idr(min(prices))}})
        if schedules:
            faq.append({'q': _('Kapan keberangkatan pertama dari %(origin)s?') % {
                            'origin': origin},
                        'a': _('Keberangkatan pertama dari %(origin)s pukul %(jam)s WIB. Tersedia %(jumlah)s jadwal setiap hari.') % {
                            'origin': origin,
                            'jam': schedules[0].departure_time.strftime('%H.%M'),
                            'jumlah': len(schedules)}})

        return render(request, self.template_name, {
            'route': route,
            'sibling_routes': sibling_routes,
            'prev_route': prev_route,
            'next_route': next_route,
            'schedules': schedules,
            'today': timezone.localdate(),
            'faq': faq,
            'schema_breadcrumbs': breadcrumb_schema(request, crumb),
            'schema_bustrip': {
                '@context': 'https://schema.org',
                '@type': 'BusTrip',
                'name': f'{origin} → {dest}',
                'provider': {
                    '@type': 'Organization',
                    'name': settings.SITE_NAME,
                    'url': request.build_absolute_uri('/'),
                },
                'departureBusStop': {'@type': 'BusStop', 'name': origin,
                                     'address': {'@type': 'PostalAddress',
                                                 'addressLocality': origin,
                                                 'addressCountry': 'ID'}},
                'arrivalBusStop': {'@type': 'BusStop', 'name': dest,
                                   'address': {'@type': 'PostalAddress',
                                               'addressLocality': dest,
                                               'addressCountry': 'ID'}},
            },
            'schema_faq': {
                '@context': 'https://schema.org',
                '@type': 'FAQPage',
                'mainEntity': [
                    {'@type': 'Question', 'name': f['q'],
                     'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}}
                    for f in faq],
            },
        })
