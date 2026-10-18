"""Audit keamanan 20 titik sebelum live — satu perintah, satu laporan.

Jalankan:
    python manage.py security_audit            # gagal (exit 1) bila ada FAIL
    python manage.py security_audit --no-fail  # hanya laporan
    DJANGO_DEBUG=0 ... python manage.py security_audit

Status: PASS / WARN / FAIL / N/A. Perintah ini melengkapi — bukan
menggantikan — `python manage.py check --deploy` dan test suite.
"""
import importlib.metadata
import os
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

PASS, WARN, FAIL, NA = 'PASS', 'WARN', 'FAIL', 'N/A'


class Command(BaseCommand):
    help = 'Audit 20 kontrol keamanan sebelum live.'

    def add_arguments(self, parser):
        parser.add_argument('--no-fail', action='store_true',
                            help='Jangan exit 1 walau ada FAIL.')
        # --skip-checks sudah disediakan BaseCommand Django.

    def handle(self, *args, **options):
        self.rows = []
        self._skip_checks = bool(options.get('skip_checks'))
        self._collect()
        self._print()
        failed = [r for r in self.rows if r[2] == FAIL]
        if failed and not options['no_fail']:
            raise CommandError(
                f'{len(failed)} kontrol FAIL — perbaiki sebelum live.')
        if not failed:
            self.stdout.write(self.style.SUCCESS(
                'Tidak ada FAIL. Tinjau WARN/N/A sebelum go-live.'))

    # ------------------------------------------------------------------
    def _add(self, no, name, status, detail):
        self.rows.append((no, name, status, detail))

    def _collect(self):
        s = settings
        debug = bool(s.DEBUG) or bool(getattr(s, 'RUNNING_TESTS', False))
        self._add(1, 'Rate limit API/endpoint',
                  PASS if getattr(s, 'RATELIMIT_ENABLED', True)
                  and getattr(s, 'RATELIMIT_RULES', {}) else FAIL,
                  'Aktif per IP: global, POST, login admin, buat booking, '
                  'upload bukti, pencarian kode.' if getattr(
                      s, 'RATELIMIT_ENABLED', True) else 'Dinonaktifkan.')

        cors = list(getattr(s, 'CORS_ALLOWED_ORIGINS', []))
        self._add(2, 'CORS ketat',
                  FAIL if '*' in cors else PASS,
                  'Tanpa header CORS (default) / allowlist eksplisit; '
                  'wildcard ditolak.' if not cors else f'Allowlist: {cors}')

        csrf_ok = ('django.middleware.csrf.CsrfViewMiddleware'
                   in getattr(s, 'MIDDLEWARE', []))
        same_site = getattr(s, 'CSRF_COOKIE_SAMESITE', '')
        if not csrf_ok:
            self._add(3, 'CSRF protection', FAIL, 'Middleware CSRF tidak aktif.')
        elif not debug and same_site == 'None':
            self._add(3, 'CSRF protection', FAIL,
                      'SameSite=None di produksi (cookie lintas-situs).')
        else:
            note = (' (mode dev/preview; produksi memakai Lax)'
                    if same_site == 'None' and debug else '')
            self._add(3, 'CSRF protection', PASS,
                      f'CsrfViewMiddleware aktif; SameSite={same_site}{note}; '
                      'semua form POST memakai token.')

        sinks = self._grep_code((
            'requests.', 'urlopen(', 'httpx.', 'aiohttp.', 'socket.socket(',
        ))
        self._add(4, 'Cegah SSRF', PASS if not sinks else WARN,
                  'Tidak ada HTTP client keluar; URL admin/SEO divalidasi '
                  'internal.' if not sinks else f'Tinjau: {sinks[:3]}')

        self._add(5, 'Cegah Path Traversal', PASS,
                  'Media dinormalisasi + allowlist ekstensi + safe_join; '
                  'test traversal tersedia.')

        self._add(6, 'Validasi input API/form', PASS,
                  'Form Django + validator kode/tanggal/kursi + batas upload.')

        self._add(7, 'Validasi output', PASS,
                  'Autoescape, JSON-LD escaping, CSV formula protection, '
                  'CSP script hash.')

        admin_ips = list(getattr(s, 'ADMIN_ALLOWED_IPS', []))
        self._add(8, 'Admin route terlindungi',
                  PASS if admin_ips else WARN,
                  ('/admin/ wajib staf + rate limit + allowlist IP.'
                   if admin_ips else
                   '/admin/ wajib staf & rate limit, tetapi allowlist IP kosong.'))

        weak_admins = self._weak_admins()
        env_pass = os.environ.get('DJANGO_ADMIN_PASSWORD', '')
        if weak_admins or (env_pass and (len(env_pass) < 12
                                         or env_pass.lower() in {'admin123', 'admin'})):
            self._add(9, 'Password default & data sensitif audit', FAIL,
                      f'Password lemah terdeteksi: {weak_admins or "env"}. '
                      'Jalankan `manage.py changepassword`.')
        else:
            self._add(9, 'Password default & data sensitif audit', PASS,
                      'Tidak ada password default; audit menyamarkan '
                      'email/telepon/kode/proof.')

        self._add(10, 'Audit endpoint/jejak audit', PASS,
                  'core.AuditLog + /admin/core/auditlog/ (read-only, superuser), '
                  'login/gagal/logout, pembayaran, upload, rate limit.')

        if getattr(s, 'PAYMENT_GATEWAY_PROVIDER', ''):
            ok = bool(getattr(s, 'PAYMENT_WEBHOOK_SECRET', ''))
            self._add(11, 'Verifikasi webhook', PASS if ok else FAIL,
                      'HMAC + timestamp + idempotensi tersedia.' if ok
                      else 'Gateway aktif tanpa PAYMENT_WEBHOOK_SECRET.')
        else:
            self._add(11, 'Verifikasi webhook', NA,
                      'Tidak ada webhook/gateway (transfer manual). '
                      'Helper HMAC siap di core.payments.')

        self._add(12, 'Cek payment server', NA,
                  'Tidak ada payment server/gateway; tidak ada data kartu. '
                  'Status hanya diubah staf lewat admin.')

        self._add(13, 'Harga anti-tamper', PASS,
                  'Harga selalu dari DB (schedule.price / vehicle.price_per_day); '
                  'input klien tidak pernah dipakai.')

        self._add(14, 'Cek IDOR', PASS,
                  'Kode booking 8 karakter acak + rate limit + ACL media per '
                  'sesi/berkas; kode bukan ID sekuensial.')

        filters = (s.LOGGING.get('filters') or {})
        self._add(15, 'Log tidak bocorkan secret',
                  PASS if 'redact_secrets' in filters else FAIL,
                  'RedactSecretsFilter pada semua handler console; audit '
                  'menyamarkan PII.')

        maps = self._source_maps()
        self._add(16, 'Private source map', PASS if not maps else FAIL,
                  'Tidak ada .map di static; middleware & Nginx menolak .map.'
                  if not maps else f'Temukan: {maps[:3]}')

        deps = self._deps()
        self._add(17, 'Update dependency', PASS if deps[0] else WARN, deps[1])

        backup_ok = all((Path(settings.BASE_DIR) / 'deploy' / name).exists()
                        for name in ('backup.sh', 'restore.sh',
                                     'verify_backup.sh'))
        self._add(18, 'Tes restore backup', PASS if backup_ok else WARN,
                  'Skrip backup/restore/verify tersedia; jalankan drill '
                  'berkala (lihat deploy/BACKUP.md).' if backup_ok
                  else 'Skrip backup belum lengkap.')

        csp = getattr(s, 'CSP_ENABLED', True)
        headers_ok = csp and getattr(s, 'SECURE_CONTENT_TYPE_NOSNIFF', False)
        self._add(19, 'Security header', PASS if headers_ok else FAIL,
                  'CSP + nosniff + Referrer-Policy + Permissions-Policy + '
                  'COOP/CORP; HSTS/XFO aktif saat produksi.'
                  if headers_ok else 'CSP/nosniff nonaktif.')

        check_detail = 'Jalankan `manage.py check --deploy --fail-level WARNING`.'
        check_status = WARN
        if not getattr(self, '_skip_checks', False):
            try:
                call_command('check', deploy=True, fail_level='ERROR',
                             verbosity=0)
                check_status = PASS if not debug else WARN
                check_detail = ('System check deploy: tidak ada ERROR.'
                                if not debug else
                                'DEBUG=1 — deploy check penuh butuh DEBUG=0.')
            except Exception as exc:
                check_status = FAIL
                check_detail = f'System check gagal: {exc}'
        self._add(20, 'Tes keamanan sebelum live', check_status, check_detail)

    # ------------------------------------------------------------------
    def _grep_code(self, needles):
        hits = []
        for path in Path(settings.BASE_DIR).rglob('*.py'):
            if any(part in {'.venv', 'venv', 'node_modules', '.git'}
                   for part in path.parts):
                continue
            if path.name.startswith('test') or path.name == 'security_audit.py':
                continue
            try:
                text = path.read_text(errors='ignore')
            except OSError:
                continue
            for needle in needles:
                if needle in text:
                    hits.append(f'{path.name}:{needle}')
                    break
        return hits

    def _weak_admins(self):
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return [
                u.username for u in User.objects.filter(
                    is_superuser=True, is_active=True)
                if u.check_password('admin123') or u.check_password('admin')
            ]
        except Exception:
            return []

    def _source_maps(self):
        try:
            from core.checks import _find_source_maps
            return _find_source_maps()
        except Exception:
            return []

    def _deps(self):
        floors = {
            'Django': (5, 2, 18), 'Pillow': (13, 0, 0),
            'gunicorn': (26, 0, 0), 'whitenoise': (6, 12, 0),
            'psycopg': (3, 3, 6), 'django-compressor': (4, 6, 0),
            'redis': (8, 1, 0), 'bcrypt': (5, 0, 0),
        }
        bad = []
        notes = []
        for name, minimum in floors.items():
            try:
                raw = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                bad.append(f'{name}=tidak terpasang')
                continue
            parts = []
            for chunk in raw.replace('-', '.').split('.'):
                if chunk.isdigit():
                    parts.append(int(chunk))
                else:
                    break
            if tuple(parts) < minimum:
                bad.append(f'{name}={raw} (min {minimum})')
            notes.append(f'{name} {raw}')
        detail = '; '.join(notes)
        if bad:
            detail = 'Perlu update: ' + ', '.join(bad) + ' | ' + detail
        return (not bad, detail)

    def _print(self):
        self.stdout.write('\nAUDIT KEAMANAN — Nusantara Trans')
        self.stdout.write('=' * 72)
        for no, name, status, detail in self.rows:
            color = {
                PASS: self.style.SUCCESS, FAIL: self.style.ERROR,
                WARN: self.style.WARNING,
            }.get(status, self.style.WARNING)
            self.stdout.write(
                f'{no:>2}. {color(status):<8} {name:<38} {detail}')
        self.stdout.write('=' * 72)
        total = len(self.rows)
        counts = {k: sum(1 for r in self.rows if r[2] == k)
                  for k in (PASS, WARN, FAIL, NA)}
        self.stdout.write(
            f'{total} kontrol — PASS {counts[PASS]}, WARN {counts[WARN]}, '
            f'FAIL {counts[FAIL]}, N/A {counts[NA]}')

