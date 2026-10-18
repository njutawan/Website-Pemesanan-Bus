"""Uji unit modul booking: kursi, kode booking, kedaluwarsa, filter."""
import re
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings
from django.utils import timezone

from booking.models import (
    Booking, BookingSeat, Bus, City, Route, Schedule,
    available_seat_count, expire_stale_bookings,
    taken_seat_counts, taken_seat_ids,
)
from booking.templatetags.booking_extras import dur, to_idr


class BaseModelTest(TestCase):
    def setUp(self):
        self.jember = City.objects.create(name='Jember', slug='jember', province='Jawa Timur')
        self.surabaya = City.objects.create(name='Surabaya', slug='surabaya', province='Jawa Timur')
        self.route = Route.objects.create(
            origin=self.jember, destination=self.surabaya,
            distance_km=190, duration_minutes=240)
        self.bus = Bus.objects.create(
            code='NT-TEST', name='Bus Uji', plate_number='N 9999 UA',
            bus_class='EKONOMI', rows=10)

    def test_bus_generate_seats(self):
        # EKONOMI = 4 kolom × 10 baris = 40 kursi berlabel
        self.assertEqual(self.bus.total_seats, 40)
        self.assertTrue(self.bus.seats.filter(label='1A').exists())
        self.assertTrue(self.bus.seats.filter(label='10D').exists())

    def test_route_slug_otomatis(self):
        self.assertEqual(self.route.slug, 'jember-surabaya')

    def test_schedule_durasi_lintas_hari(self):
        from datetime import time
        s = Schedule.objects.create(
            route=self.route, bus=self.bus,
            departure_time=time(22, 0), arrival_time=time(4, 0), price=100000)
        self.assertTrue(s.arrives_next_day)
        self.assertEqual(s.duration_minutes, 6 * 60)


class BookingTest(TestCase):
    def setUp(self):
        self.jember = City.objects.create(name='Jember', slug='jember', province='Jawa Timur')
        self.surabaya = City.objects.create(name='Surabaya', slug='surabaya', province='Jawa Timur')
        self.route = Route.objects.create(
            origin=self.jember, destination=self.surabaya,
            distance_km=190, duration_minutes=240)
        self.bus = Bus.objects.create(
            code='NT-T1', name='Bus Uji 2', plate_number='N 8888 UA',
            bus_class='EKONOMI', rows=10)
        self.schedule = Schedule.objects.create(
            route=self.route, bus=self.bus,
            departure_time='08:00', arrival_time='12:00', price=120000)

    def _booking(self, labels):
        booking = Booking.objects.create(
            schedule=self.schedule, travel_date=date.today(),
            contact_name='Uji', contact_phone='081234567890',
            seats_qty=len(labels), total_price=self.schedule.price * len(labels))
        seats = self.bus.seats.filter(label__in=labels)
        from booking.models import BookingSeat
        BookingSeat.objects.bulk_create(
            [BookingSeat(booking=booking, seat=s) for s in seats])
        return booking

    def test_kode_booking_format(self):
        b = self._booking(['1A'])
        self.assertRegex(b.code, r'^NT-[A-Z2-9]{8}$')

    def test_kursi_terkunci_status_aktif(self):
        b = self._booking(['1A', '1B'])
        taken = taken_seat_ids(self.schedule, date.today())
        self.assertEqual(len(taken), 2)

    def test_kursi_lepas_setelah_dibatalkan(self):
        b = self._booking(['2A'])
        b.status = Booking.Status.CANCELLED
        b.save()
        self.assertEqual(taken_seat_ids(self.schedule, date.today()), set())

    def test_kedaluwarsa_otomatis(self):
        b = self._booking(['3A'])
        Booking.objects.filter(pk=b.pk).update(
            created_at=timezone.now() - timedelta(hours=3))
        n = expire_stale_bookings()
        self.assertEqual(n, 1)
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.Status.EXPIRED)
        self.assertEqual(taken_seat_ids(self.schedule, date.today()), set())

    def test_bayar_konfirmasi(self):
        b = self._booking(['4A'])
        b.mark_confirmed()
        b.refresh_from_db()
        self.assertEqual(b.status, Booking.Status.CONFIRMED)
        self.assertIsNotNone(b.paid_at)


class BookingFlowTest(TestCase):
    """Regresi alur langkah 2 → 3 (denah kursi → data pemesan)."""

    def setUp(self):
        self.jember = City.objects.create(name='Jember', slug='jember', province='Jawa Timur')
        self.surabaya = City.objects.create(name='Surabaya', slug='surabaya', province='Jawa Timur')
        self.route = Route.objects.create(
            origin=self.jember, destination=self.surabaya,
            distance_km=190, duration_minutes=240)
        self.bus = Bus.objects.create(
            code='NT-TFLOW', name='Bus Uji Alur', plate_number='N 7777 UA',
            bus_class='EKONOMI', rows=10)
        self.schedule = Schedule.objects.create(
            route=self.route, bus=self.bus,
            departure_time='08:00', arrival_time='12:00', price=120000)
        self.travel_date = timezone.localdate() + timedelta(days=7)

    def _booking(self, labels):
        booking = Booking.objects.create(
            schedule=self.schedule, travel_date=self.travel_date,
            contact_name='Uji', contact_phone='081234567890',
            seats_qty=len(labels), total_price=self.schedule.price * len(labels))
        seats = self.bus.seats.filter(label__in=labels)
        BookingSeat.objects.bulk_create(
            [BookingSeat(booking=booking, seat=s) for s in seats])
        return booking

    def test_form_kursi_pakai_get_ke_langkah_3_tanpa_error(self):
        # Bug 1: form POST hanya membawa date+seats → PassengerForm kosong
        # tervalidasi → langkah 3 langsung 400 dengan error "wajib diisi".
        date_str = self.travel_date.isoformat()
        r = self.client.get(
            f'/bus/kursi/{self.schedule.id}/?date={date_str}&passengers=2')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        m = re.search(r'<form[^>]*id="seatForm"[^>]*>', html)
        self.assertIsNotNone(m)
        self.assertIn('method="get"', m.group(0).lower())

        # Kirim seperti browser (GET date+seats) → form pemesan kosong, 200.
        r = self.client.get(
            f'/bus/pesan/{self.schedule.id}/?date={date_str}&seats=1A,1B')
        self.assertEqual(r.status_code, 200)
        form = r.context['form']
        self.assertFalse(form.is_bound)
        self.assertEqual(form.errors, {})

    def test_redirect_kursi_terisi_meneruskan_tanggal_dan_penumpang(self):
        # Bug 2: redirect tanpa query string → SeatSelectionView gagal
        # mem-parsing tanggal kosong → user terlempar ke pencarian.
        self._booking(['1A'])
        date_str = self.travel_date.isoformat()
        r = self.client.get(
            f'/bus/pesan/{self.schedule.id}/?date={date_str}&seats=1A,1B')
        self.assertEqual(r.status_code, 302)
        parsed = urlparse(r.url)
        self.assertEqual(parsed.path, f'/bus/kursi/{self.schedule.id}/')
        query = parse_qs(parsed.query)
        self.assertEqual(query.get('date'), [date_str])
        self.assertEqual(query.get('passengers'), ['2'])

        # Tujuan redirect harus benar-benar merender denah kursi (200),
        # bukan berantai redirect ke halaman pencarian.
        r2 = self.client.get(r.url)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.context['travel_date'], self.travel_date)
        self.assertEqual(r2.context['passengers'], 2)

    def test_booking_baru_redirect_baru_1_dan_banner_tampil(self):
        # Regresi: banner sukses di detail mensyaratkan ?baru=1, tetapi
        # redirect setelah POST dulu tidak pernah menyertakannya.
        r = self.client.post(f'/bus/pesan/{self.schedule.id}/', {
            'date': self.travel_date.isoformat(),
            'seats': '1A',
            'contact_name': 'Uji',
            'contact_phone': '081234567890',
            'contact_email': '',
            'agree': 'on',
        })
        self.assertEqual(r.status_code, 302)
        booking = Booking.objects.get()
        parsed = urlparse(r.url)
        self.assertEqual(parsed.path, f'/bus/booking/{booking.code}/')
        self.assertEqual(parse_qs(parsed.query).get('baru'), ['1'])

        detail = self.client.get(r.url)
        self.assertTrue(detail.context['is_new'])
        self.assertContains(detail, 'Booking Berhasil Dibuat!')
        # Tanpa parameter (mis. dari Cek Booking) banner tidak tampil.
        detail_tanpa_baru = self.client.get(parsed.path)
        self.assertFalse(detail_tanpa_baru.context['is_new'])

    def test_batas_kursi_mengikuti_max_seats_settings(self):
        with override_settings(MAX_SEATS_PER_BOOKING=2):
            r = self.client.get(
                f'/bus/kursi/{self.schedule.id}/'
                f'?date={self.travel_date.isoformat()}&passengers=99')
            self.assertEqual(r.context['passengers'], 2)

            r = self.client.get(
                f'/bus/pesan/{self.schedule.id}/'
                f'?date={self.travel_date.isoformat()}&seats=1A,1B,1C',
                follow=True)
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, 'maksimal 2')

    def test_countdown_deadline_dirender_dengan_offset_zona(self):
        booking = self._booking(['1A'])
        r = self.client.get(f'/bus/booking/{booking.code}/')
        m = re.search(rb'data-deadline="([^"]+)"', r.content)
        self.assertIsNotNone(m)
        deadline = datetime.fromisoformat(m.group(1).decode())
        self.assertIsNotNone(deadline.tzinfo)
        self.assertEqual(deadline.utcoffset(), timedelta(hours=7))

    def test_kelas_shake_seat_map_memiliki_css(self):
        from django.conf import settings
        css = (settings.BASE_DIR / 'static' / 'css' / 'style.css').read_text()
        self.assertIn('.needs-shake', css)
        self.assertIn('@keyframes nt-shake', css)


class SearchAvailabilityPerformanceTest(TestCase):
    """Ketersediaan hasil pencarian tanpa N+1 & tanpa UPDATE per request."""

    def setUp(self):
        from datetime import time as dtime
        self.jember = City.objects.create(name='Jember', slug='jember', province='Jawa Timur')
        self.surabaya = City.objects.create(name='Surabaya', slug='surabaya', province='Jawa Timur')
        self.route = Route.objects.create(
            origin=self.jember, destination=self.surabaya,
            distance_km=190, duration_minutes=240)
        self.travel_date = timezone.localdate() + timedelta(days=7)
        self.schedules = []
        for i in range(4):
            bus = Bus.objects.create(
                code=f'NT-P{i}', name=f'Bus Kinerja {i}',
                plate_number=f'N 900{i} UA', bus_class='EKONOMI', rows=10)
            self.schedules.append(Schedule.objects.create(
                route=self.route, bus=bus,
                departure_time=dtime(5 + i, 0), arrival_time=dtime(9 + i, 0),
                price=120000))
        self._booking(self.schedules[0], ['1A', '1B'])
        self._booking(self.schedules[0], ['1A'])  # kursi ganda: DISTINCT = tetap 2
        self._booking(self.schedules[1], ['1A'])
        self._booking(self.schedules[2], ['1A'], status=Booking.Status.CANCELLED)

    def _booking(self, schedule, labels, status=Booking.Status.PENDING):
        booking = Booking.objects.create(
            schedule=schedule, travel_date=self.travel_date,
            contact_name='Uji', contact_phone='081234567890',
            seats_qty=len(labels), total_price=schedule.price * len(labels),
            status=status)
        seats = schedule.bus.seats.filter(label__in=labels)
        BookingSeat.objects.bulk_create(
            [BookingSeat(booking=booking, seat=s) for s in seats])
        return booking

    def _annotated_schedules(self):
        from django.db.models import Count
        return list(
            Schedule.objects
            .select_related('route__origin', 'route__destination', 'bus')
            .annotate(bus_seat_count=Count('bus__seats'))
            .filter(route=self.route)
            .order_by('departure_time'))

    def test_available_seat_count_memakai_annotate_tanpa_count_tambahan(self):
        # Hanya query kursi terkunci; total kursi dari annotate, bukan
        # COUNT baru lewat schedule.bus.total_seats.
        annotated = self._annotated_schedules()[0]
        with self.assertNumQueries(1):
            self.assertEqual(
                available_seat_count(annotated, self.travel_date), 38)

    def test_taken_seat_counts_semua_jadwal_satu_query(self):
        schedules = self._annotated_schedules()
        with self.assertNumQueries(1):
            counts = taken_seat_counts(
                [s.id for s in schedules], self.travel_date)
            available = [
                s.bus_total_seats - counts.get(s.id, 0) for s in schedules]
        self.assertEqual(counts, {
            self.schedules[0].id: 2, self.schedules[1].id: 1})
        self.assertEqual(available, [38, 39, 40, 40])

    def test_pencarian_4_jadwal_maks_7_query_dan_tanpa_update(self):
        from django.core.cache import cache
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        stale = self._booking(self.schedules[3], ['3A'])
        Booking.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=3))
        cache.clear()
        url = (
            f'/bus/?origin={self.jember.pk}&destination={self.surabaya.pk}'
            f'&date={self.travel_date.isoformat()}&passengers=2')
        with CaptureQueriesContext(connection) as ctx:
            r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        # Sebelum optimasi: 15 query (UPDATE expire + COUNT & kursi
        # terkunci per jadwal + PageMeta). Sekarang 7 saat cache dingin.
        self.assertLessEqual(len(ctx.captured_queries), 7)
        sql = ' '.join(q['sql'] for q in ctx.captured_queries)
        self.assertNotIn('UPDATE "booking_booking"', sql)
        self.assertNotIn('SELECT COUNT(*) FROM "booking_seat"', sql)
        self.assertEqual(
            [s.available for s in r.context['schedules']], [38, 39, 40, 39])
        stale.refresh_from_db()
        self.assertEqual(stale.status, Booking.Status.PENDING)

    def test_get_publik_tidak_mengexpire_command_cron_yang_melakukannya(self):
        from io import StringIO
        from django.core.management import call_command
        stale = self._booking(self.schedules[3], ['3A'])
        Booking.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=3))

        self.assertEqual(self.client.get('/bus/').status_code, 200)
        self.assertEqual(self.client.get(
            f'/bus/kursi/{self.schedules[3].id}/'
            f'?date={self.travel_date.isoformat()}&passengers=1').status_code, 200)
        self.assertEqual(
            self.client.get(f'/bus/booking/{stale.code}/').status_code, 200)
        stale.refresh_from_db()
        self.assertEqual(stale.status, Booking.Status.PENDING)

        out = StringIO()
        call_command('expire_stale_bookings', stdout=out)
        stale.refresh_from_db()
        self.assertEqual(stale.status, Booking.Status.EXPIRED)
        self.assertIn('1 booking', out.getvalue())


class SeedDataWebPTest(TestCase):
    """Seed harus menghasilkan varian WebP yang dirujuk template."""

    def test_seed_menghasilkan_webp_termasuk_kendaraan_lama_berformat_jpg(self):
        import shutil
        import tempfile
        from io import StringIO
        from pathlib import Path

        from django.conf import settings
        from django.core.management import call_command

        from rental.models import Vehicle

        with tempfile.TemporaryDirectory() as tmp, \
                override_settings(MEDIA_ROOT=Path(tmp)):
            call_command('seed_data', stdout=StringIO())
            vehicles = list(Vehicle.objects.all())
            self.assertTrue(vehicles)
            for vehicle in vehicles:
                self.assertTrue(vehicle.image.name.endswith('.webp'))
                self.assertTrue((Path(tmp) / vehicle.image.name).exists())

            # Simulasi data lama: baris sudah ada menunjuk .jpg (update
            # queryset melewati hook konversi di Vehicle.save()).
            vehicle = vehicles[0]
            jpg_name = f"{vehicle.image.name.rsplit('.', 1)[0]}.jpg"
            jpg_path = Path(tmp) / jpg_name
            jpg_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(settings.BASE_DIR / 'static' / 'img' / jpg_name, jpg_path)
            Vehicle.objects.filter(pk=vehicle.pk).update(image=jpg_name)

            # Seed ulang: get_or_create tidak men-save baris lama, jadi
            # hanya convert_media_webp di akhir seed yang memperbaikinya.
            call_command('seed_data', stdout=StringIO())
            vehicle.refresh_from_db()
            self.assertTrue(vehicle.image.name.endswith('.webp'))
            self.assertTrue((Path(tmp) / vehicle.image.name).exists())


class TemplateTagTest(TestCase):
    def test_to_idr(self):
        self.assertEqual(to_idr(150000), 'Rp 150.000')
        self.assertEqual(to_idr(1234500), 'Rp 1.234.500')

    def test_dur(self):
        from django.utils import translation
        with translation.override('id'):
            self.assertEqual(dur(60), '1j')
            self.assertEqual(dur(150), '2j 30m')
            self.assertEqual(dur(1500), '1h 1j')
        with translation.override('en'):
            self.assertEqual(dur(150), '2h 30m')
