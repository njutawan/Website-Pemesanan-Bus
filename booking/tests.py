"""Uji unit modul booking: kursi, kode booking, kedaluwarsa, filter."""
from datetime import date, datetime, timedelta

from django.test import TestCase
from django.utils import timezone

from booking.models import (
    Booking, Bus, City, Route, Schedule, expire_stale_bookings, taken_seat_ids,
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
        self.assertRegex(b.code, r'^NT-[A-Z2-9]{6}$')

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
