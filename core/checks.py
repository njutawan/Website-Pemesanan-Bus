"""System check: gagal cepat bila urutan deploy compress → collectstatic terbalik.

Saat COMPRESS_OFFLINE aktif (DEBUG=0), {% compress %} butuh manifest hasil
`manage.py compress`. Bila manifest tidak ada, setiap halaman akan 500 saat
produksi. Check ini menampilkan Error di `manage.py check` SEBELUM deploy.
Catatan: saat DEBUG=0 compressor membaca sumber dari STATIC_ROOT — urutan
yang benar adalah `collectstatic` DULULU, baru `compress --force`.
"""
import os

from django.conf import settings
from django.core import checks


@checks.register()
def compress_offline_manifest(app_configs, **kwargs):
    if (settings.DEBUG or getattr(settings, 'RUNNING_TESTS', False)
            or not getattr(settings, 'COMPRESS_OFFLINE', False)):
        return []
    try:
        from compressor.storage import default_offline_manifest_storage
        ada = default_offline_manifest_storage.exists(settings.COMPRESS_OFFLINE_MANIFEST)
    except Exception:
        return []  # compressor tidak terpasang — biarkan modul lain yang mengeluh
    if not ada:
        return [checks.Error(
            'Manifest django-compressor offline tidak ditemukan di STATIC_ROOT.',
            hint='Saat DEBUG=0 compressor membaca sumber dari STATIC_ROOT. Jalankan '
                 '"python manage.py collectstatic --noinput" lalu '
                 '"DJANGO_DEBUG=0 python manage.py compress --force".',
            id='core.E001',
        )]
    return []


# =============================================================================
# System check keamanan produksi
# - Saat DEBUG=1 hanya warning (agar `manage.py check` lokal tetap nyaman).
# - Saat DEBUG=0 pelanggaran kritis menjadi Error → deploy berhenti.
# =============================================================================
_WEAK_PASSWORDS = {
    'admin', 'admin123', 'password', 'password123', '12345678', '123456789',
    'qwerty123', 'nusantar', 'changeme', 'secret123', 'letmein123',
}
_DEFAULT_SECRET = 'django-insecure-ganti-di-produksi-kunci-rahasia-ini'


def _level(debug, error=True):
    return checks.WARNING if debug else (checks.ERROR if error else checks.WARNING)


@checks.register()
def production_security(app_configs, **kwargs):
    debug = bool(settings.DEBUG) or bool(
        getattr(settings, 'RUNNING_TESTS', False))
    issues = []

    if settings.SECRET_KEY == _DEFAULT_SECRET or len(settings.SECRET_KEY) < 50:
        issues.append(checks.Error(
            'SECRET_KEY masih default/terlalu pendek.',
            hint='Set DJANGO_SECRET_KEY acak ≥50 karakter (mis. openssl rand -base64 48).',
            id='core.E002',
        ) if not debug else checks.Warning(
            'SECRET_KEY default hanya untuk pengembangan.',
            hint='Set DJANGO_SECRET_KEY sebelum produksi.', id='core.W002'))

    hosts = list(getattr(settings, 'ALLOWED_HOSTS', []))
    if not hosts or '*' in hosts:
        issues.append(checks.Error(
            'ALLOWED_HOSTS kosong atau berisi "*".',
            hint='Set DJANGO_ALLOWED_HOSTS=domain-anda.example,www.domain-anda.example.',
            id='core.E003',
        ) if not debug else checks.Warning(
            'ALLOWED_HOSTS="*" tidak aman untuk produksi.',
            hint='Isi DJANGO_ALLOWED_HOSTS dengan domain eksplisit.', id='core.W003'))

    db_password = str(settings.DATABASES.get('default', {}).get('PASSWORD') or '')
    if not db_password or db_password.lower() in _WEAK_PASSWORDS:
        issues.append(checks.Error(
            'Password PostgreSQL kosong/lemah.',
            hint='Set POSTGRES_PASSWORD acak (jangan "nusantar"/"postgres").',
            id='core.E004',
        ) if not debug else checks.Warning(
            'Password database kosong/lemah (boleh untuk trust auth lokal).',
            hint='Set POSTGRES_PASSWORD untuk produksi.', id='core.W004'))

    if settings.CSRF_COOKIE_SAMESITE == 'None' and not debug:
        issues.append(checks.Error(
            'CSRF cookie SameSite=None di produksi.',
            hint='Set DJANGO_COOKIE_SAMESITE=Lax (atau Strict).',
            id='core.E005',
        ))
    if not settings.CSRF_COOKIE_SECURE or not settings.SESSION_COOKIE_SECURE:
        issues.append(checks.Error(
            'Cookie CSRF/sesi tidak Secure.',
            hint='Aktifkan HTTPS + DJANGO_COOKIE_SECURE=1.',
            id='core.E006',
        ) if not debug else checks.Warning(
            'Cookie belum Secure (normal untuk HTTP lokal).',
            hint='Aktifkan HTTPS + cookie Secure di produksi.', id='core.W006'))

    if any(origin.strip() == '*' for origin in getattr(settings, 'CORS_ALLOWED_ORIGINS', [])):
        issues.append(checks.Error(
            'CORS_ALLOWED_ORIGINS memuat "*" (tidak diizinkan).',
            hint='Daftarkan origin eksplisit, mis. https://app.example.',
            id='core.E007',
        ))

    if not debug:
        bad_origins = [
            o for o in getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
            if '*' in o or 'e2b.app' in o
        ]
        if bad_origins or not getattr(settings, 'CSRF_TRUSTED_ORIGINS', []):
            issues.append(checks.Error(
                'CSRF_TRUSTED_ORIGINS masih wildcard preview/kosong di produksi.',
                hint='Set DJANGO_CSRF_TRUSTED_ORIGINS=https://domain-anda.example.',
                id='core.E008',
            ))

    if not getattr(settings, 'RATELIMIT_ENABLED', True) and not debug:
        issues.append(checks.Error(
            'Rate limit dinonaktifkan di produksi.', id='core.E009',
            hint='Set DJANGO_RATELIMIT_ENABLED=1.'))
    if not getattr(settings, 'CSP_ENABLED', True) and not debug:
        issues.append(checks.Error(
            'Content-Security-Policy dinonaktifkan di produksi.',
            id='core.E010', hint='Set DJANGO_CSP_ENABLED=1.'))

    if not debug:
        if not getattr(settings, 'ADMIN_ALLOWED_IPS', []):
            issues.append(checks.Warning(
                'ADMIN_ALLOWED_IPS kosong — panel admin terbuka untuk semua IP.',
                hint='Sangat disarankan membatasi /admin/ ke VPN/IP kantor.',
                id='core.W011'))
        if not settings.SECURE_SSL_REDIRECT:
            issues.append(checks.Warning(
                'DJANGO_SSL_REDIRECT=0 — pastikan Nginx memaksa HTTPS.',
                id='core.W012'))
        if not os.environ.get('REDIS_URL'):
            issues.append(checks.Warning(
                'REDIS_URL kosong — rate limit hanya per-proses Gunicorn.',
                hint='Gunakan Redis agar batas berlaku lintas worker.',
                id='core.W013'))
        sslmode = str(settings.DATABASES.get('default', {}).get(
            'OPTIONS', {}).get('sslmode', '')).lower()
        if sslmode in {'disable', 'allow', 'prefer', ''}:
            issues.append(checks.Warning(
                'Koneksi PostgreSQL belum memakai TLS ketat.',
                hint='Set POSTGRES_SSLMODE=require (atau verify-full).',
                id='core.W014'))
        if getattr(settings, 'PAYMENT_GATEWAY_PROVIDER', ''):
            if not getattr(settings, 'PAYMENT_WEBHOOK_SECRET', ''):
                issues.append(checks.Error(
                    'Payment gateway aktif tanpa PAYMENT_WEBHOOK_SECRET.',
                    hint='Webhook wajib diverifikasi HMAC; isi secret acak.',
                    id='core.E015'))
        if settings.SECURE_HSTS_SECONDS < 31_536_000:
            issues.append(checks.Warning(
                'HSTS kurang dari 1 tahun.',
                hint='Set DJANGO_SSL_REDIRECT=1 (HSTS otomatis 31536000).',
                id='core.W016'))
        if settings.X_FRAME_OPTIONS != 'DENY':
            issues.append(checks.Warning(
                'X-Frame-Options bukan DENY di produksi.',
                hint='Aktifkan DJANGO_SSL_REDIRECT=1.',
                id='core.W017'))

    weak_env = os.environ.get('DJANGO_ADMIN_PASSWORD', '')
    if weak_env and (len(weak_env) < 12 or weak_env.lower() in _WEAK_PASSWORDS):
        issues.append(checks.Error(
            'DJANGO_ADMIN_PASSWORD terlalu lemah.',
            hint='Gunakan ≥12 karakter acak atau biarkan kosong agar seed '
                 'membuat password acak (mode DEBUG).',
            id='core.E018',
        ))

    # Source map: jangan pernah ikut ter-deploy.
    map_files = _find_source_maps()
    if map_files:
        issues.append(checks.Warning(
            'Berkas source map ditemukan di static: %s' % ', '.join(map_files[:5]),
            hint='Hapus *.map dari static/vendor (source map tidak untuk publik).',
            id='core.W019'))

    # .env di dalam proyek: jangan pernah bisa dibaca pengguna lain.
    env_file = os.path.join(str(settings.BASE_DIR), '.env')
    if os.path.exists(env_file):
        try:
            mode = os.stat(env_file).st_mode & 0o777
        except OSError:
            mode = 0
        if mode & 0o077:
            issues.append(checks.Warning(
                f'Berkas .env dapat dibaca pengguna/grup lain (mode {mode:o}).',
                hint='Jalankan: chmod 600 .env (atau simpan variabel di '
                     '/etc/nusantartrans/app.env dengan mode 600).',
                id='core.W020'))

    if not debug:
        backend = str(getattr(settings, 'EMAIL_BACKEND', ''))
        if 'console' in backend or 'locmem' in backend or 'dummy' in backend:
            issues.append(checks.Warning(
                'EMAIL_BACKEND pengembangan (console/locmem/dummy) di produksi.',
                hint='Reset password admin tidak akan terkirim. Set '
                     'DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend '
                     'dan variabel DJANGO_EMAIL_* .',
                id='core.W021'))
        if int(getattr(settings, 'PASSWORD_RESET_TIMEOUT', 259200)) > 24 * 3600:
            issues.append(checks.Warning(
                'PASSWORD_RESET_TIMEOUT lebih dari 24 jam.',
                hint='Set DJANGO_PASSWORD_RESET_TIMEOUT=3600.',
                id='core.W022'))
    return issues


def _find_source_maps():
    from pathlib import Path
    roots = []
    for entry in getattr(settings, 'STATICFILES_DIRS', []):
        roots.append(Path(entry[1] if isinstance(entry, (list, tuple)) else entry))
    static_root = getattr(settings, 'STATIC_ROOT', None)
    if static_root:
        roots.append(Path(static_root))
    found = []
    for root in roots:
        try:
            if not root.exists():
                continue
            for path in root.rglob('*.map'):
                if path.is_file():
                    found.append(str(path))
                if len(found) >= 10:
                    return found
        except OSError:
            continue
    return found
