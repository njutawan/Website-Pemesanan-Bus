"""Uji unit modul rental."""
from datetime import date

from django.test import TestCase

from rental.models import RentalBooking, Vehicle


class VehicleTest(TestCase):
    def test_slug_otomatis(self):
        v = Vehicle.objects.create(
            name='Toyota Uji', category='MPV', year=2023, transmission='MATIC',
            seats=7, price_per_day=400000)
        self.assertEqual(v.slug, 'toyota-uji')

    def test_slug_unik_berurutan(self):
        Vehicle.objects.create(
            name='Daihatsu Uji', category='MPV', year=2022, transmission='MANUAL',
            seats=7, price_per_day=350000)
        v2 = Vehicle.objects.create(
            name='Daihatsu Uji', category='SUV', year=2023, transmission='MATIC',
            seats=7, price_per_day=500000)
        self.assertEqual(v2.slug, 'daihatsu-uji-2')


class RentalBookingTest(TestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            name='Toyota Kode', category='MPV', year=2023, transmission='MATIC',
            seats=7, price_per_day=400000, driver_fee_per_day=250000)

    def test_kode_sewa_format(self):
        b = RentalBooking.objects.create(
            vehicle=self.vehicle, pickup_date=date.today(),
            return_date=date.today(), pickup_location='Jember',
            contact_name='Uji', contact_phone='081234567890',
            days=1, total_price=400000)
        self.assertRegex(b.code, r'^SEWA-[A-Z2-9]{6}$')

    def test_batas_waktu_kedaluwarsa(self):
        from datetime import timedelta
        from django.utils import timezone
        b = RentalBooking.objects.create(
            vehicle=self.vehicle, pickup_date=date.today(),
            return_date=date.today(), pickup_location='Jember',
            contact_name='Uji', contact_phone='081234567890',
            days=1, total_price=400000)
        RentalBooking.objects.filter(pk=b.pk).update(
            created_at=timezone.now() - timedelta(hours=3))
        b.refresh_from_db()
        self.assertTrue(b.is_payment_overdue)
