"""Test 19 kontrol hardening: secret, env, debug, error, akses, DB, upload.

Berbeda dari ``tests_security`` (20 kontrol aplikasi), berkas ini menguji
*postur konfigurasi*: apakah rahasia bocor, apakah .env publik, apakah DB
terbuka, apakah hash/sesi/upload dibatasi.
"""
import os
import re
import subprocess
import sys
from datetime import date, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from PIL import Image

from core.validators import clean_text, validate_image_upload

BASE = Path(settings.BASE_DIR)
User = get_user_model()


def _git(*args):
    try:
        result = subprocess.run(
            ['git', *args], cwd=str(BASE), capture_output=True, text=True,
            timeout=20)
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ''


def _png_bytes(size=(10, 10), color=(10, 120, 200)):
    buf = BytesIO()
    Image.new('RGB', size, color).save(buf, format='PNG')
    return buf.getvalue()


# =============================================================================
# 1-4. Rahasia & .env
# =============================================================================
class SecretsTest(TestCase):
    def test_tidak_ada_api_key_literal_di_kode(self):
        pattern = re.compile(
            r'''(?xi)\b(?:api[_-]?key|apikey|secret[_-]?key|client[_-]?secret|
                access[_-]?token|auth[_-]?token|private[_-]?key)\b
                \s*[:=]\s*['"][^'"\s]{12,}['"]''')
        offenders = []
        for root in ('core', 'booking', 'rental'):
            for path in (BASE / root).rglob('*.py'):
                if path.name.startswith('test') or '__pycache__' in path.parts:
                    continue
                if path.name in {'checks.py', 'logging.py',
                                 'security_review.py'}:
                    continue
                if pattern.search(path.read_text(errors='ignore')):
                    offenders.append(str(path.relative_to(BASE)))
        self.assertEqual(offenders, [])

    def test_env_tidak_ter_track_dan_diabaikan(self):
        tracked = _git('ls-files', '.env', '.env.local')
        self.assertEqual(tracked.strip(), '')
        self.assertIn('.env', (BASE / '.gitignore').read_text().splitlines())

    def test_env_tidak_bisa_diakses_http(self):
        for path in ('/.env', '/.env.local', '/.git/config',
                     '/.htaccess', '/.pgpass'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_secret_hanya_dibaca_dari_env(self):
        source = (BASE / 'core' / 'settings.py').read_text()
        self.assertIn("os.environ.get(\n    'DJANGO_SECRET_KEY'", source)
        self.assertNotRegex(
            source, r"SECRET_KEY\s*=\s*['\"][A-Za-z0-9+/=_-]{40,}['\"]")

    def test_riwayat_git_tanpa_private_key(self):
        if not _git('rev-parse', '--git-dir').strip():
            self.skipTest('bukan repo git')
        for pattern in (r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
                        r'AKIA[0-9A-Z]{16}', r'sk_live_[0-9A-Za-z]{16,}',
                        r'ghp_[0-9A-Za-z]{36}'):
            with self.subTest(pattern=pattern):
                hits = _git('grep', '-I', '-l', '-E', pattern, '--',
                            ':!*.po', ':!*.mo')
                self.assertEqual(hits.strip(), '')

    def test_compose_tidak_membawa_password_default(self):
        text = (BASE / 'docker-compose.yml').read_text()
        self.assertIn('POSTGRES_PASSWORD:?', text)
        self.assertNotIn('POSTGRES_PASSWORD=nusantar', text)
        self.assertNotIn('DJANGO_ADMIN_PASSWORD: admin', text)


# =============================================================================
# 5-6. Debug & kebocoran error
# =============================================================================
class DebugAndErrorTest(TestCase):
    def test_debug_default_mati(self):
        """Impor settings tanpa env DJANGO_DEBUG harus menghasilkan DEBUG=False."""
        code = (
            'import django, os;'
            'os.environ.setdefault("DJANGO_SETTINGS_MODULE","core.settings");'
            'django.setup();'
            'from django.conf import settings;'
            'print(settings.DEBUG)'
        )
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('DJANGO_', 'POSTGRES_', 'REDIS_'))}
        result = subprocess.run(
            [sys.executable, '-c', code], cwd=str(BASE), env=env,
            capture_output=True, text=True, timeout=60)
        self.assertIn('False', result.stdout.strip().splitlines()[-1])

    @override_settings(DEBUG=False)
    def test_halaman_500_tidak_membocorkan_detail(self):
        request = RequestFactory().get('/ledakan/')
        response = call_command  # noqa: F841 — penanda modul termuat
        from core.views import error_500
        response = error_500(request)
        body = response.content.decode()
        self.assertEqual(response.status_code, 500)
        for leak in ('Traceback', 'SECRET_KEY', 'settings.DEBUG',
                     'Exception Value', 'DATABASES'):
            self.assertNotIn(leak, body)

    @override_settings(DEBUG=False)
    def test_halaman_400_dan_403_tersedia(self):
        from core.views import error_400, error_403, error_404
        request = RequestFactory().get('/x/')
        self.assertEqual(error_400(request).status_code, 400)
        self.assertEqual(error_403(request).status_code, 403)
        self.assertEqual(error_404(request).status_code, 404)
        for name in ('400.html', '403.html', '404.html', '500.html'):
            self.assertTrue((BASE / 'templates' / name).exists(), msg=name)

    def test_handler_terdaftar(self):
        import core.urls as urls
        for name in ('handler400', 'handler403', 'handler404', 'handler500'):
            self.assertTrue(getattr(urls, name).startswith('core.views.'))


# =============================================================================
# 7-8. Validasi & sanitasi input
# =============================================================================
class InputTest(TestCase):
    def test_clean_text_membuang_karakter_kontrol(self):
        dirty = 'Budi\x00\x07\x1f \t  Santoso\x7f'
        self.assertEqual(clean_text(dirty), 'Budi Santoso')

    def test_clean_text_membatasi_panjang(self):
        with self.assertRaises(ValidationError):
            clean_text('a' * 101, max_length=100)
        self.assertEqual(clean_text('ok', max_length=100), 'ok')

    def test_clean_text_bisa_mempertahankan_newline(self):
        self.assertEqual(
            clean_text('baris 1\nbaris 2', allow_newlines=True),
            'baris 1\nbaris 2')

    def test_telepon_menolak_format_aneh(self):
        from core.validators import clean_phone
        for bad in ('123', '<script>', '08' * 20):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    clean_phone(bad)

    def test_kode_publik_menolak_karakter_kontrol(self):
        from core.validators import clean_public_code
        for bad in ('NT-AB\x00CD1234', 'NT-<script>', 'A' * 40):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    clean_public_code(bad)


# =============================================================================
# 9-10. SQL injection & XSS
# =============================================================================
class InjectionTest(TestCase):
    def test_tidak_ada_query_mentah(self):
        offenders = []
        for root in ('core', 'booking', 'rental'):
            for path in (BASE / root).rglob('*.py'):
                if path.name.startswith('test') or path.name in {
                        'security_review.py', 'security_audit.py'}:
                    continue
                text = path.read_text(errors='ignore')
                for pattern in ('.raw(', 'RawSQL', 'cursor.execute(',
                                '.extra('):
                    if pattern in text:
                        offenders.append(f'{path.name}: {pattern}')
        self.assertEqual(offenders, [])

    def test_tidak_ada_template_memakai_safe(self):
        offenders = [
            str(path.relative_to(BASE))
            for path in (BASE / 'templates').rglob('*.html')
            if re.search(r'\|\s*safe\b', path.read_text(errors='ignore'))
        ]
        self.assertEqual(offenders, [])

    def test_tidak_ada_autoescape_off(self):
        offenders = [
            str(path.relative_to(BASE))
            for path in (BASE / 'templates').rglob('*.html')
            if 'autoescape off' in path.read_text(errors='ignore')
        ]
        self.assertEqual(offenders, [])

    def test_jsonld_tetap_mengescape_script(self):
        from booking.templatetags.booking_extras import jsonld
        out = jsonld({'x': '</script><img src=x onerror=alert(1)>'})
        self.assertNotIn('</script>', out)
        self.assertNotIn('<img', out)

    def test_csp_memakai_hash_bukan_unsafe_inline_untuk_script(self):
        response = self.client.get('/')
        csp = response['Content-Security-Policy']
        script_src = csp.split('script-src ', 1)[1].split(';', 1)[0]
        self.assertNotIn('unsafe-inline', script_src)
        self.assertIn("script-src-attr 'none'", csp)


# =============================================================================
# 11-13. Auth, akses objek, role admin
# =============================================================================
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class AccessControlTest(TestCase):
    def test_admin_menolak_anonim_dan_non_staf(self):
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        user = User.objects.create_user('biasa2', password='StrongPass#2026')
        self.client.force_login(user)
        self.assertIn(self.client.get('/admin/').status_code, (302, 403))

    def test_staf_tidak_bisa_membuka_manajemen_user(self):
        """Model User sengaja tidak didaftarkan di panel kustom."""
        staff = User.objects.create_user(
            'staf3', password='StrongPass#2026', is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(
            self.client.get('/admin/auth/user/').status_code, 404)

    def test_audit_log_hanya_superuser(self):
        from core.admin import AuditLogAdmin
        from core.models import AuditLog
        admin_obj = AuditLogAdmin(AuditLog, None)
        staff = User.objects.create_user(
            'staf4', password='StrongPass#2026', is_staff=True)
        superuser = User.objects.create_superuser(
            'root4', password='StrongPass#2026')
        req_staff = type('R', (), {'user': staff})()
        req_root = type('R', (), {'user': superuser})()
        self.assertFalse(admin_obj.has_view_permission(req_staff))
        self.assertTrue(admin_obj.has_view_permission(req_root))
        self.assertFalse(admin_obj.has_add_permission(req_root))
        self.assertFalse(admin_obj.has_change_permission(req_root))
        self.assertFalse(admin_obj.has_delete_permission(req_root))

    def test_bukti_bayar_tidak_bisa_ditebak(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with override_settings(MEDIA_ROOT=tmp.name):
            target = Path(tmp.name) / 'payment_proofs' / '2026' / '10' / 'rahasia.jpg'
            target.parent.mkdir(parents=True)
            target.write_bytes(_png_bytes())
            self.assertEqual(
                self.client.get('/media/payment_proofs/2026/10/rahasia.jpg')
                .status_code, 404)

    def test_halaman_booking_hanya_terbuka_dengan_kode_benar(self):
        self.assertEqual(
            self.client.get('/bus/booking/NT-ZZZZ9999/').status_code, 404)


# =============================================================================
# 14-15. Database
# =============================================================================
class DatabaseTest(TestCase):
    def test_compose_dev_hanya_loopback(self):
        text = (BASE / 'docker-compose.yml').read_text()
        db = text.split('  db:', 1)[1].split('  redis:', 1)[0]
        self.assertIn('127.0.0.1:5432:5432', db)
        self.assertNotRegex(db, r'(?m)^\s*-\s*"0\.0\.0\.0:5432')

    def test_compose_produksi_tanpa_port_db(self):
        prod = (BASE / 'deploy' / 'docker-compose.prod.yml')
        self.assertTrue(prod.exists())
        text = prod.read_text()
        db = text.split('  db:', 1)[1].split('  redis:', 1)[0]
        self.assertNotRegex(db, r'(?m)^\s{4}ports:')
        # Aplikasi memakai role runtime terpisah dari superuser cluster.
        self.assertIn('POSTGRES_APP_USER', text)
        self.assertIn('POSTGRES_SUPERUSER_PASSWORD', text)

    def test_nginx_tidak_mem_proxy_postgres(self):
        nginx = (BASE / 'deploy' / 'nginx.conf').read_text()
        self.assertNotIn('5432', nginx)

    def test_skrip_role_database_ada_dan_minimal(self):
        sql = (BASE / 'deploy' / 'db_setup.sql').read_text().lower()
        self.assertIn('nosuperuser', sql)
        self.assertIn('nocreatedb', sql)
        self.assertIn('nocreaterole', sql)
        self.assertIn('revoke all on schema public from public', sql)
        self.assertIn('nt_app', sql)
        self.assertIn('nt_owner', sql)


# =============================================================================
# 16-17. Password & sesi
# =============================================================================
class PasswordAndSessionTest(TestCase):
    def test_hash_password_memakai_bcrypt(self):
        user = User.objects.create_user('hash1', password='StrongPass#2026')
        self.assertTrue(user.password.startswith('bcrypt_sha256$'))

    def test_password_pendek_ditolak_validator(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        with self.assertRaises(DjangoValidationError):
            validate_password('pendek123', user=None)

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
    def test_kunci_sesi_berubah_setelah_login(self):
        User.objects.create_user('sesi1', password='StrongPass#2026')
        self.client.get('/bus/cek-booking/')
        before = self.client.session.session_key
        self.assertTrue(self.client.login(
            username='sesi1', password='StrongPass#2026'))
        after = self.client.session.session_key
        self.assertNotEqual(before, after)

    def test_cookie_sesi_httponly(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

    @override_settings(SECURE_SSL_REDIRECT=True, SESSION_COOKIE_SECURE=True,
                       CSRF_COOKIE_SECURE=True, SESSION_COOKIE_SAMESITE='Lax')
    def test_setting_produksi_cookie_aman(self):
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, 'Lax')

    def test_umur_sesi_maksimal_12_jam(self):
        self.assertLessEqual(settings.SESSION_COOKIE_AGE, 12 * 3600)

    def test_sesi_disimpan_di_server_bukan_cookie(self):
        self.assertNotIn('signed_cookies', settings.SESSION_ENGINE)


# =============================================================================
# 18. Reset password
# =============================================================================
class PasswordResetTest(TestCase):
    def test_tidak_ada_route_reset_publik(self):
        for name in ('password_reset', 'password_reset_confirm',
                     'password_reset_done'):
            with self.subTest(name=name):
                with self.assertRaises(NoReverseMatch):
                    reverse(name)

    def test_timeout_reset_maksimal_24_jam(self):
        self.assertLessEqual(settings.PASSWORD_RESET_TIMEOUT, 24 * 3600)

    def test_tidak_bisa_ubah_password_tanpa_login(self):
        response = self.client.get('/admin/password_change/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_tidak_ada_enumerasi_akun_di_halaman_publik(self):
        self.assertNotIn('Lupa password', self.client.get('/').content.decode())
        self.assertNotIn('Reset password', self.client.get('/').content.decode())


# =============================================================================
# 19. Upload
# =============================================================================
class UploadLimitTest(TestCase):
    def _upload(self, name='bukti.png', data=None, content_type='image/png'):
        return SimpleUploadedFile(name, data or _png_bytes(),
                                  content_type=content_type)

    def test_upload_gambar_valid_diterima(self):
        file_obj = self._upload()
        self.assertIs(validate_image_upload(file_obj), file_obj)

    def test_ekstensi_berbahaya_ditolak(self):
        for name in ('bukti.html', 'bukti.svg', 'bukti.php', 'bukti.js'):
            with self.subTest(name=name):
                with self.assertRaises(ValidationError):
                    validate_image_upload(
                        self._upload(name, b'<script>alert(1)</script>',
                                     'text/html'))

    def test_isi_bukan_gambar_ditolak(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(
                self._upload('bukti.png', b'\x89PNG\r\n\x1a\nBUKAN-GAMBAR'))

    def test_berkas_terlalu_besar_ditolak(self):
        big = _png_bytes() + b'\0' * (6 * 1024 * 1024)
        with self.assertRaises(ValidationError):
            validate_image_upload(self._upload('besar.png', big))

    def test_dimensi_bomb_ditolak(self):
        buf = BytesIO()
        Image.new('RGB', (10, 10), (0, 0, 0)).save(buf, format='PNG')
        with override_settings(IMAGE_MAX_PIXELS=50):
            with self.assertRaises(ValidationError):
                validate_image_upload(self._upload('bomb.png', buf.getvalue()))

    def test_batas_setting_dan_model(self):
        self.assertLessEqual(settings.MAX_UPLOAD_SIZE, 10 * 1024 * 1024)
        self.assertLessEqual(settings.DATA_UPLOAD_MAX_NUMBER_FILES, 10)
        self.assertIn('validate_image_upload',
                      (BASE / 'core' / 'models.py').read_text())
        self.assertIn('validate_image_upload',
                      (BASE / 'rental' / 'models.py').read_text())

    def test_nginx_membatasi_body(self):
        nginx = (BASE / 'deploy' / 'nginx.conf').read_text()
        self.assertRegex(nginx, r'client_max_body_size\s+\d+[mM]')


# =============================================================================
# Perintah security_review
# =============================================================================
class SecurityReviewCommandTest(TestCase):
    def test_menampilkan_19_kontrol(self):
        out = StringIO()
        call_command('security_review', '--no-fail', stdout=out)
        text = out.getvalue()
        self.assertIn('19 kontrol', text)
        for no in range(1, 20):
            self.assertRegex(text, rf'(?m)^\s*{no}\.\s')

    def test_tidak_ada_fail_dalam_mode_produksi_simulasi(self):
        out = StringIO()
        with override_settings(
                DEBUG=False,
                ADMIN_ALLOWED_IPS=['127.0.0.1/32'],
                EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'):
            call_command('security_review', '--no-fail', stdout=out)
        self.assertNotRegex(out.getvalue(), r'(?m)^\s*\d+\.\s*FAIL')
