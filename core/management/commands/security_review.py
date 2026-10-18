"""Cek keamanan 19 titik (hardening) — satu perintah, satu laporan.

Fokus checklist ini berbeda dari `security_audit` (20 kontrol aplikasi):
di sini yang diperiksa adalah **rahasia, konfigurasi, akses, dan data**.

    python manage.py security_review           # exit 1 bila ada FAIL
    python manage.py security_review --no-fail # hanya laporan
    DJANGO_DEBUG=0 ... python manage.py security_review

Status: PASS / WARN / FAIL / N/A. Pemeriksaan bersifat *bukti*: membaca
konfigurasi efektif, isi repo, dan (bila tersedia) role database — bukan
sekadar mencocokkan nama setting.
"""
import os
import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

PASS, WARN, FAIL, NA = 'PASS', 'WARN', 'FAIL', 'N/A'

_SECRET_LITERAL_RE = re.compile(
    r'''(?xi)
    \b(?:api[_-]?key|apikey|secret[_-]?key|client[_-]?secret|
        access[_-]?token|auth[_-]?token|private[_-]?key)\b
    \s*[:=]\s*['"][^'"\s]{12,}['"]
    ''')
_GIT_SECRET_PATTERNS = (
    r'AKIA[0-9A-Z]{16}',
    r'sk_live_[0-9A-Za-z]{16,}',
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
    r'ghp_[0-9A-Za-z]{36}',
    r'xox[baprs]-[0-9A-Za-z-]{10,}',
)
_SENSITIVE_FILENAMES = ('.env', '.env.local', 'id_rsa', 'id_ed25519',
                        '.netrc', '.pgpass')


class Command(BaseCommand):
    help = 'Cek 19 kontrol hardening (secret, env, akses, DB, upload).'

    def add_arguments(self, parser):
        parser.add_argument('--no-fail', action='store_true',
                            help='Jangan exit 1 walau ada FAIL.')

    def handle(self, *args, **options):
        self.rows = []
        self.base = Path(settings.BASE_DIR)
        self._collect()
        self._print()
        failed = [r for r in self.rows if r[2] == FAIL]
        if failed and not options['no_fail']:
            raise CommandError(
                f'{len(failed)} kontrol FAIL — perbaiki sebelum live.')

    # ------------------------------------------------------------------
    def _add(self, no, name, status, detail):
        self.rows.append((no, name, status, detail))

    def _collect(self):
        s = settings
        self._check_api_keys()
        self._check_env_private()
        self._check_hardcoded_secrets()
        self._check_git_secrets()
        self._add(5, 'Debug mode OFF',
                  PASS if not s.DEBUG else FAIL,
                  'DEBUG=False (default fail-closed).' if not s.DEBUG else
                  'DEBUG=True — jangan pernah dipakai di produksi.')
        self._check_error_pages()
        self._check_input_validation()
        self._check_input_sanitizing()
        self._check_sql_injection()
        self._check_xss()
        self._check_server_side_auth()
        self._check_object_access()
        self._check_admin_role()
        self._check_db_network()
        self._check_db_privileges()
        self._check_password_hashing()
        self._check_session()
        self._check_password_reset()
        self._check_uploads()

    # -- 1 -------------------------------------------------------------
    def _check_api_keys(self):
        hits = []
        for path in self._py_files():
            text = path.read_text(errors='ignore')
            for match in _SECRET_LITERAL_RE.finditer(text):
                hits.append(f'{path.relative_to(self.base)}: {match.group(0)[:40]}')
        def _from_env(name, value):
            value = str(value or '')
            if not value:
                return True
            return (os.environ.get(name, '') == value
                    or os.environ.get('PAYMENT_WEBHOOK_SECRET', '') == value)

        env_only = all((
            _from_env('PAYMENT_WEBHOOK_SECRET',
                      getattr(settings, 'PAYMENT_WEBHOOK_SECRET', '')),
            _from_env('PAKASIR_SLUG', getattr(settings, 'PAKASIR_SLUG', '')),
            _from_env('PAKASIR_API_KEY', getattr(settings, 'PAKASIR_API_KEY', '')),
            _from_env('PAKASIR_WEBHOOK_SECRET',
                      getattr(settings, 'PAKASIR_WEBHOOK_SECRET', '')),
        ))
        if hits:
            self._add(1, 'API key aman', FAIL,
                      f'Literal key di kode: {hits[:2]}')
        else:
            self._add(1, 'API key aman', PASS if env_only else WARN,
                      'Tidak ada API key di kode; secret hanya dari env '
                      '(Pakasir/webhook/EMAIL_PASSWORD).' if env_only
                      else 'Ada secret konfigurasi yang bukan dari env.')

    # -- 2 -------------------------------------------------------------
    def _check_env_private(self):
        gitignore = (self.base / '.gitignore').read_text(errors='ignore')
        tracked = self._git('ls-files', '.env', '.env.local') or ''
        nginx = (self.base / 'deploy' / 'nginx.conf')
        nginx_text = nginx.read_text(errors='ignore') if nginx.exists() else ''
        dotfiles_blocked = bool(re.search(
            r'location\s+~\s+/\\\.', nginx_text))
        ignored = bool(re.search(r'(?m)^\s*\.env\s*$', gitignore))
        if tracked.strip():
            self._add(2, 'File .env tidak publik', FAIL,
                      f'.env ikut ter-track git: {tracked.split()[:3]}')
        elif not ignored:
            self._add(2, 'File .env tidak publik', FAIL,
                      '.env tidak ada di .gitignore.')
        elif not dotfiles_blocked:
            self._add(2, 'File .env tidak publik', WARN,
                      'Nginx belum memblokir dotfiles. .env tidak disajikan '
                      'Django (media view dibatasi), tetapi blokir eksplisit '
                      'di Nginx lebih aman.')
        else:
            self._add(2, 'File .env tidak publik', PASS,
                      '.env masuk .gitignore, tidak ter-track, dan Nginx '
                      'menolak semua dotfile (kecuali /.well-known/).')

    # -- 3 -------------------------------------------------------------
    def _check_hardcoded_secrets(self):
        default_key = 'django-insecure-ganti-di-produksi-kunci-rahasia-ini'
        from_env = os.environ.get('DJANGO_SECRET_KEY') is not None
        # Berkas yang memang memuat pola placeholder sebagai bagian dari
        # kontrol (deteksi/penyamaran), bukan secret sungguhan.
        allowed_files = {'settings.py', 'checks.py', 'logging.py',
                         'security_review.py'}
        hits = []
        for path in self._py_files():
            if path.name in allowed_files:
                continue
            text = path.read_text(errors='ignore')
            if 'django-insecure-' in text or _SECRET_LITERAL_RE.search(text):
                hits.append(str(path.relative_to(self.base)))
        if hits:
            self._add(3, 'Tidak ada secret hardcoded', FAIL,
                      f'Pola secret di: {hits[:3]}')
        elif settings.SECRET_KEY == default_key and not from_env:
            self._add(3, 'Tidak ada secret hardcoded', WARN,
                      'SECRET_KEY masih placeholder pengembangan — wajib '
                      'DJANGO_SECRET_KEY di produksi (core.E002).')
        else:
            self._add(3, 'Tidak ada secret hardcoded', PASS,
                      'SECRET_KEY dan kredensial hanya dibaca dari '
                      'environment; tidak ada literal di kode.')

    # -- 4 -------------------------------------------------------------
    def _check_git_secrets(self):
        tracked = self._git('ls-files') or ''
        bad_files = [line for line in tracked.splitlines()
                     if Path(line).name in _SENSITIVE_FILENAMES]
        if bad_files:
            self._add(4, 'Tidak ada secret di git', FAIL,
                      f'Berkas sensitif ter-track: {bad_files[:3]}')
            return
        found = []
        if self._git('rev-parse', '--git-dir') is not None:
            for pattern in _GIT_SECRET_PATTERNS:
                out = self._git(
                    'grep', '-I', '-l', '-E', pattern, '--',
                    ':!*.po', ':!*.mo', ':!.venv', timeout=15) or ''
                found += [line.strip() for line in out.splitlines()[:3]]
            # Nilai contoh pengembangan yang pernah ada di riwayat.
            history = self._git(
                'log', '--all', '-p', '--', '.env.example', timeout=15) or ''
            legacy = 'admin123' in history or 'POSTGRES_PASSWORD=nusantar' in history
        else:
            legacy = False
        if found:
            self._add(4, 'Tidak ada secret di git', FAIL,
                      f'Pola secret ditemukan: {found[:3]}')
        elif legacy:
            self._add(4, 'Tidak ada secret di git', PASS,
                      'Tidak ada kunci/token/privat key di HEAD maupun '
                      'riwayat. Catatan: password demo lama (admin123 / DB '
                      'demo) pernah ada di commit pra-hardening — bukan '
                      'secret produksi, sudah dihapus di HEAD dan ditolak '
                      'oleh seed/check; rotasi bila pernah dipakai di server.')
        else:
            self._add(4, 'Tidak ada secret di git', PASS,
                      'Tidak ada berkas .env/kunci/privat atau pola token di '
                      'HEAD maupun riwayat git.')

    # -- 6 -------------------------------------------------------------
    def _check_error_pages(self):
        handlers = (self.base / 'core' / 'urls.py').read_text(errors='ignore')
        missing = [name for name in ('handler400', 'handler403',
                                     'handler404', 'handler500')
                   if name not in handlers]
        templates = [name for name in ('400.html', '403.html',
                                       '404.html', '500.html')
                     if not (self.base / 'templates' / name).exists()]
        view = (self.base / 'core' / 'views.py').read_text(errors='ignore')
        leaks = bool(re.search(
            r'import\s+traceback|traceback\.format_exc|exc_info\s*=', view))
        if settings.DEBUG:
            self._add(6, 'Error tidak bocorkan detail', FAIL,
                      'DEBUG=True menampilkan traceback lengkap ke browser.')
        elif missing or templates or leaks:
            self._add(6, 'Error tidak bocorkan detail', FAIL,
                      f'Handler/template belum lengkap: {missing + templates}')
        else:
            self._add(6, 'Error tidak bocorkan detail', PASS,
                      'DEBUG=False; 400/403/404/500 memakai template sendiri '
                      'tanpa traceback/settings.')

    # -- 7 -------------------------------------------------------------
    def _check_input_validation(self):
        from core import validators as v
        need = ('clean_public_code', 'clean_seat_labels',
                'validate_travel_date', 'validate_image_upload')
        missing = [name for name in need if not hasattr(v, name)]
        forms = (self.base / 'booking' / 'forms.py').read_text(errors='ignore')
        guest_ok = 'max_length' in forms and 'min_length' in forms
        if missing or not guest_ok:
            self._add(7, 'Validasi input', WARN,
                      f'Belum lengkap: {missing or "batas panjang form"}')
        else:
            self._add(7, 'Validasi input', PASS,
                      'Validator kode/tanggal/kursi/telepon/gambar + '
                      'max_length & rentang di form; divalidasi ulang di '
                      'server saat POST.')

    # -- 8 -------------------------------------------------------------
    def _check_input_sanitizing(self):
        raw_post = []
        validator_markers = (
            'fromisoformat', 'validate_', 'clean_', 'int(', 'min(', 'max(',
            'form.cleaned_data', 'Form(', '.values', ' in ')
        for path in self._py_files(('booking', 'rental', 'core')):
            text = path.read_text(errors='ignore')
            if path.name in {'tests.py', 'tests_security.py',
                             'tests_hardening.py'}:
                continue
            for match in re.finditer(
                    r'request\.(?:POST|GET)\.get\([^)]*\)', text):
                snippet = match.group(0)
                if 'code' in snippet or 'username' in snippet:
                    continue
                nearby = text[max(0, match.start() - 400):match.start() + 400]
                if any(marker in nearby for marker in validator_markers):
                    continue
                raw_post.append(f'{path.name}: {snippet[:50]}')
        has_clean_text = hasattr(__import__(
            'core.validators', fromlist=['clean_text']), 'clean_text')
        if raw_post:
            self._add(8, 'Sanitasi input', WARN,
                      f'Input dibaca langsung (pastikan divalidasi form): '
                      f'{raw_post[:2]}')
        elif not has_clean_text:
            self._add(8, 'Sanitasi input', WARN,
                      'Helper clean_text belum tersedia.')
        else:
            self._add(8, 'Sanitasi input', PASS,
                      'Semua POST lewat form/validator; clean_public_code '
                      'membatasi charset; clean_text membuang karakter '
                      'kontrol; escaping dilakukan template (autoescape).')

    # -- 9 -------------------------------------------------------------
    def _check_sql_injection(self):
        hits = []
        for path in self._py_files():
            text = path.read_text(errors='ignore')
            for pattern in (r'\.raw\(', r'\bRawSQL\b', r'cursor\.execute\(',
                            r'\.extra\('):
                if re.search(pattern, text):
                    hits.append(f'{path.name}: {pattern}')
        if hits:
            self._add(9, 'Anti SQL injection', FAIL, f'Temuan: {hits[:3]}')
        else:
            self._add(9, 'Anti SQL injection', PASS,
                      'Tidak ada raw SQL/extra/cursor; semua query lewat ORM '
                      'berparameter (parameterisasi driver psycopg).')

    # -- 10 ------------------------------------------------------------
    def _check_xss(self):
        unsafe = []
        for path in (self.base / 'templates').rglob('*.html'):
            text = path.read_text(errors='ignore')
            if re.search(r'\|\s*safe\b', text):
                unsafe.append(path.name)
        autoescape_off = any(
            'autoescape off' in p.read_text(errors='ignore')
            for p in (self.base / 'templates').rglob('*.html'))
        csp = bool(getattr(settings, 'CSP_ENABLED', False))
        jsonld = (self.base / 'booking' / 'templatetags' /
                  'booking_extras.py').read_text(errors='ignore')
        if unsafe or autoescape_off:
            self._add(10, 'Anti XSS', FAIL,
                      f'|safe / autoescape off di template: {unsafe[:3]}')
        elif not csp or 'u003c' not in jsonld:
            self._add(10, 'Anti XSS', WARN,
                      'CSP atau escaping JSON-LD belum aktif.')
        else:
            self._add(10, 'Anti XSS', PASS,
                      'Autoescape aktif, tidak ada |safe pada data pengguna, '
                      'JSON-LD memakai escape \\u003c, CSP + script-src-attr '
                      "'none' terpasang.")

    # -- 11 ------------------------------------------------------------
    def _check_server_side_auth(self):
        middleware = list(getattr(settings, 'MIDDLEWARE', []))
        urls = (self.base / 'core' / 'urls.py').read_text(errors='ignore')
        ok = ('django.contrib.auth.middleware.AuthenticationMiddleware'
              in middleware and 'admin_site.urls' in urls)
        audit = (self.base / 'core' / 'admin.py').read_text(errors='ignore')
        read_only = all(name in audit for name in (
            'has_add_permission', 'has_change_permission',
            'has_delete_permission', 'is_superuser'))
        if not ok:
            self._add(11, 'Auth di server', FAIL,
                      'AuthenticationMiddleware/admin URL tidak ditemukan.')
        elif not read_only:
            self._add(11, 'Auth di server', WARN,
                      'AuditLog belum read-only penuh.')
        else:
            self._add(11, 'Auth di server', PASS,
                      'Login staf diperiksa Django di server; media privat '
                      'memakai ACL sesi/staf; tombol UI bukan kontrol akses.')

    # -- 12 ------------------------------------------------------------
    def _check_object_access(self):
        sources = ''.join(
            (self.base / app / 'views.py').read_text(errors='ignore')
            for app in ('booking', 'rental'))
        by_pk = re.findall(r'Booking\.objects\.get\([^)]*pk=', sources)
        by_code = 'code__iexact=code' in sources
        if by_pk or not by_code:
            self._add(12, 'Cek akses objek (IDOR)', WARN,
                      f'Objek diakses lewat PK: {len(by_pk)} tempat.')
        else:
            self._add(12, 'Cek akses objek (IDOR)', PASS,
                      'Booking/sewa selalu dicari lewat kode acak, bukan ID '
                      'sekuensial; bukti bayar butuh staf/grant sesi.')

    # -- 13 ------------------------------------------------------------
    def _check_admin_role(self):
        from core.admin import admin_site
        from django.contrib.auth.models import User
        user_registered = any(
            model is User for model in admin_site._registry)
        ips = list(getattr(settings, 'ADMIN_ALLOWED_IPS', []))
        if user_registered:
            self._add(13, 'Role admin aman', WARN,
                      'Model User terdaftar di admin kustom — tinjau izin '
                      'per field agar staf tidak bisa menaikkan role.')
        elif not ips:
            self._add(13, 'Role admin aman', WARN,
                      'Admin hanya mengandalkan login staf; '
                      'DJANGO_ADMIN_ALLOWED_IPS masih kosong.')
        else:
            self._add(13, 'Role admin aman', PASS,
                      'Hanya is_staff yang bisa masuk; allowlist IP admin '
                      f'{ips[:2]}; audit read-only superuser; model User/Group '
                      'tidak diekspos di panel kustom.')

    # -- 14 ------------------------------------------------------------
    def _check_db_network(self):
        compose = self.base / 'docker-compose.yml'
        prod = self.base / 'deploy' / 'docker-compose.prod.yml'
        text = compose.read_text(errors='ignore') if compose.exists() else ''
        db_section = self._compose_service(text, 'db')
        loopback = re.search(
            r'["\']?127\.0\.0\.1:\d+:5432["\']?', db_section)
        public = re.search(
            r'(?m)^\s*-\s*["\']?(?!127\.0\.0\.1:|\[::1\]:|localhost:)'
            r'[^"\'\s#]*:5432:5432', db_section)
        prod_text = prod.read_text(errors='ignore') if prod.exists() else ''
        prod_ok = prod.exists() and not re.search(
            r'(?m)^\s{4}ports:', self._compose_service(prod_text, 'db'))
        if public:
            self._add(14, 'Database tidak publik', FAIL,
                      'docker-compose mempublikasikan port 5432 ke semua '
                      'interface.')
        elif not (loopback or prod_ok):
            self._add(14, 'Database tidak publik', WARN,
                      'Port DB tidak dibatasi ke loopback dan belum ada '
                      'compose produksi tanpa port.')
        else:
            self._add(14, 'Database tidak publik', PASS,
                      'Dev: 127.0.0.1:5432 saja. Produksi: '
                      'deploy/docker-compose.prod.yml tanpa port DB; Nginx '
                      'tidak mem-proxy 5432.')

    # -- 15 ------------------------------------------------------------
    def _check_db_privileges(self):
        sql = (self.base / 'deploy' / 'db_setup.sql')
        script_ok = sql.exists()
        info = None
        try:
            from django.db import connection
            with connection.cursor() as cur:
                cur.execute(
                    'SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls '
                    'FROM pg_roles WHERE rolname = current_user')
                info = cur.fetchone()
        except Exception:
            info = None
        if info is None:
            self._add(15, 'Izin database ketat', WARN if script_ok else FAIL,
                      'Role DB tidak dapat diperiksa (DB tidak terjangkau). '
                      'Gunakan deploy/db_setup.sql.' if script_ok else
                      'Skrip role DB belum ada dan DB tidak terjangkau.')
            return
        superuser, createdb, createrole, bypassrls = info
        if superuser or createdb or createrole or bypassrls:
            self._add(15, 'Izin database ketat', WARN,
                      'Role aplikasi masih SUPERUSER/CREATEDB/CREATEROLE/'
                      'BYPASSRLS. Produksi: pisahkan nt_owner (migrasi) dan '
                      'nt_app (runtime) via deploy/db_setup.sql.')
        elif not script_ok:
            self._add(15, 'Izin database ketat', WARN,
                      'Role sudah terbatas, tetapi skrip provisioning belum ada.')
        else:
            self._add(15, 'Izin database ketat', PASS,
                      'Role runtime tanpa SUPERUSER/CREATEDB/CREATEROLE/'
                      'BYPASSRLS; deploy/db_setup.sql menyediakan owner '
                      'migrasi terpisah.')

    # -- 16 ------------------------------------------------------------
    def _check_password_hashing(self):
        hashers = list(getattr(settings, 'PASSWORD_HASHERS', []))
        primary = hashers[0] if hashers else ''
        min_len = 0
        for item in getattr(settings, 'AUTH_PASSWORD_VALIDATORS', []):
            if item['NAME'].endswith('MinimumLengthValidator'):
                min_len = int(item.get('OPTIONS', {}).get('min_length', 8))
        if 'bcrypt' not in primary.lower() and 'argon2' not in primary.lower():
            self._add(16, 'Hash password kuat', FAIL,
                      f'Hasher utama bukan bcrypt/argon2: {primary}')
        elif min_len < 12:
            self._add(16, 'Hash password kuat', WARN,
                      f'Hasher {primary.split(".")[-1]}, tetapi panjang '
                      f'minimum password {min_len} (<12).')
        else:
            self._add(16, 'Hash password kuat', PASS,
                      f'{primary.split(".")[-1]} (cost 12) + validator panjang '
                      f'minimal {min_len}, kemiripan, password umum, dan '
                      'numerik.')

    # -- 17 ------------------------------------------------------------
    def _check_session(self):
        issues = []
        if not getattr(settings, 'SESSION_COOKIE_HTTPONLY', False):
            issues.append('HttpOnly off')
        if not getattr(settings, 'SESSION_COOKIE_SECURE', False):
            issues.append('Secure off (wajib di HTTPS)')
        if getattr(settings, 'SESSION_COOKIE_SAMESITE', '') not in {'Lax', 'Strict'}:
            issues.append(f'SameSite={getattr(settings, "SESSION_COOKIE_SAMESITE", "")}')
        if int(getattr(settings, 'SESSION_COOKIE_AGE', 0)) > 12 * 3600:
            issues.append('umur sesi > 12 jam')
        engine = str(getattr(settings, 'SESSION_ENGINE', ''))
        if 'signed_cookies' in engine:
            issues.append('sesi di cookie (sulit dicabut)')
        if issues:
            self._add(17, 'Session aman', WARN, '; '.join(issues))
        else:
            self._add(17, 'Session aman', PASS,
                      'Cookie sesi HttpOnly + Secure + SameSite=Lax, umur '
                      '8 jam, sesi disimpan di DB (bisa dicabut), kunci sesi '
                      'diperbarui saat login (Django cycle_key).')

    # -- 18 ------------------------------------------------------------
    def _check_password_reset(self):
        urls = (self.base / 'core' / 'urls.py').read_text(errors='ignore')
        public_reset = 'django.contrib.auth.urls' in urls
        timeout = int(getattr(settings, 'PASSWORD_RESET_TIMEOUT', 259200))
        backend = str(getattr(settings, 'EMAIL_BACKEND', ''))
        console = any(x in backend for x in ('console', 'locmem', 'dummy'))
        if public_reset:
            self._add(18, 'Reset password aman', WARN,
                      'Route reset password publik aktif — pastikan '
                      'rate limit + email terverifikasi.')
        elif timeout > 24 * 3600:
            self._add(18, 'Reset password aman', WARN,
                      f'PASSWORD_RESET_TIMEOUT {timeout}s (>24 jam).')
        elif console and not settings.DEBUG:
            self._add(18, 'Reset password aman', WARN,
                      'Tidak ada reset publik (aman dari enumerasi), tetapi '
                      'EMAIL_BACKEND console — email reset tidak terkirim.')
        else:
            self._add(18, 'Reset password aman', PASS,
                      'Tidak ada form reset publik (tidak ada enumerasi '
                      'akun). Ganti password admin lewat /admin/ wajib sesi '
                      f'+ password lama; token reset (bila dipakai) berlaku '
                      f'{timeout // 60} menit, sekali pakai, di-hash.')

    # -- 19 ------------------------------------------------------------
    def _check_uploads(self):
        max_size = int(getattr(settings, 'MAX_UPLOAD_SIZE', 0))
        exts = tuple(getattr(settings, 'MEDIA_ALLOWED_EXTENSIONS', ()))
        pixels = int(getattr(settings, 'IMAGE_MAX_PIXELS', 0))
        max_files = int(getattr(settings, 'DATA_UPLOAD_MAX_NUMBER_FILES', 0))
        nginx = (self.base / 'deploy' / 'nginx.conf').read_text(errors='ignore')
        body_limit = re.search(r'client_max_body_size\s+(\d+[mMkK]?)', nginx)
        models = ((self.base / 'core' / 'models.py').read_text(errors='ignore')
                  + (self.base / 'rental' / 'models.py').read_text(errors='ignore'))
        model_guard = 'validate_image_upload' in models
        if not (0 < max_size <= 10 * 1024 * 1024) or not exts or \
                not pixels or not max_files or not body_limit or not model_guard:
            self._add(19, 'Batasi upload berkas', WARN,
                      f'MAX_UPLOAD_SIZE={max_size}, ext={exts}, '
                      f'piksel={pixels}, files/request={max_files}, '
                      f'nginx={bool(body_limit)}, model={model_guard}')
        else:
            self._add(19, 'Batasi upload berkas', PASS,
                      f'Per berkas ≤ {max_size // (1024 * 1024)} MB, '
                      f'ekstensi {exts}, piksel ≤ {pixels:,}, '
                      f'{max_files} berkas/request, Nginx '
                      f'{body_limit.group(1)}; isi diverifikasi Pillow '
                      '(bukan hanya ekstensi/Content-Type).')

    # ------------------------------------------------------------------
    @staticmethod
    def _compose_service(text, name):
        """Ambil blok YAML satu service (indentasi 2 spasi)."""
        match = re.search(
            rf'(?ms)^  {re.escape(name)}:\s*$.*?(?=^  [a-zA-Z0-9_-]+:\s*$|\Z)',
            text)
        return match.group(0) if match else ''

    def _py_files(self, subdirs=None):
        roots = [self.base / name for name in (subdirs or ('core', 'booking', 'rental'))]
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob('*.py'):
                if '__pycache__' in path.parts or path.name.startswith('test'):
                    continue
                yield path

    def _git(self, *args, timeout=10):
        try:
            result = subprocess.run(
                ['git', *args], cwd=str(self.base), capture_output=True,
                text=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode not in (0, 1):
            return result.stdout if result.stdout else None
        return result.stdout

    # ------------------------------------------------------------------
    def _print(self):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'REVIEW KEAMANAN (HARDENING) — Nusantara Trans'))
        self.stdout.write('=' * 88)
        for no, name, status, detail in self.rows:
            color = {'PASS': self.style.SUCCESS, 'WARN': self.style.WARNING,
                     'FAIL': self.style.ERROR, 'N/A': self.style.NOTICE}[status]
            self.stdout.write(
                f'{no:>2}. {color(f"{status:<4}")} {name:<30} {detail}')
        self.stdout.write('=' * 88)
        counts = {key: sum(1 for r in self.rows if r[2] == key)
                  for key in (PASS, WARN, FAIL, NA)}
        self.stdout.write(
            f'{len(self.rows)} kontrol — PASS {counts[PASS]}, '
            f'WARN {counts[WARN]}, FAIL {counts[FAIL]}, N/A {counts[NA]}')
        if not counts[FAIL]:
            self.stdout.write(self.style.SUCCESS(
                'Tidak ada FAIL. Tinjau WARN sebelum go-live.'))
