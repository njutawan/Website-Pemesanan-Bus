"""Uji unit modul rental."""
from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from rental.models import (
    RentalBooking, Vehicle, expire_stale_rental_bookings, has_overlapping_rental,
)


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

    def _create_booking(self, status=RentalBooking.Status.PENDING, age_hours=0,
                        pickup=None):
        pickup = pickup or date.today()
        booking = RentalBooking.objects.create(
            vehicle=self.vehicle, pickup_date=pickup, return_date=pickup,
            pickup_location='Jember', contact_name='Uji',
            contact_phone='081234567890', days=1, total_price=400000,
            status=status)
        if age_hours:
            RentalBooking.objects.filter(pk=booking.pk).update(
                created_at=timezone.now() - timedelta(hours=age_hours))
            booking.refresh_from_db()
        return booking

    def test_kode_sewa_format(self):
        b = RentalBooking.objects.create(
            vehicle=self.vehicle, pickup_date=date.today(),
            return_date=date.today(), pickup_location='Jember',
            contact_name='Uji', contact_phone='081234567890',
            days=1, total_price=400000)
        self.assertRegex(b.code, r'^SEWA-[A-Z2-9]{6}$')

    def test_batas_waktu_kedaluwarsa(self):
        b = RentalBooking.objects.create(
            vehicle=self.vehicle, pickup_date=date.today(),
            return_date=date.today(), pickup_location='Jember',
            contact_name='Uji', contact_phone='081234567890',
            days=1, total_price=400000)
        RentalBooking.objects.filter(pk=b.pk).update(
            created_at=timezone.now() - timedelta(hours=3))
        b.refresh_from_db()
        self.assertTrue(b.is_payment_overdue)

    def test_payment_deadline_mengikuti_settings(self):
        # Regresi: deadline rental dulu hardcode 2 jam, mengabaikan
        # settings.PAYMENT_TIMEOUT_HOURS yang dipakai modul booking.
        b = RentalBooking.objects.create(
            vehicle=self.vehicle, pickup_date=date.today(),
            return_date=date.today(), pickup_location='Jember',
            contact_name='Uji', contact_phone='081234567890',
            days=1, total_price=400000)
        with override_settings(PAYMENT_TIMEOUT_HOURS=5):
            self.assertEqual(
                b.payment_deadline, b.created_at + timedelta(hours=5))

        RentalBooking.objects.filter(pk=b.pk).update(
            created_at=timezone.now() - timedelta(hours=3))
        b.refresh_from_db()
        with override_settings(PAYMENT_TIMEOUT_HOURS=5):
            self.assertFalse(b.is_payment_overdue)
        with override_settings(PAYMENT_TIMEOUT_HOURS=2):
            self.assertTrue(b.is_payment_overdue)


    def test_expire_stale_rental_hanya_pending_lewat_deadline(self):
        stale = self._create_booking(age_hours=3)
        fresh = self._create_booking()
        confirmed = self._create_booking(
            status=RentalBooking.Status.CONFIRMED, age_hours=3)

        self.assertEqual(expire_stale_rental_bookings(), 1)
        stale.refresh_from_db()
        fresh.refresh_from_db()
        confirmed.refresh_from_db()
        self.assertEqual(stale.status, RentalBooking.Status.EXPIRED)
        self.assertEqual(fresh.status, RentalBooking.Status.PENDING)
        self.assertEqual(confirmed.status, RentalBooking.Status.CONFIRMED)

    def test_command_expire_rental_melepas_unit_dan_get_detail_tidak_menulis(self):
        from io import StringIO
        from django.core.management import call_command
        pickup = date.today() + timedelta(days=7)
        stale = self._create_booking(age_hours=3, pickup=pickup)
        self.assertTrue(
            has_overlapping_rental(self.vehicle, pickup, pickup))

        # GET detail tidak boleh meng-expire (pola yang sama dengan bus:
        # kedaluwarsa adalah tugas cron, bukan request handler).
        self.assertEqual(
            self.client.get(f'/rental/sewa/{stale.code}/').status_code, 200)
        stale.refresh_from_db()
        self.assertEqual(stale.status, RentalBooking.Status.PENDING)

        out = StringIO()
        call_command('expire_stale_rental_bookings', stdout=out)
        stale.refresh_from_db()
        self.assertEqual(stale.status, RentalBooking.Status.EXPIRED)
        self.assertIn('1 pesanan sewa', out.getvalue())
        self.assertFalse(
            has_overlapping_rental(self.vehicle, pickup, pickup))
        # Status baru tampil semestinya di halaman detail.
        r = self.client.get(f'/rental/sewa/{stale.code}/')
        self.assertContains(r, 'Kedaluwarsa')

    def test_booking_rental_baru_redirect_baru_1_dan_banner_tampil(self):
        # Pola dead-code yang sama dengan booking bus juga diperbaiki.
        from urllib.parse import parse_qs, urlparse
        pickup = date.today() + timedelta(days=7)
        r = self.client.post(f'/rental/mobil/{self.vehicle.slug}/sewa/', {
            'pickup_date': pickup.isoformat(),
            'return_date': pickup.isoformat(),
            'pickup_location': 'Jember',
            'contact_name': 'Uji',
            'contact_phone': '081234567890',
            'contact_email': '',
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(parse_qs(urlparse(r.url).query).get('baru'), ['1'])
        detail = self.client.get(r.url)
        self.assertTrue(detail.context['is_new'])
        self.assertContains(detail, 'Pesanan Sewa Berhasil Dibuat!')


class RentalOverlapTest(TestCase):
    """Anti double-booking: satu unit tak boleh disewa pada tanggal yang
    tumpang tindih dengan sewa aktif (PENDING/CONFIRMED) lain."""

    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            name='Toyota Overlap', category='MPV', year=2023,
            transmission='MATIC', seats=7, price_per_day=400000)
        self.other_vehicle = Vehicle.objects.create(
            name='Daihatsu Overlap', category='MPV', year=2023,
            transmission='MATIC', seats=7, price_per_day=350000)
        self.base = timezone.localdate() + timedelta(days=10)
        self.existing = self._booking(
            self.vehicle, self.base, self.base + timedelta(days=2))

    def _booking(self, vehicle, pickup, ret, status=RentalBooking.Status.PENDING):
        return RentalBooking.objects.create(
            vehicle=vehicle, pickup_date=pickup, return_date=ret,
            pickup_location='Jember', contact_name='Uji',
            contact_phone='081234567890', days=(ret - pickup).days + 1,
            total_price=vehicle.price_per_day, status=status)

    def _post(self, pickup, ret, vehicle=None):
        vehicle = vehicle or self.vehicle
        return self.client.post(f'/rental/mobil/{vehicle.slug}/sewa/', {
            'pickup_date': pickup.isoformat(),
            'return_date': ret.isoformat(),
            'pickup_location': 'Jember',
            'contact_name': 'Penyewa Lain',
            'contact_phone': '081298765432',
            'contact_email': '',
        })

    def test_helper_overlap_inklusif_dan_exclude(self):
        base = self.base
        self.assertTrue(has_overlapping_rental(self.vehicle, base, base))
        # Rentang booking itu sendiri tak dihitung bila dikecualikan.
        self.assertFalse(has_overlapping_rental(
            self.vehicle, base, base + timedelta(days=2),
            exclude_pk=self.existing.pk))

    def test_post_overlap_ditolak_tanpa_booking_baru(self):
        base = self.base
        awal = RentalBooking.objects.count()
        # Tanggal inklusif: berbagi SATU hari saja (ujung rentang) sudah tabrakan.
        for pickup, ret in [
            (base - timedelta(days=2), base),                    # berakhir di hari ambil
            (base + timedelta(days=1), base + timedelta(days=1)),  # di tengah rentang
            (base + timedelta(days=2), base + timedelta(days=4)),  # mulai di hari kembali
        ]:
            with self.subTest(pickup=pickup, ret=ret):
                r = self._post(pickup, ret)
                self.assertEqual(r.status_code, 409)
                self.assertTrue(r.context['form'].non_field_errors())
        self.assertEqual(RentalBooking.objects.count(), awal)

    def test_post_tanpa_hari_yang_sama_diizinkan(self):
        base = self.base
        r = self._post(base - timedelta(days=3), base - timedelta(days=1))
        self.assertEqual(r.status_code, 302)
        r = self._post(base + timedelta(days=3), base + timedelta(days=4))
        self.assertEqual(r.status_code, 302)

    def test_confirmed_mengunci_cancelled_tidak(self):
        base = self.base
        rentang = (base, base + timedelta(days=2))
        self.existing.status = RentalBooking.Status.CONFIRMED
        self.existing.save(update_fields=['status'])
        self.assertEqual(self._post(*rentang).status_code, 409)

        self.existing.status = RentalBooking.Status.CANCELLED
        self.existing.save(update_fields=['status'])
        self.assertEqual(self._post(*rentang).status_code, 302)

    def test_completed_tidak_mengunci_dan_unit_lain_bebas(self):
        base = self.base
        rentang = (base, base + timedelta(days=2))
        # Unit lain pada tanggal yang sama tidak ikut terkunci.
        self.assertEqual(
            self._post(*rentang, vehicle=self.other_vehicle).status_code, 302)

        self.existing.status = RentalBooking.Status.COMPLETED
        self.existing.save(update_fields=['status'])
        self.assertEqual(self._post(*rentang).status_code, 302)
