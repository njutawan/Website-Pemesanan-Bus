"""Test integrasi QRIS Pakasir: klien, pembuatan link, webhook, settlement.

Semua panggilan jaringan di-mock — test suite tidak boleh menghubungi
internet dan tidak boleh membutuhkan kredensial nyata.
"""
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from booking.models import Booking, Bus, City, Route, Schedule
from core import payment_service
from core.checks import production_security
from core.models import AuditLog, PaymentTransaction
from core.pakasir import (
    PakasirClient, PakasirError, _clean_error_text, is_enabled,
    webhook_secret_matches,
)
from rental.models import RentalBooking, Vehicle

SECRET = 'test-webhook-secret-0123456789'
API_KEY = 'test-api-key-0123456789abcdef'
PAKASIR_SETTINGS = dict(
    PAYMENT_GATEWAY_PROVIDER='pakasir',
    PAKASIR_SLUG='nusantara-demo',
    PAKASIR_API_KEY=API_KEY,
    PAKASIR_WEBHOOK_SECRET=SECRET,
    PAKASIR_SANDBOX=False,
    PAKASIR_MIN_AMOUNT=500,
    PAKASIR_MAX_AMOUNT=50_000_000,
    RATELIMIT_ENABLED=False,
)
PAYMENT_URL = 'https://app.pakasir.com/pay-v2/txn-abc123'


def _make_bus_booking(price=50000):
    suffix = str(abs(hash((timezone.now().isoformat(), price))) % 1_000_000)
    a = City.objects.create(name=f'Kota A{suffix}', slug=f'kota-a-{suffix}',
                            province='Jatim')
    b = City.objects.create(name=f'Kota B{suffix}', slug=f'kota-b-{suffix}',
                            province='Jatim')
    route = Route.objects.create(origin=a, destination=b, distance_km=100,
                                 duration_minutes=120)
    bus = Bus.objects.create(code=f'U{suffix}', name='Bus Uji',
                             plate_number=f'N {suffix} XX', bus_class='EKONOMI',
                             rows=2)
    schedule = Schedule.objects.create(route=route, bus=bus,
                                       departure_time='08:00',
                                       arrival_time='10:00', price=price)
    return Booking.objects.create(
        schedule=schedule,
        travel_date=timezone.localdate() + timedelta(days=1),
        contact_name='Budi Uji', contact_phone='081234567890',
        seats_qty=1, total_price=price,
    )


def _make_rental_booking(price=600000):
    suffix = str(abs(hash((timezone.now().isoformat(), price))) % 1_000_000)
    vehicle = Vehicle.objects.create(
        name=f'Mobil {suffix}', category='MPV', year=2023,
        transmission='MATIC', seats=7, price_per_day=price // 2)
    base = timezone.localdate() + timedelta(days=10)
    return RentalBooking.objects.create(
        vehicle=vehicle, pickup_date=base, return_date=base + timedelta(days=1),
        pickup_location='Jember', contact_name='Penyewa Uji',
        contact_phone='081234567891', days=2, total_price=price,
    )


class FakePakasir:
    """Pengganti PakasirClient yang mencatat panggilan."""

    create_calls = []
    status_calls = []
    create_error = None
    status_error = None
    create_result = None
    status_result = None

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def reset(cls):
        cls.create_calls = []
        cls.status_calls = []
        cls.create_error = None
        cls.status_error = None
        cls.create_result = None
        cls.status_result = None

    def create_payment(self, order_id, amount):
        type(self).create_calls.append((order_id, amount))
        if type(self).create_error:
            raise type(self).create_error
        return {
            'txn_id': 'txn-abc123',
            'order_id': order_id,
            'amount': amount,
            'payment_url': PAYMENT_URL,
            'is_sandbox': False,
            'expired_at': '',
            'fee': 0,
            'total_payment': amount,
        }

    def get_status(self, txn_id):
        type(self).status_calls.append(txn_id)
        if type(self).status_error:
            raise type(self).status_error
        if type(self).status_result:
            return dict(type(self).status_result)
        txn = PaymentTransaction.objects.filter(
            txn_id=txn_id).order_by('-id').first()
        return {
            'txn_id': txn.txn_id,
            'order_id': txn.order_id,
            'amount': int(txn.amount),
            'status': 'completed',
            'is_sandbox': False,
            'completed_at': timezone.now().isoformat(),
        }

    @staticmethod
    def hosted_url(payment_url, *, redirect_url=''):
        return PakasirClient.hosted_url(
            payment_url, redirect_url=redirect_url)


class PakasirBaseTest(TestCase):
    def setUp(self):
        cache.clear()
        FakePakasir.reset()
        self.settings_ctx = override_settings(**PAKASIR_SETTINGS)
        self.settings_ctx.enable()
        self.addCleanup(self.settings_ctx.disable)
        self.booking = _make_bus_booking()
        patcher = patch('core.payment_service.PakasirClient', FakePakasir)
        self.client_patch = patcher
        patcher.start()
        self.addCleanup(patcher.stop)

    def create_txn(self, booking=None, kind='bus'):
        booking = booking or self.booking
        return payment_service.start_payment(kind, booking.code)

    def webhook_payload(self, txn, **overrides):
        payload = {
            'txn_id': txn.txn_id,
            'order_id': txn.order_id,
            'amount': int(txn.amount),
            'is_sandbox': False,
            'status': 'completed',
            'completed_at': '2026-10-19T10:00:00+07:00',
        }
        payload.update(overrides)
        return payload

    def post_webhook(self, payload, secret=SECRET, **extra):
        return self.client.post(
            reverse('pakasir_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_SECRET=secret,
            **extra,
        )


class ClientUnitTest(TestCase):
    def test_clean_error_membuang_api_key(self):
        with override_settings(PAKASIR_API_KEY=API_KEY):
            text = _clean_error_text(
                f'HTTP 401 api_key={API_KEY} ditolak {API_KEY}')
        self.assertNotIn(API_KEY, text)
        self.assertIn('[REDACTED]', text)

    def test_order_id_dan_amount_divalidasi(self):
        client = PakasirClient(slug='demo', api_key=API_KEY)
        with self.assertRaises(PakasirError):
            client.create_payment('../evil', 10000)
        with self.assertRaises(PakasirError):
            client.create_payment('ORDER-1', 100)
        with self.assertRaises(PakasirError):
            client.create_payment('ORDER-1', 60_000_000)

    def test_link_bukan_host_resmi_ditolak(self):
        client = PakasirClient(slug='demo', api_key=API_KEY)
        with patch.object(client, '_request', return_value={
                'txn_id': 'txn-abc123',
                'payment_link': 'https://evil.example/pay-v2/x'}):
            with self.assertRaises(PakasirError):
                client.create_payment('ORDER-1', 10000)

    def test_api_key_di_header_bukan_url(self):
        captured = {}

        class FakeResponse:
            status = 200

            def read(self, size):
                return (b'{"txn_id":"txn-abc123","order_id":"ORDER-1",'
                        b'"amount":10000,"payment_link":'
                        b'"https://app.pakasir.com/pay-v2/txn-abc123"}')

        class FakeConnection:
            def __init__(self, host, timeout=None, context=None):
                captured['host'] = host
                captured['timeout'] = timeout

            def request(self, method, path, body=None, headers=None):
                captured.update(method=method, path=path, body=body,
                                headers=headers)

            def getresponse(self):
                return FakeResponse()

            def close(self):
                pass

        client = PakasirClient(slug='demo', api_key=API_KEY)
        with patch('core.pakasir.http.client.HTTPSConnection',
                   FakeConnection):
            client.create_payment('ORDER-1', 10000)
        self.assertEqual(captured['host'], 'app.pakasir.com')
        self.assertEqual(captured['headers']['X-Api-Key'], API_KEY)
        self.assertNotIn(API_KEY, captured['path'])
        self.assertIn('create-transaction/demo/ORDER-1', captured['path'])

    def test_error_http_tidak_membocorkan_key(self):
        class FakeResponse:
            status = 401

            def read(self, size):
                return ('{"message":"api_key=%s salah"}' % API_KEY).encode()

        class FakeConnection:
            def __init__(self, *args, **kwargs):
                pass

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                return FakeResponse()

            def close(self):
                pass

        client = PakasirClient(slug='demo', api_key=API_KEY)
        with patch('core.pakasir.http.client.HTTPSConnection',
                   FakeConnection):
            with self.assertRaises(PakasirError) as ctx:
                client.create_payment('ORDER-1', 10000)
        self.assertNotIn(API_KEY, str(ctx.exception))

    def test_sandbox_tanpa_flag_di_respons_tetap_valid(self):
        client = PakasirClient(slug='demo', api_key=API_KEY)
        with override_settings(PAKASIR_SANDBOX=True), \
                patch.object(client, '_request', return_value={
                    'txn_id': 'txn-abc123',
                    'payment_link': PAYMENT_URL}):
            result = client.create_payment('ORDER-1', 10000)
        self.assertTrue(result['is_sandbox'])

    def test_link_resmi_dapat_dipakai(self):
        client = PakasirClient(slug='demo', api_key=API_KEY)
        with patch.object(client, '_request', return_value={
                'txn_id': 'txn-abc123',
                'payment_link': PAYMENT_URL,
                'amount': 10000,
                'order_id': 'ORDER-1'}):
            result = client.create_payment('ORDER-1', 10000)
        self.assertEqual(result['txn_id'], 'txn-abc123')

    def test_status_tidak_dikenal_ditolak(self):
        client = PakasirClient(slug='demo', api_key=API_KEY)
        with patch.object(client, '_request', return_value={
                'txn_id': 'txn-abc123', 'order_id': 'ORDER-1',
                'amount': 10000, 'status': 'refunded'}):
            with self.assertRaises(PakasirError):
                client.get_status('txn-abc123')

    def test_hosted_url_menambahkan_qris_only(self):
        url = PakasirClient.hosted_url(
            PAYMENT_URL, redirect_url='https://example.com/bayar/')
        self.assertIn('qris_only=1', url)
        self.assertIn('redirect=', url)
        with self.assertRaises(PakasirError):
            PakasirClient.hosted_url('https://evil.example/pay-v2/x')

    def test_secret_dibandingkan_konstan(self):
        with override_settings(PAKASIR_WEBHOOK_SECRET=SECRET):
            self.assertTrue(webhook_secret_matches(SECRET))
            self.assertFalse(webhook_secret_matches(SECRET + 'x'))
            self.assertFalse(webhook_secret_matches(''))

    def test_enabled_butuh_semua_kredensial(self):
        with override_settings(**PAKASIR_SETTINGS):
            self.assertTrue(is_enabled())
        with override_settings(PAKASIR_API_KEY=''):
            self.assertFalse(is_enabled())
        with override_settings(PAKASIR_WEBHOOK_SECRET=''):
            self.assertFalse(is_enabled())


class PaymentCreationTest(PakasirBaseTest):
    def test_gateway_mati_tidak_bisa_dibuat(self):
        with override_settings(PAYMENT_GATEWAY_PROVIDER=''):
            response = self.client.post(reverse(
                'payment_create', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(PaymentTransaction.objects.count(), 0)

    def test_link_dibuat_dengan_nominal_server(self):
        response = self.client.post(reverse(
            'payment_create', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(PAYMENT_URL))
        self.assertIn('qris_only=1', response['Location'])
        txn = PaymentTransaction.objects.get()
        self.assertEqual(int(txn.amount), 50000)
        self.assertEqual(txn.status, PaymentTransaction.Status.PENDING)
        self.assertEqual(FakePakasir.create_calls[0][1], 50000)
        self.assertTrue(txn.order_id.startswith(self.booking.code))
        self.assertNotIn(API_KEY, response['Location'])

    def test_klik_ulang_memakai_transaksi_yang_sama(self):
        self.client.post(reverse('payment_create',
                                 args=['bus', self.booking.code]))
        self.client.post(reverse('payment_create',
                                 args=['bus', self.booking.code]))
        self.assertEqual(PaymentTransaction.objects.count(), 1)
        self.assertEqual(len(FakePakasir.create_calls), 1)

    def test_booking_overdue_ditolak(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            created_at=timezone.now() - timedelta(
                hours=5 + 24))
        response = self.client.post(reverse(
            'payment_create', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PaymentTransaction.objects.count(), 0)

    def test_gagal_api_dicatat_failed(self):
        FakePakasir.create_error = PakasirError('down', code='network')
        response = self.client.post(reverse(
            'payment_create', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 302)
        txn = PaymentTransaction.objects.get()
        self.assertEqual(txn.status, PaymentTransaction.Status.FAILED)

    def test_csrf_wajib_untuk_pembuatan_link(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse(
            'payment_create', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(PaymentTransaction.objects.count(), 0)

    def test_halaman_tidak_membocorkan_api_key(self):
        response = self.client.get(reverse(
            'booking:detail', kwargs={'code': self.booking.code}))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn(API_KEY, body)
        self.assertNotIn(SECRET, body)
        self.assertIn('QRIS Online', body)
        self.assertNotIn('qris-placeholder', body)

    def test_tanpa_gateway_qris_statis_tetap_tampil(self):
        with override_settings(PAYMENT_GATEWAY_PROVIDER=''):
            response = self.client.get(reverse(
                'booking:detail', kwargs={'code': self.booking.code}))
        self.assertContains(response, 'qris-placeholder.png')

    def test_rental_dapat_membuat_link(self):
        rental = _make_rental_booking(price=600000)
        response = self.client.post(reverse(
            'payment_create', args=['rental', rental.code]))
        self.assertEqual(response.status_code, 302)
        txn = PaymentTransaction.objects.get()
        self.assertEqual(txn.kind, PaymentTransaction.Kind.RENTAL)
        self.assertEqual(int(txn.amount), 600000)


class WebhookTest(PakasirBaseTest):
    def setUp(self):
        super().setUp()
        self.txn = self.create_txn()

    def test_get_ditolak(self):
        response = self.client.get(reverse('pakasir_webhook'))
        self.assertEqual(response.status_code, 405)

    def test_secret_salah_ditolak(self):
        response = self.post_webhook(
            self.webhook_payload(self.txn), secret='salah')
        self.assertEqual(response.status_code, 401)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertTrue(AuditLog.objects.filter(
            action='WEBHOOK_REJECTED').exists())

    def test_tanpa_secret_ditolak(self):
        response = self.client.post(
            reverse('pakasir_webhook'),
            data=json.dumps(self.webhook_payload(self.txn)),
            content_type='application/json')
        self.assertEqual(response.status_code, 401)

    def test_webhook_valid_konfirmasi_booking(self):
        response = self.post_webhook(self.webhook_payload(self.txn))
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.txn.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(self.booking.payment_method, 'pakasir_qris')
        self.assertIsNotNone(self.booking.paid_at)
        self.assertEqual(self.txn.status, PaymentTransaction.Status.COMPLETED)
        self.assertTrue(AuditLog.objects.filter(
            action='PAYMENT_RECEIVED', success=True).exists())
        # Status API WAJIB dipanggil (verifikasi ulang).
        self.assertEqual(FakePakasir.status_calls, [self.txn.txn_id])

    def test_webhook_duplikat_idempoten(self):
        self.post_webhook(self.webhook_payload(self.txn))
        self.booking.refresh_from_db()
        paid_at = self.booking.paid_at
        response = self.post_webhook(self.webhook_payload(self.txn))
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.paid_at, paid_at)
        self.assertEqual(PaymentTransaction.objects.count(), 1)

    def test_nominal_tidak_cocok_ditolak(self):
        response = self.post_webhook(
            self.webhook_payload(self.txn, amount=1000))
        self.assertEqual(response.status_code, 400)
        self.booking.refresh_from_db()
        self.txn.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertTrue(self.txn.needs_review)
        self.assertFalse(self.txn.txn_id == '')

    def test_order_tidak_dikenal_ditolak(self):
        payload = self.webhook_payload(self.txn, order_id='NT-TIDAKADA')
        response = self.post_webhook(payload)
        self.assertEqual(response.status_code, 404)

    def test_txn_id_tidak_cocok_ditolak(self):
        response = self.post_webhook(
            self.webhook_payload(self.txn, txn_id='txn-lain999'))
        self.assertEqual(response.status_code, 400)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_sandbox_ditolak_di_produksi(self):
        response = self.post_webhook(
            self.webhook_payload(self.txn, is_sandbox=True))
        self.assertEqual(response.status_code, 400)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_api_belum_lunas_tidak_konfirmasi(self):
        FakePakasir.status_result = {
            'txn_id': self.txn.txn_id,
            'order_id': self.txn.order_id,
            'amount': int(self.txn.amount),
            'status': 'pending',
            'is_sandbox': False,
        }
        response = self.post_webhook(self.webhook_payload(self.txn))
        self.assertEqual(response.status_code, 409)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_api_error_minta_retry(self):
        FakePakasir.status_error = PakasirError('timeout', code='network')
        response = self.post_webhook(self.webhook_payload(self.txn))
        self.assertEqual(response.status_code, 503)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_api_nominal_berbeda_tidak_konfirmasi(self):
        FakePakasir.status_result = {
            'txn_id': self.txn.txn_id,
            'order_id': self.txn.order_id,
            'amount': 12345,
            'status': 'completed',
            'is_sandbox': False,
        }
        response = self.post_webhook(self.webhook_payload(self.txn))
        self.assertEqual(response.status_code, 400)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_status_tidak_didukung_ditolak(self):
        response = self.post_webhook(
            self.webhook_payload(self.txn, status='pending'))
        self.assertEqual(response.status_code, 400)

    def test_is_sandbox_harus_boolean(self):
        response = self.post_webhook(
            self.webhook_payload(self.txn, is_sandbox='false'))
        self.assertEqual(response.status_code, 400)

    def test_json_rusak_ditolak(self):
        response = self.client.post(
            reverse('pakasir_webhook'), data='{bukan json',
            content_type='application/json', HTTP_X_SECRET=SECRET)
        self.assertEqual(response.status_code, 400)

    def test_content_type_form_tetap_diterima(self):
        # Contoh resmi Pakasir memakai `curl --data` (form-urlencoded).
        response = self.client.post(
            reverse('pakasir_webhook'),
            data=json.dumps(self.webhook_payload(self.txn)),
            content_type='application/x-www-form-urlencoded',
            HTTP_X_SECRET=SECRET)
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)

    def test_amount_string_numerik_diterima(self):
        response = self.post_webhook(
            self.webhook_payload(self.txn, amount='50000'))
        self.assertEqual(response.status_code, 200)

    def test_body_terlalu_besar_ditolak(self):
        payload = dict(self.webhook_payload(self.txn))
        payload['padding'] = 'x' * (17 * 1024)
        response = self.post_webhook(payload)
        self.assertEqual(response.status_code, 400)

    def test_webhook_tanpa_csrf_token_tetap_diterima(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse('pakasir_webhook'),
            data=json.dumps(self.webhook_payload(self.txn)),
            content_type='application/json', HTTP_X_SECRET=SECRET)
        self.assertEqual(response.status_code, 200)

    def test_pembayaran_setelah_booking_expired_perlu_tinjauan(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            status=Booking.Status.EXPIRED)
        response = self.post_webhook(self.webhook_payload(self.txn))
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.txn.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.EXPIRED)
        self.assertTrue(self.txn.needs_review)
        self.assertEqual(self.txn.status, PaymentTransaction.Status.COMPLETED)
        self.assertTrue(AuditLog.objects.filter(
            action='PAYMENT_UNMATCHED').exists())

    def test_pembayaran_melewati_batas_waktu_perlu_tinjauan(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            created_at=timezone.now() - timedelta(hours=5))
        response = self.post_webhook(self.webhook_payload(self.txn))
        self.assertEqual(response.status_code, 200)
        self.booking.refresh_from_db()
        self.txn.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)
        self.assertTrue(self.txn.needs_review)
        self.assertEqual(self.txn.status, PaymentTransaction.Status.COMPLETED)

    def test_webhook_mengonfirmasi_sewa(self):
        rental = _make_rental_booking(price=600000)
        txn = self.create_txn(rental, kind='rental')
        response = self.post_webhook(self.webhook_payload(txn))
        self.assertEqual(response.status_code, 200)
        rental.refresh_from_db()
        self.assertEqual(rental.status, RentalBooking.Status.CONFIRMED)


class StatusSyncTest(PakasirBaseTest):
    def setUp(self):
        super().setUp()
        self.txn = self.create_txn()

    def test_sync_completed_konfirmasi(self):
        response = self.client.post(reverse(
            'payment_status', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(FakePakasir.status_calls, [self.txn.txn_id])

    def test_sync_cooldown_empat_detik(self):
        self.client.post(reverse(
            'payment_status', args=['bus', self.booking.code]))
        FakePakasir.status_result = {
            'txn_id': self.txn.txn_id, 'order_id': self.txn.order_id,
            'amount': 50000, 'status': 'pending', 'is_sandbox': False}
        self.client.post(reverse(
            'payment_status', args=['bus', self.booking.code]))
        self.assertEqual(len(FakePakasir.status_calls), 1)

    def test_sync_pending_belum_konfirmasi(self):
        FakePakasir.status_result = {
            'txn_id': self.txn.txn_id, 'order_id': self.txn.order_id,
            'amount': 50000, 'status': 'pending', 'is_sandbox': False}
        self.client.post(reverse(
            'payment_status', args=['bus', self.booking.code]))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_sync_canceled_menandai_transaksi(self):
        FakePakasir.status_result = {
            'txn_id': self.txn.txn_id, 'order_id': self.txn.order_id,
            'amount': 50000, 'status': 'canceled', 'is_sandbox': False}
        self.client.post(reverse(
            'payment_status', args=['bus', self.booking.code]))
        self.txn.refresh_from_db()
        self.assertEqual(self.txn.status, PaymentTransaction.Status.CANCELED)

    def test_tanpa_transaksi_hanya_pesan(self):
        PaymentTransaction.objects.all().delete()
        response = self.client.post(reverse(
            'payment_status', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FakePakasir.status_calls, [])

    def test_status_api_error_tidak_crash(self):
        FakePakasir.status_error = PakasirError('down', code='network')
        response = self.client.post(reverse(
            'payment_status', args=['bus', self.booking.code]))
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)


class ConfigAndAuditTest(TestCase):
    def _ids(self, **overrides):
        values = dict(
            DEBUG=False, RUNNING_TESTS=False, SECRET_KEY='x' * 60,
            ALLOWED_HOSTS=['example.com'],
            CSRF_TRUSTED_ORIGINS=['https://example.com'],
            RATELIMIT_ENABLED=True, CSP_ENABLED=True,
            ADMIN_ALLOWED_IPS=['10.0.0.0/8'],
            SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=31536000,
            X_FRAME_OPTIONS='DENY', PAYMENT_GATEWAY_PROVIDER='pakasir',
            PAKASIR_SLUG='demo', PAKASIR_API_KEY=API_KEY,
            PAKASIR_WEBHOOK_SECRET=SECRET, PAKASIR_SANDBOX=False,
        )
        values.update(overrides)
        with override_settings(**values):
            return {issue.id for issue in production_security(None)}

    def test_kredensial_kurang_menghasilkan_error(self):
        ids = self._ids(PAKASIR_SLUG='', PAKASIR_API_KEY='',
                        PAKASIR_WEBHOOK_SECRET='')
        self.assertIn('core.E020', ids)

    def test_provider_tidak_dikenal_error(self):
        self.assertIn('core.E019',
                      self._ids(PAYMENT_GATEWAY_PROVIDER='midtrans'))

    def test_sandbox_di_produksi_warning(self):
        self.assertIn('core.W023', self._ids(PAKASIR_SANDBOX=True))

    def test_kredensial_tanpa_provider_warning(self):
        self.assertIn('core.W024', self._ids(PAYMENT_GATEWAY_PROVIDER=''))

    def test_security_audit_menandai_webhook_pass(self):
        from io import StringIO
        out = StringIO()
        with override_settings(**PAKASIR_SETTINGS):
            call_command('security_audit', '--no-fail', '--skip-checks',
                         stdout=out)
        text = out.getvalue()
        self.assertRegex(text, r'11\. PASS')
        self.assertRegex(text, r'12\. PASS')

    def test_security_audit_manual_tetap_na(self):
        from io import StringIO
        out = StringIO()
        with override_settings(PAYMENT_GATEWAY_PROVIDER=''):
            call_command('security_audit', '--no-fail', '--skip-checks',
                         stdout=out)
        text = out.getvalue()
        self.assertRegex(text, r'11\. N/A')
        self.assertRegex(text, r'12\. N/A')


class AdminReadOnlyTest(TestCase):
    def setUp(self):
        cache.clear()
        with override_settings(**PAKASIR_SETTINGS):
            booking = _make_bus_booking()
            with patch('core.payment_service.PakasirClient', FakePakasir):
                self.txn = payment_service.start_payment('bus', booking.code)

    def test_superuser_bisa_melihat(self):
        user = User.objects.create_superuser(
            'root', 'root@example.com', 'Passw0rd-Kuat-2026')
        self.client.force_login(user)
        response = self.client.get(
            '/admin/core/paymenttransaction/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.txn.order_id)

    def test_staf_biasa_ditolak(self):
        user = User.objects.create_user(
            'staf', 'staf@example.com', 'Passw0rd-Kuat-2026', is_staff=True)
        self.client.force_login(user)
        response = self.client.get('/admin/core/paymenttransaction/')
        self.assertEqual(response.status_code, 403)
