"""Test keamanan 20 kontrol (lihat SECURITY.md / `manage.py security_audit`).

Test ini sengaja memakai `override_settings` untuk meniru produksi, dan
`Client(enforce_csrf_checks=True)` untuk memastikan proteksi CSRF benar-benar
bekerja — bukan hanya karena test client mematikan pemeriksaan.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import time
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from core.audit import log_event, mask_target
from core.checks import production_security
from core.logging import RedactSecretsFilter
from core.middleware import (
    SecurityHeadersMiddleware, TrustedProxyHeadersMiddleware,
)
from core.payments import (
    claim_webhook_event, parse_event, verify_webhook_signature,
)
from core.validators import clean_public_code, clean_seat_labels, csv_safe

User = get_user_model()


class BaseTestCase(TestCase):
    def setUp(self):
        cache.clear()


# =============================================================================
# 1. Rate limit
# =============================================================================
class RateLimitTest(BaseTestCase):
    RULES = {
        'global': {'limit': 100, 'window': 60},
        'lookup': {'limit': 2, 'window': 60},
    }

    @override_settings(RATELIMIT_ENABLED=True, RATELIMIT_RULES=RULES)
    def test_lookup_dibatasi_dan_mengirim_retry_after(self):
        for _ in range(2):
            self.assertEqual(self.client.get(
                '/bus/cek-booking/', REMOTE_ADDR='198.51.100.10').status_code, 200)
        r = self.client.get('/bus/cek-booking/', REMOTE_ADDR='198.51.100.10')
        self.assertEqual(r.status_code, 429)
        self.assertIn('Retry-After', r)
        self.assertGreater(int(r['Retry-After']), 0)
        self.assertEqual(r['Cache-Control'], 'no-store')

    @override_settings(RATELIMIT_ENABLED=True, RATELIMIT_RULES=RULES)
    def test_xff_diambil_dari_kanan_bukan_kiri(self):
        from core.middleware import get_client_ip
        req = RequestFactory().get(
            '/', HTTP_X_FORWARDED_FOR='1.2.3.4, 203.0.113.9',
            REMOTE_ADDR='127.0.0.1')
        self.assertEqual(get_client_ip(req), '203.0.113.9')

    def test_brute_force_kode_booking_dibatasi(self):
        with override_settings(
                RATELIMIT_ENABLED=True,
                RATELIMIT_RULES={'lookup': {'limit': 1, 'window': 60}}):
            cache.clear()
            self.client.get(
                '/bus/booking/NT-ZZZZ9999/', REMOTE_ADDR='198.51.100.21')
            r = self.client.get(
                '/bus/booking/NT-ZZZZ9999/', REMOTE_ADDR='198.51.100.21')
            self.assertEqual(r.status_code, 429)

    def test_form_sewa_rental_juga_dibatasi(self):
        with override_settings(
                RATELIMIT_ENABLED=True,
                RATELIMIT_RULES={'booking_create': {'limit': 1, 'window': 60}}):
            cache.clear()
            self.client.get('/rental/mobil/mobil-uji/sewa/', REMOTE_ADDR='198.51.100.20')
            r = self.client.get(
                '/rental/mobil/mobil-uji/sewa/', REMOTE_ADDR='198.51.100.20')
            self.assertEqual(r.status_code, 429)

    def test_ip_lain_tidak_terkena(self):
        for _ in range(3):
            self.client.get('/bus/cek-booking/', REMOTE_ADDR='198.51.100.11')
        self.assertEqual(self.client.get(
            '/bus/cek-booking/', REMOTE_ADDR='198.51.100.12').status_code, 200)

    @override_settings(RATELIMIT_ENABLED=False, RATELIMIT_RULES=RULES)
    def test_bisa_dinonaktifkan_untuk_maintenance(self):
        for _ in range(4):
            self.assertEqual(self.client.get(
                '/bus/cek-booking/', REMOTE_ADDR='198.51.100.13').status_code, 200)


# =============================================================================
# 2. CORS
# =============================================================================
class CorsTest(BaseTestCase):
    def test_default_tidak_ada_header_cors(self):
        r = self.client.get('/', HTTP_ORIGIN='https://evil.example')
        self.assertNotIn('Access-Control-Allow-Origin', r)

    @override_settings(CORS_ALLOWED_ORIGINS=['https://app.example'])
    def test_origin_eksplisit_di_echo_bukan_wildcard(self):
        r = self.client.get('/', HTTP_ORIGIN='https://app.example')
        self.assertEqual(r['Access-Control-Allow-Origin'], 'https://app.example')
        self.assertIn('Origin', r['Vary'])
        r2 = self.client.get('/', HTTP_ORIGIN='https://evil.example')
        self.assertNotIn('Access-Control-Allow-Origin', r2)

    @override_settings(CORS_ALLOWED_ORIGINS=['https://app.example'])
    def test_preflight_hanya_origin_diizinkan(self):
        ok = self.client.options(
            '/', HTTP_ORIGIN='https://app.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET')
        self.assertEqual(ok.status_code, 204)
        no = self.client.options(
            '/', HTTP_ORIGIN='https://evil.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET')
        self.assertEqual(no.status_code, 403)

    @override_settings(CORS_ALLOWED_ORIGINS=['*'])
    def test_wildcard_diabaikan(self):
        r = self.client.get('/', HTTP_ORIGIN='https://evil.example')
        self.assertNotIn('Access-Control-Allow-Origin', r)


# =============================================================================
# 3. CSRF
# =============================================================================
class CsrfTest(BaseTestCase):
    def test_post_tanpa_token_ditolak(self):
        client = Client(enforce_csrf_checks=True)
        r = client.post('/bus/cek-booking/', {'code': 'NT-AAAA1111'})
        self.assertEqual(r.status_code, 403)

    def test_post_dengan_token_lolos_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/bus/cek-booking/')
        token = client.cookies['csrftoken'].value
        r = client.post('/bus/cek-booking/',
                        {'code': 'NT-AAAA1111', 'csrfmiddlewaretoken': token})
        self.assertNotEqual(r.status_code, 403)  # 404 = kode tidak ada
        self.assertEqual(r.status_code, 404)

    def test_semua_form_post_memakai_csrf_token(self):
        templates = Path(settings.BASE_DIR) / 'templates'
        for path in templates.rglob('*.html'):
            text = path.read_text(errors='ignore')
            for match in re.finditer(
                    r'<form\b[^>]*method=["\']post["\'][^>]*>', text, re.I):
                block = text[match.start():match.start() + 1200]
                self.assertIn('csrf_token', block, msg=str(path))


# =============================================================================
# 4. SSRF & open redirect
# =============================================================================
class SsrfTest(BaseTestCase):
    def test_url_admin_seo_wajib_internal(self):
        from booking.models import City
        from core.models import PageMeta, SeoKeyword
        for url in ('https://evil.example/a', '//evil.example/a',
                    'javascript:alert(1)'):
            with self.subTest(url=url):
                with self.assertRaises(ValidationError):
                    SeoKeyword(phrase='x', url=url).full_clean()
        with self.assertRaises(ValidationError):
            PageMeta(path='https://evil.example/').full_clean()
        with self.assertRaises(ValidationError):
            PageMeta(path='//evil.example/').full_clean()
        City.objects.create(name='Kota X', slug='kota-x', province='Jatim')

    def test_redirect_admin_menolak_tujuan_luar(self):
        from django.contrib.redirects.models import Redirect
        from core.admin import SafeRedirectForm
        site = Site.objects.get_or_create(
            pk=1, defaults={'domain': 'testserver', 'name': 'test'})[0]
        form = SafeRedirectForm(data={
            'site': site.pk, 'old_path': '/lama/', 'new_path': 'https://evil.example/'})
        self.assertFalse(form.is_valid())
        form_ok = SafeRedirectForm(data={
            'site': site.pk, 'old_path': '/lama/', 'new_path': '/baru/'})
        self.assertTrue(form_ok.is_valid(), form_ok.errors)
        self.assertTrue(Redirect.objects.count() == 0)

    def test_tidak_ada_http_client_keluar_di_kode_app(self):
        # Satu-satunya HTTP client keluar yang diizinkan adalah klien Pakasir
        # (host tetap, header API key, tanpa redirect). File lain harus bersih
        # agar tidak ada jalur SSRF baru.
        needles = ('requests.', 'urlopen(', 'httpx.', 'aiohttp.',
                   'socket.socket(', 'http.client')
        allowed = Path(settings.BASE_DIR) / 'core' / 'pakasir.py'
        hits = []
        for path in Path(settings.BASE_DIR).rglob('*.py'):
            if any(part in {'.venv', 'venv', 'node_modules', '.git'}
                   for part in path.parts):
                continue
            if path.name.startswith('test') or path.name == 'security_audit.py':
                continue
            if path == allowed:
                continue
            text = path.read_text(errors='ignore')
            hits += [f'{path.name}:{n}' for n in needles if n in text]
        self.assertEqual(hits, [])

    def test_klien_pakasir_memakai_host_tetap(self):
        text = (Path(settings.BASE_DIR) / 'core' / 'pakasir.py').read_text()
        self.assertEqual(text.count('HTTPSConnection('), 1)
        self.assertIn("'app.pakasir.com'", text)
        self.assertNotIn('urlopen(', text)
        self.assertIn("'X-Api-Key'", text)


# =============================================================================
# 5. Path traversal & media
# =============================================================================
class MediaSecurityTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._ov = override_settings(MEDIA_ROOT=self._tmp.name)
        self._ov.enable()
        self.addCleanup(self._ov.disable)
        root = Path(self._tmp.name)
        files = {
            'vehicles/ok.jpg': b'ok',
            'vehicles/evil.html': b'<script>alert(1)</script>',
            'payment_proofs/2026/10/proof.jpg': b'rahasia',
        }
        for rel, data in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def test_ekstensi_berbahaya_tidak_disajikan(self):
        self.assertEqual(self.client.get('/media/vehicles/evil.html').status_code, 404)

    def test_traversal_encoded_ditolak(self):
        for path in (
            '/media/vehicles/../payment_proofs/2026/10/proof.jpg',
            '/media/vehicles/%2e%2e/payment_proofs/2026/10/proof.jpg',
            '/media/vehicles/%252e%252e/payment_proofs/2026/10/proof.jpg',
            '/media/vehicles/..%2fpayment_proofs/2026/10/proof.jpg',
            '/media/vehicles%00.jpg',
        ):
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 404)
                self.assertNotIn(b'rahasia', r.content)

    def test_media_publik_punya_nosniff_dan_csp_sandbox(self):
        r = self.client.get('/media/vehicles/ok.jpg')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertIn("sandbox", r['Content-Security-Policy'])
        self.assertIn('public', r['Cache-Control'])

    def test_bukti_privat_tetap_tertutup(self):
        url = '/media/payment_proofs/2026/10/proof.jpg'
        self.assertEqual(self.client.get(url).status_code, 404)
        staff = User.objects.create_user(
            'staf-media', password='StrongPass#2026', is_staff=True)
        self.client.force_login(staff)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Cache-Control'], 'private, no-store')
        self.assertIn('sandbox', r['Content-Security-Policy'])

    def test_source_map_selalu_404(self):
        for path in ('/static/js/main.js.map', '/media/x.map', '/foo.MAP'):
            self.assertEqual(self.client.get(path).status_code, 404)


# =============================================================================
# 6. Validasi input
# =============================================================================
class InputValidationTest(TestCase):
    def test_kode_publik(self):
        self.assertEqual(clean_public_code(' NT-ABCD1234 '), 'NT-ABCD1234')
        for bad in ('', 'x', 'A' * 21, 'NT-<script>', 'NT-AB CD'):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    clean_public_code(bad)

    def test_label_kursi(self):
        self.assertEqual(clean_seat_labels('1a, 2b', max_seats=3), ['1A', '2B'])
        for raw in ('1A,1A', '1A,2B,3C', '<script>', 'A' * 130):
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError):
                    clean_seat_labels(raw, max_seats=2)

    def test_nomor_telepon(self):
        from core.validators import clean_phone
        self.assertEqual(clean_phone('+62 812-3456-7890'), '+6281234567890')
        for bad in ('12345', 'abc123456789', '0' * 17, ''):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    clean_phone(bad)

    def test_tanggal_masa_lalu_dan_terlalu_jauh(self):
        from core.validators import validate_travel_date
        with self.assertRaises(ValidationError):
            validate_travel_date(timezone.localdate() - timedelta(days=1))
        with self.assertRaises(ValidationError):
            validate_travel_date(timezone.localdate() + timedelta(days=9999))


# =============================================================================
# 7. Output validation
# =============================================================================
class OutputValidationTest(BaseTestCase):
    def test_jsonld_tidak_bisa_keluar_script(self):
        from booking.templatetags.booking_extras import jsonld
        out = jsonld({'x': '</script><script>alert(1)</script>'})
        self.assertNotIn('</script>', out)
        self.assertIn('\\u003c', out)

    def test_csv_formula_injection_dinetralkan(self):
        for payload in ('=cmd|calc', '+SUM(A1)', '-1+2', '@import',
                        '  =cmd|calc', '\t=cmd|calc'):
            with self.subTest(payload=payload):
                self.assertTrue(csv_safe(payload).startswith("'"))

    def test_auto_internal_link_tidak_bisa_menyisipkan_atribut(self):
        from core.models import SeoKeyword
        from core.templatetags.seo_internal_links import auto_internal_link
        SeoKeyword.objects.create(
            phrase='klik', url='/tujuan/?a=" onmouseover="alert(1)')
        cache.delete('seo:db_keywords')
        out = auto_internal_link('klik di sini', None)
        self.assertNotIn('onmouseover="', out)
        self.assertIn('&quot;', out)
        self.assertIn('href="/tujuan/?a=&quot;', out)

    def test_nama_pemesan_di_escape_di_halaman_booking(self):
        booking = _make_booking(contact_name='<script>alert(1)</script>')
        r = self.client.get(f'/bus/booking/{booking.code}/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'<script>alert(1)</script>', r.content)
        self.assertIn(b'&lt;script&gt;alert(1)&lt;/script&gt;', r.content)


# =============================================================================
# 8. Admin
# =============================================================================
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AdminProtectionTest(BaseTestCase):
    def _staff(self, **kwargs):
        return User.objects.create_user(
            'staf-admin', password='StrongPass#2026', is_staff=True, **kwargs)

    def test_anonim_diarahkan_ke_login(self):
        r = self.client.get('/admin/')
        self.assertIn(r.status_code, (302, 403))
        self.assertEqual(r.status_code, 302)

    def test_non_staf_tidak_bisa_masuk(self):
        user = User.objects.create_user('biasa', password='StrongPass#2026')
        self.client.force_login(user)
        r = self.client.get('/admin/')
        self.assertIn(r.status_code, (302, 403))

    def test_staf_bisa_membuka_dasbor(self):
        self.client.force_login(self._staff())
        self.assertEqual(self.client.get('/admin/').status_code, 200)

    @override_settings(ADMIN_ALLOWED_IPS=['10.0.0.0/8'], RATELIMIT_ENABLED=False)
    def test_allowlist_ip_admin(self):
        self.assertEqual(self.client.get(
            '/admin/login/', REMOTE_ADDR='198.51.100.9').status_code, 404)
        self.assertEqual(self.client.get(
            '/admin/login/', REMOTE_ADDR='10.1.2.3').status_code, 200)

    @override_settings(
        RATELIMIT_ENABLED=True,
        RATELIMIT_RULES={
            'global': {'limit': 100, 'window': 60},
            'unsafe': {'limit': 100, 'window': 60},
            'admin_login': {'limit': 2, 'window': 60},
            'admin_login_user': {'limit': 100, 'window': 60},
        })
    def test_login_admin_dibatasi(self):
        for _ in range(2):
            self.assertEqual(self.client.post(
                '/admin/login/',
                {'username': 'admin', 'password': 'salah'}).status_code, 200)
        r = self.client.post('/admin/login/',
                             {'username': 'admin', 'password': 'salah'})
        self.assertEqual(r.status_code, 429)
        self.assertIn('Retry-After', r)


# =============================================================================
# 9-10. Password default & audit
# =============================================================================
class DefaultPasswordTest(BaseTestCase):
    def test_tidak_ada_admin123_di_dokumen_config(self):
        for name in ('.env.example', 'docker-compose.yml', 'README.md'):
            with self.subTest(name=name):
                text = (Path(settings.BASE_DIR) / name).read_text(errors='ignore')
                self.assertNotIn('admin123', text)

    def test_env_example_membatasi_admin_tanpa_wildcard(self):
        text = (Path(settings.BASE_DIR) / '.env.example').read_text()
        self.assertIn(
            'DJANGO_ADMIN_ALLOWED_IPS=127.0.0.1/32,::1/128,192.168.0.0/16', text)
        self.assertNotIn('DJANGO_ADMIN_ALLOWED_IPS=0.0.0.0/0', text)

    def test_seed_menolak_password_lemah_dan_mewajibkan_env_di_produksi(self):
        from booking.management.commands.seed_data import _resolve_admin_password
        with mock.patch.dict(os.environ, {'DJANGO_ADMIN_PASSWORD': 'admin123'}):
            with self.assertRaises(CommandError):
                _resolve_admin_password()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DJANGO_ADMIN_PASSWORD', None)
            with override_settings(DEBUG=False, RUNNING_TESTS=False):
                with self.assertRaises(CommandError):
                    _resolve_admin_password()
            with override_settings(DEBUG=True):
                password, generated = _resolve_admin_password()
                self.assertTrue(generated)
                self.assertGreaterEqual(len(password), 16)


class AuditTest(BaseTestCase):
    def test_audit_menyamarkan_pii_dan_secret(self):
        log_event('LOGIN_FAILED', target='budi@example.com',
                  metadata={'password': 'hunter2', 'email': 'a@b.com',
                            'phone': '081234567890', 'route': 'Jember-Surabaya'})
        from core.models import AuditLog
        row = AuditLog.objects.latest('created_at')
        self.assertNotIn('budi@example.com', row.target)
        self.assertEqual(row.metadata['password'], '[REDACTED]')
        self.assertNotIn('a@b.com', json.dumps(row.metadata))
        self.assertNotIn('081234567890', json.dumps(row.metadata))
        self.assertEqual(row.metadata['route'], 'Jember-Surabaya')

    def test_kode_booking_disamarkan(self):
        self.assertEqual(mask_target('NT-ABCD1234'), 'NT-AB****')
        self.assertNotEqual(mask_target('NT-ABCD1234'), 'NT-ABCD1234')

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
    def test_login_sukses_dan_gagal_tercatat(self):
        from core.models import AuditLog
        User.objects.create_user('audit-user', password='StrongPass#2026')
        self.assertTrue(self.client.login(username='audit-user',
                                          password='StrongPass#2026'))
        self.assertTrue(AuditLog.objects.filter(action='LOGIN_SUCCESS').exists())
        self.client.logout()
        self.assertFalse(self.client.login(username='audit-user',
                                           password='salah'))
        self.assertTrue(AuditLog.objects.filter(action='LOGIN_FAILED').exists())

    def test_purge_audit_menghormati_retensi(self):
        from datetime import timedelta
        from django.core.management import call_command
        from django.utils import timezone
        from core.models import AuditLog
        old = AuditLog.objects.create(
            action='OLD_EVENT', success=True, target='x')
        AuditLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=10))
        fresh = AuditLog.objects.create(
            action='FRESH_EVENT', success=True, target='y')
        call_command('purge_audit_logs', '--days', '5', stdout=StringIO())
        self.assertFalse(AuditLog.objects.filter(pk=old.pk).exists())
        self.assertTrue(AuditLog.objects.filter(pk=fresh.pk).exists())

    def test_audit_log_read_only_dan_hanya_superuser(self):
        from core.models import AuditLog
        from core.admin import AuditLogAdmin
        model_admin = AuditLogAdmin(AuditLog, None)
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))
        superuser = type('U', (), {'is_active': True, 'is_superuser': True})()
        staff = type('U', (), {'is_active': True, 'is_superuser': False})()
        self.assertTrue(model_admin.has_view_permission(
            type('R', (), {'user': superuser})()))
        self.assertFalse(model_admin.has_view_permission(
            type('R', (), {'user': staff})()))


# =============================================================================
# 11. Webhook
# =============================================================================
class WebhookTest(BaseTestCase):
    def _sign(self, payload, ts, secret='s3cret'):
        sig = hmac.new(secret.encode(), f'{ts}.'.encode() + payload,
                       hashlib.sha256).hexdigest()
        return f't={ts},v1={sig}'

    def test_hmac_valid_dan_replay_ditolak(self):
        payload = b'{"id":"evt_1","type":"payment.paid"}'
        ts = int(time.time())
        header = self._sign(payload, ts)
        self.assertTrue(verify_webhook_signature(
            payload, header, secret='s3cret', now=ts))
        self.assertFalse(verify_webhook_signature(
            payload, header, secret='salah', now=ts))
        self.assertFalse(verify_webhook_signature(
            payload, self._sign(payload, ts - 1000), secret='s3cret',
            now=ts, tolerance=300))
        self.assertFalse(verify_webhook_signature(
            payload, header, secret='', now=ts))

    def test_idempotensi_event(self):
        self.assertTrue(claim_webhook_event('evt_abc'))
        self.assertFalse(claim_webhook_event('evt_abc'))

    def test_payload_harus_json_objek(self):
        self.assertEqual(parse_event(b'{"id":"x"}'), {'id': 'x'})
        with self.assertRaises(Exception):
            parse_event(b'[1,2]')
        with self.assertRaises(Exception):
            parse_event(b'<xml/>')


# =============================================================================
# 12-14. Payment, harga, IDOR
# =============================================================================
class PaymentAndPriceTest(BaseTestCase):
    def test_metode_pembayaran_hanya_pilihan_server(self):
        from core.forms import PaymentProofForm
        form = PaymentProofForm(data={'payment_method': 'bitcoin'})
        self.assertFalse(form.is_valid())
        self.assertIn('payment_method', form.errors)

    def test_harga_booking_tidak_bisa_ditimpa_klien(self):
        schedule = _make_schedule(price=50000)
        data = _booking_post_data(schedule, seats='1A')
        data.update({'total_price': '1', 'price': '1', 'status': 'CONFIRMED'})
        r = self.client.post(f'/bus/pesan/{schedule.pk}/', data)
        self.assertEqual(r.status_code, 302)
        from booking.models import Booking
        booking = Booking.objects.latest('created_at')
        self.assertEqual(int(booking.total_price), 50000)
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_harga_rental_tidak_bisa_ditimpa_klien(self):
        from rental.models import RentalBooking, Vehicle
        vehicle = Vehicle.objects.create(
            name='Mobil Uji', slug='mobil-uji', category='MPV', year=2023,
            seats=7, price_per_day=400000, driver_fee_per_day=100000)
        data = {
            'pickup_date': (date.today() + timedelta(days=1)).isoformat(),
            'return_date': (date.today() + timedelta(days=2)).isoformat(),
            'pickup_location': 'Jember',
            'contact_name': 'Uji', 'contact_phone': '081234567890',
            'contact_email': 'uji@example.com',
            'total_price': '1', 'days': '99', 'price_per_day': '1',
        }
        r = self.client.post(f'/rental/mobil/{vehicle.slug}/sewa/', data)
        self.assertEqual(r.status_code, 302)
        booking = RentalBooking.objects.latest('created_at')
        self.assertEqual(booking.days, 2)
        self.assertEqual(int(booking.total_price), 800000)  # 2 hari x 400rb

    def test_idor_kode_tidak_valid_dan_upload_bukan_pending(self):
        booking = _make_booking()
        self.assertEqual(self.client.get(
            '/bus/booking/' + 'X' * 40 + '/').status_code, 404)
        booking.status = booking.Status.CONFIRMED
        booking.save(update_fields=['status'])
        r = self.client.post(
            f'/bus/booking/{booking.code}/upload/', {'payment_method': 'bca'})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('/upload/', r['Location'])
        booking.refresh_from_db()
        self.assertFalse(booking.payment_proof)

    def test_upload_ekstensi_berbahaya_ditolak(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        booking = _make_booking()
        upload = SimpleUploadedFile(
            'bukti.html', b'<script>alert(1)</script>',
            content_type='text/html')
        r = self.client.post(
            f'/bus/booking/{booking.code}/upload/',
            {'payment_method': 'bca', 'payment_proof': upload})
        self.assertEqual(r.status_code, 302)
        booking.refresh_from_db()
        self.assertFalse(booking.payment_proof)


# =============================================================================
# 15. Log
# =============================================================================
class LogRedactionTest(TestCase):
    def test_filter_menyamarkan_secret_dan_pii(self):
        import logging
        record = logging.LogRecord(
            'x', logging.INFO, __file__, 1,
            'password=hunter2 token=abc Authorization: Bearer xyz '
            'postgresql://user:pass@db/app email=a@b.com phone=081234567890 '
            'url=/bus/booking/NT-ABCD1234/',
            (), None)
        RedactSecretsFilter().filter(record)
        text = record.getMessage()
        for secret in ('hunter2', 'abc', 'xyz', 'user:pass', 'a@b.com',
                       '081234567890', 'NT-ABCD1234'):
            self.assertNotIn(secret, text)
        self.assertIn('[REDACTED]', text)

    def test_traceback_juga_disamarkan(self):
        import logging
        import sys
        try:
            raise RuntimeError('koneksi postgresql://user:pass@db/app gagal')
        except RuntimeError:
            info = sys.exc_info()
        record = logging.LogRecord(
            'x', logging.ERROR, __file__, 1, 'gagal', (), info)
        RedactSecretsFilter().filter(record)
        rendered = logging.Formatter('%(message)s\n%(exc_text)s').format(record)
        self.assertNotIn('user:pass', rendered)
        self.assertIn('[REDACTED]', rendered)

    def test_logging_config_memakai_filter(self):
        self.assertIn('redact_secrets', settings.LOGGING['filters'])
        self.assertIn('redact_secrets', settings.LOGGING['handlers']['console']['filters'])


# =============================================================================
# 16-17. Source map & dependency
# =============================================================================
class DockerImageTest(TestCase):
    def test_dockerignore_tidak_membawa_env_media_atau_git(self):
        path = Path(settings.BASE_DIR) / '.dockerignore'
        self.assertTrue(path.exists())
        entries = {line.strip() for line in path.read_text().splitlines()
                   if line.strip() and not line.startswith('#')}
        for required in ('.env', '.git', 'media', '.venv'):
            self.assertIn(required, entries)


class SourceMapAndDependencyTest(TestCase):
    def test_tidak_ada_source_map_di_static(self):
        maps = list((Path(settings.BASE_DIR) / 'static').rglob('*.map'))
        self.assertEqual(maps, [])

    def test_nginx_memblokir_map_dan_memakai_header_keamanan(self):
        conf = (Path(settings.BASE_DIR) / 'deploy' / 'nginx.conf').read_text()
        for needle in (r'\.map$', 'limit_req_zone', 'X-Frame-Options',
                       'ssl_protocols TLSv1.2 TLSv1.3',
                       'Strict-Transport-Security'):
            self.assertIn(needle, conf)
        # XFF harus ditimpa, bukan menambahkan header kiriman klien.
        self.assertNotIn('$proxy_add_x_forwarded_for', conf)
        self.assertIn('X-Forwarded-For   $remote_addr', conf)

    def test_requirements_memakai_versi_patch_keamanan(self):
        req = (Path(settings.BASE_DIR) / 'requirements.txt').read_text()
        self.assertIn('Django>=6.1.2', req)
        self.assertIn('Pillow>=13.0.0', req)
        self.assertIn('bcrypt>=5.0.0', req)


# =============================================================================
# 18. Backup
# =============================================================================
class BackupTest(TestCase):
    def test_skrip_backup_restore_ada_dan_valid(self):
        deploy = Path(settings.BASE_DIR) / 'deploy'
        for name in ('backup.sh', 'restore.sh', 'verify_backup.sh'):
            path = deploy / name
            self.assertTrue(path.exists(), msg=name)
            self.assertTrue(os.access(path, os.X_OK), msg=f'{name} tidak executable')
            result = subprocess.run(
                ['bash', '-n', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn('verify_backup.sh', (deploy / 'BACKUP.md').read_text())


# =============================================================================
# 19. Security headers
# =============================================================================
class TrustedProxyTest(BaseTestCase):
    def test_header_proto_dari_klien_biasa_dibuang(self):
        req = RequestFactory().get(
            '/', HTTP_X_FORWARDED_PROTO='https',
            REMOTE_ADDR='198.51.100.77')
        TrustedProxyHeadersMiddleware(lambda r: HttpResponse('ok'))(req)
        self.assertFalse(req.is_secure())

    def test_header_proto_dari_proxy_tepercaya_dihormati(self):
        req = RequestFactory().get(
            '/', HTTP_X_FORWARDED_PROTO='https', REMOTE_ADDR='127.0.0.1')
        TrustedProxyHeadersMiddleware(lambda r: HttpResponse('ok'))(req)
        self.assertTrue(req.is_secure())


class SecurityHeadersTest(BaseTestCase):
    def test_header_wajib_pada_halaman_publik(self):
        r = self.client.get('/')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertIn('strict-origin-when-cross-origin', r['Referrer-Policy'])
        self.assertIn("default-src 'self'", r['Content-Security-Policy'])
        self.assertIn("object-src 'none'", r['Content-Security-Policy'])
        self.assertIn("script-src-attr 'none'", r['Content-Security-Policy'])
        self.assertIn('Permissions-Policy', r)
        self.assertIn('Cross-Origin-Opener-Policy', r)
        self.assertIn('Cross-Origin-Resource-Policy', r)
        self.assertNotIn('Server', r)
        # preview/dev: frame-ancestors tidak boleh memblokir iframe sandbox
        self.assertNotIn('frame-ancestors', r['Content-Security-Policy'])

    def test_inline_script_diizinkan_lewat_hash(self):
        r = self.client.get('/')
        csp = r['Content-Security-Policy']
        match = re.search(rb'<script>(.*?)</script>', r.content, re.S)
        self.assertIsNotNone(match)
        digest = base64.b64encode(
            hashlib.sha256(match.group(1)).digest()).decode()
        self.assertIn(f"'sha256-{digest}'", csp)
        # script-src publik tidak memakai unsafe-inline
        script_src = csp.split('script-src ', 1)[1].split(';', 1)[0]
        self.assertNotIn('unsafe-inline', script_src)

    def test_csp_admin_terpisah_dan_tidak_ada_cdn_chart(self):
        r = self.client.get('/admin/login/')
        self.assertIn("script-src 'self' 'unsafe-inline'",
                      r['Content-Security-Policy'])
        self.assertNotIn('cdn.jsdelivr.net', r['Content-Security-Policy'])

    def test_mode_produksi_frame_dan_hsts(self):
        req = RequestFactory().get('/')
        response = HttpResponse(
            b'<html><script>alert(1)</script></html>',
            content_type='text/html; charset=utf-8')
        with override_settings(SECURE_SSL_REDIRECT=True,
                               X_FRAME_OPTIONS='DENY'):
            out = SecurityHeadersMiddleware(lambda r: response)(req)
        self.assertEqual(out['X-Frame-Options'], 'DENY')
        self.assertIn("frame-ancestors 'none'", out['Content-Security-Policy'])
        self.assertIn('upgrade-insecure-requests',
                      out['Content-Security-Policy'])

    def test_tidak_ada_inline_event_handler_di_template(self):
        templates = Path(settings.BASE_DIR) / 'templates'
        offenders = []
        for path in templates.rglob('*.html'):
            text = path.read_text(errors='ignore')
            if re.search(r'\son[a-z]+\s*=', text, re.I):
                offenders.append(str(path.relative_to(templates)))
        self.assertEqual(offenders, [])


# =============================================================================
# 20. Pre-live checks
# =============================================================================
class PreLiveGateTest(BaseTestCase):
    def test_security_audit_menampilkan_20_kontrol(self):
        out = StringIO()
        call_command('security_audit', '--no-fail', '--skip-checks', stdout=out)
        text = out.getvalue()
        self.assertIn('20 kontrol', text)
        self.assertIn('FAIL 0', text)
        for no in range(1, 21):
            self.assertRegex(text, rf'(?m)^\s*{no}\.\s')

    def test_checks_produksi_menolak_konfigurasi_tidak_aman(self):
        with override_settings(
                DEBUG=False, RUNNING_TESTS=False,
                SECRET_KEY='django-insecure-ganti-di-produksi-kunci-rahasia-ini',
                ALLOWED_HOSTS=['*'],
                DATABASES={'default': {'PASSWORD': 'nusantar',
                                       'OPTIONS': {'sslmode': 'disable'}}},
                CSRF_COOKIE_SAMESITE='None', CSRF_COOKIE_SECURE=False,
                SESSION_COOKIE_SECURE=False,
                CSRF_TRUSTED_ORIGINS=['https://*.e2b.app'],
                CORS_ALLOWED_ORIGINS=[], RATELIMIT_ENABLED=True,
                CSP_ENABLED=True, PAYMENT_GATEWAY_PROVIDER=''):
            ids = {issue.id for issue in production_security(None)}
        for expected in ('core.E002', 'core.E003', 'core.E004',
                         'core.E005', 'core.E006', 'core.E008'):
            self.assertIn(expected, ids)

    def test_checks_produksi_lolos_konfigurasi_aman(self):
        with override_settings(
                DEBUG=False, RUNNING_TESTS=False,
                SECRET_KEY='x' * 64, ALLOWED_HOSTS=['example.com'],
                DATABASES={'default': {'PASSWORD': 'StrongDbPass#2026',
                                       'OPTIONS': {'sslmode': 'require'}}},
                CSRF_COOKIE_SAMESITE='Lax', CSRF_COOKIE_SECURE=True,
                SESSION_COOKIE_SECURE=True,
                CSRF_TRUSTED_ORIGINS=['https://example.com'],
                CORS_ALLOWED_ORIGINS=[], RATELIMIT_ENABLED=True,
                CSP_ENABLED=True, ADMIN_ALLOWED_IPS=['10.0.0.0/8'],
                SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=31536000,
                X_FRAME_OPTIONS='DENY', PAYMENT_GATEWAY_PROVIDER=''):
            issues = production_security(None)
        errors = [i for i in issues if i.level >= 40]  # checks.ERROR
        self.assertEqual(errors, [], msg=[(i.id, i.msg) for i in errors])


# =============================================================================
# Factory helpers
# =============================================================================
def _make_schedule(price=50000):
    from booking.models import Bus, City, Route, Schedule
    suffix = str(abs(hash((date.today(), price))) % 100000)
    a = City.objects.create(
        name=f'Asal {suffix}', slug=f'asal-{suffix}', province='Jatim')
    b = City.objects.create(
        name=f'Tujuan {suffix}', slug=f'tujuan-{suffix}', province='Jatim')
    route = Route.objects.create(
        origin=a, destination=b, distance_km=100, duration_minutes=120)
    bus = Bus.objects.create(
        code=f'NT-U{suffix}', name='Bus Uji', plate_number=f'N {suffix} UA',
        bus_class='EKONOMI', rows=2)
    return Schedule.objects.create(
        route=route, bus=bus, departure_time='08:00',
        arrival_time='10:00', price=price)


def _booking_post_data(schedule, seats='1A'):
    return {
        'date': (timezone.localdate() + timedelta(days=1)).isoformat(),
        'seats': seats,
        'contact_name': 'Budi Uji',
        'contact_phone': '081234567890',
        'contact_email': 'budi@example.com',
        'agree': 'on',
    }


def _make_booking(contact_name='Budi Uji'):
    from booking.models import Booking
    schedule = _make_schedule()
    return Booking.objects.create(
        schedule=schedule,
        travel_date=timezone.localdate() + timedelta(days=1),
        contact_name=contact_name, contact_phone='081234567890',
        seats_qty=1, total_price=schedule.price)
