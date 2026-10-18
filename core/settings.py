"""
Settings proyek "Nusantara Trans" — Website Pemesanan Tiket Bus & Rental Mobil.

Stack: Python (Django) + Bootstrap 5 + Nginx (lihat deploy/nginx.conf untuk produksi).
"""
import os
import sys
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name, default=False):
    """True hanya untuk nilai env yang tegas (1/true/yes/on)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name, default=''):
    """Daftar CSV dari env; buang spasi & entri kosong."""
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


# =============================================================================
# Keamanan dasar — di produksi set DJANGO_SECRET_KEY & DJANGO_DEBUG=0 via env
# =============================================================================
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-ganti-di-produksi-kunci-rahasia-ini',
)
# DEBUG default OFF (fail-closed). Pengembangan lokal WAJIB menyalakannya
# secara eksplisit: `DJANGO_DEBUG=1 python manage.py runserver`.
DEBUG = _env_bool('DJANGO_DEBUG', default=False)
# Django test runner memaksa settings.DEBUG=False; penanda ini mencegah system
# check produksi "gagal" saat menjalankan test suite.
RUNNING_TESTS = 'test' in sys.argv or 'pytest' in sys.argv

# Paksa HTTPS di level aplikasi HANYA saat env produksi di-set — jangan
# hardcode True agar preview/lokal HTTP tetap berfungsi. Redirect utama
# HTTP->HTTPS ada di Nginx. Didefinisikan lebih awal karena memengaruhi
# kebijakan cookie & CSP di bawah.
SECURE_SSL_REDIRECT = _env_bool('DJANGO_SSL_REDIRECT', default=False)

# ---------------------------------------------------------------------------
# ALLOWED_HOSTS
# - Debug/preview: '*' agar host dinamis sandbox (https://<port>-<id>.e2b.app)
#   bisa diakses.
# - Produksi: WAJIB diisi eksplisit. Nilai kosong membuat Django menolak
#   semua Host header (fail-closed); system check core.E003 memandu deploy.
# ---------------------------------------------------------------------------
_allowed_hosts = _env_list('DJANGO_ALLOWED_HOSTS')
ALLOWED_HOSTS = _allowed_hosts or (['*'] if DEBUG else [])
USE_X_FORWARDED_HOST = _env_bool('DJANGO_USE_X_FORWARDED_HOST', default=False)

# Pratinjau sandbox (https://<port>-<sandbox>.e2b.app) + host produksi via env.
# Wildcard e2b.app hanya default saat DEBUG — produksi wajib domain sendiri;
# system check core.E013 menolak wildcard preview di produksi.
CSRF_TRUSTED_ORIGINS = _env_list(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'https://*.e2b.app' if DEBUG else '',
)

# ---------------------------------------------------------------------------
# Cookie & CSRF
# - Produksi (SECURE_SSL_REDIRECT=1): SameSite=Lax — cookie tidak ikut
#   dikirim pada request lintas-situs, pertahanan berlapis di atas CSRF token.
# - Preview sandbox: halaman tampil di dalam iframe HTTPS. Browser memblokir
#   cookie Lax sebagai pihak ketiga; SameSite=None + Secure diperlukan agar
#   form tetap bisa submit. Nilai ini HANYA default di mode non-produksi.
# - Bisa dipaksa lewat DJANGO_COOKIE_SAMESITE (Lax/Strict/None).
# ---------------------------------------------------------------------------
_cookie_samesite = os.environ.get(
    'DJANGO_COOKIE_SAMESITE',
    'Lax' if SECURE_SSL_REDIRECT else 'None',
).strip().title()
if _cookie_samesite not in {'Lax', 'Strict', 'None'}:
    _cookie_samesite = 'Lax'
CSRF_COOKIE_SAMESITE = _cookie_samesite
SESSION_COOKIE_SAMESITE = _cookie_samesite
CSRF_COOKIE_SECURE = _env_bool('DJANGO_COOKIE_SECURE', default=not DEBUG)
SESSION_COOKIE_SECURE = _env_bool('DJANGO_COOKIE_SECURE', default=not DEBUG)
SESSION_COOKIE_HTTPONLY = True
# Admin Django memakai JavaScript untuk membaca cookie csrftoken.
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_AGE = int(os.environ.get('DJANGO_SESSION_AGE', 8 * 60 * 60))
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'

# Di belakang proxy Nginx/preview: hormati proto asli agar request.scheme = https.
# Hanya aktif bila header memang di-set oleh proxy tepercaya (Nginx lokal).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# IP proxy yang boleh dipercaya untuk X-Forwarded-For (rate limit & allowlist
# admin). Di produksi Gunicorn hanya listen 127.0.0.1 sehingga nilai default
# aman. JANGAN tambahkan IP publik ke sini.
TRUSTED_PROXY_IPS = _env_list('DJANGO_TRUSTED_PROXY_IPS', '127.0.0.1,::1')

# =============================================================================
# CORS — TIDAK ada header Access-Control-Allow-Origin secara default.
# Situs ini tidak mengekspos API lintas-origin; browser memblokir pembacaan
# respons dari origin lain. Bila suatu saat menambah API, daftarkan origin
# eksplisit (tidak boleh '*') di env. Lihat core.middleware.CorsMiddleware.
# =============================================================================
CORS_ALLOWED_ORIGINS = _env_list('DJANGO_CORS_ALLOWED_ORIGINS')
# Credentials (cookie) TIDAK diizinkan lintas-origin secara default.
CORS_ALLOW_CREDENTIALS = False

# =============================================================================
# Keamanan password: bcrypt (algoritma hashing anti-brute-force, faktor biaya
# bisa dinaikkan seiring waktu). BCryptSHA256 = pre-hash SHA-256 agar password
# >72 byte tidak terpotong. Hasher lama dipertahankan sebagai fallback agar
# hash PBKDF2 bawaan masih bisa login & OTOMATIS ter-upgrade ke bcrypt
# pada login berikutnya.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]

# =============================================================================
# Standardisasi URL & kanonik (SEO)
# =============================================================================
# /bus -> 301 /bus/ (CommonMiddleware). Semua pola URL memakai trailing slash.
APPEND_SLASH = True
# Standar domain utama: TANPA www. www dialihkan 301 di level Nginx
# (deploy/nginx.conf) — lebih hemat satu hop aplikasi.
PREPEND_WWW = False

# Header keamanan yang aman di semua mode (tidak mengganggu iframe pratinjau)
SECURE_CONTENT_TYPE_NOSNIFF = True   # X-Content-Type-Options: nosniff
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Header produksi penuh (ikuti DJANGO_SSL_REDIRECT=1): HSTS + anti-clickjacking.
# X-Frame-Options: DENY sengaja env-gated — bila aktif di sandbox, pratinjau
# berbasis iframe langsung rusak; di produksi dilarang diframe siapa pun.
# CSP (core.middleware.SecurityHeadersMiddleware) memakai frame-ancestors
# 'none' di produksi dan TIDAK membatasi frame di mode preview.
if SECURE_SSL_REDIRECT:
    SECURE_HSTS_SECONDS = 31_536_000          # HSTS 1 tahun (31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'
else:
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    X_FRAME_OPTIONS = 'SAMEORIGIN'  # tidak dipakai (middleware tak terpasang)

# =============================================================================
# Content-Security-Policy & header tambahan (core.middleware.SecurityHeaders)
# =============================================================================
CSP_ENABLED = _env_bool('DJANGO_CSP_ENABLED', default=True)
CSP_REPORT_ONLY = _env_bool('DJANGO_CSP_REPORT_ONLY', default=False)
# Origin CDN yang memang dipakai halaman publik (Font Awesome & Google Fonts).
CSP_STYLE_ORIGINS = (
    'https://cdnjs.cloudflare.com',
    'https://fonts.googleapis.com',
)
CSP_FONT_ORIGINS = (
    'https://cdnjs.cloudflare.com',
    'https://fonts.gstatic.com',
)
# Chart.js & aset admin disajikan lokal (static/vendor/) — tidak perlu CDN.

# =============================================================================
# Rate limit (core.middleware.RateLimitMiddleware)
# - Disimpan di cache (Redis di produksi; LocMem saat dev). Tanpa Redis,
#   batas berlaku per-proses Gunicorn — aktifkan REDIS_URL di produksi.
# - Setiap aturan = jumlah maksimum request per jendela (detik) per IP.
# =============================================================================
RATELIMIT_ENABLED = _env_bool('DJANGO_RATELIMIT_ENABLED', default=True)
RATELIMIT_RULES = {
    'global': {'limit': 600, 'window': 60},
    'unsafe': {'limit': 60, 'window': 60},
    'admin_login': {'limit': 8, 'window': 300},
    'admin_login_user': {'limit': 5, 'window': 300},
    'booking_create': {'limit': 15, 'window': 3600},
    'proof_upload': {'limit': 15, 'window': 3600},
    'lookup': {'limit': 120, 'window': 600},
    # Pembuatan link bayar & sinkronisasi status (panggilan keluar ke Pakasir)
    'payment_create': {'limit': 10, 'window': 3600},
    'payment_sync': {'limit': 30, 'window': 600},
    'payment_webhook': {'limit': 120, 'window': 60},
}
RATELIMIT_EXEMPT_PREFIXES = ('/static/',)

# =============================================================================
# Proteksi panel admin
# - ADMIN_ALLOWED_IPS kosong = semua IP boleh membuka /admin/ (tetap wajib
#   login staf). Isi CIDR/IP di produksi untuk pertahanan berlapis, mis.
#   "10.0.0.0/8,203.0.113.10".
# =============================================================================
ADMIN_ALLOWED_IPS = _env_list('DJANGO_ADMIN_ALLOWED_IPS')

# =============================================================================
# Batas input & unggahan (anti-DoS / validasi)
# =============================================================================
MAX_TRAVEL_DATE_DAYS = 365          # tanggal perjalanan maksimal 1 tahun ke depan
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
DATA_UPLOAD_MAX_NUMBER_FILES = 5          # hanya butuh 1 bukti bayar per request
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024      # 6 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024      # 6 MB
MAX_UPLOAD_SIZE = 6 * 1024 * 1024                  # batas keras per berkas
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
# Hanya format gambar yang benar-benar dipakai (cegah HTML/SVG tersimpan).
MEDIA_ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')
# Batas dekompresi Pillow (anti "decompression bomb").
IMAGE_MAX_PIXELS = 25_000_000
AUDIT_RETENTION_DAYS = int(os.environ.get('DJANGO_AUDIT_RETENTION_DAYS', 180))

# =============================================================================
# Pembayaran
# - Default: transfer manual / QRIS statis, diverifikasi admin.
# - `PAYMENT_GATEWAY_PROVIDER=pakasir` mengaktifkan QRIS online lewat
#   Pakasir API v2 (hosted payment link). Kredensial HANYA dari env:
#     PAKASIR_SLUG, PAKASIR_API_KEY, PAKASIR_WEBHOOK_SECRET
# - Webhook Pakasir memakai header `X-Secret` (bukan HMAC bertimestamp).
#   Endpoint tetap memverifikasi ulang status ke API Pakasir sebelum
#   mengubah status booking (lihat core/pakasir.py & payment_service.py).
# - Base URL dikunci ke host resmi (anti-SSRF) dan tidak bisa diubah env.
# =============================================================================
PAYMENT_GATEWAY_PROVIDER = os.environ.get('PAYMENT_GATEWAY_PROVIDER', '').strip().lower()
PAYMENT_WEBHOOK_SECRET = os.environ.get('PAYMENT_WEBHOOK_SECRET', '')
PAYMENT_WEBHOOK_TOLERANCE_SECONDS = int(
    os.environ.get('PAYMENT_WEBHOOK_TOLERANCE_SECONDS', 300))

PAKASIR_BASE_URL = 'https://app.pakasir.com'
PAKASIR_SLUG = os.environ.get('PAKASIR_SLUG', '').strip()
PAKASIR_API_KEY = os.environ.get('PAKASIR_API_KEY', '').strip()
# Fallback ke nama lama agar deployment lama tidak langsung mati.
PAKASIR_WEBHOOK_SECRET = (
    os.environ.get('PAKASIR_WEBHOOK_SECRET', '').strip()
    or PAYMENT_WEBHOOK_SECRET.strip()
)
# Mode sandbox ditandai eksplisit; respons API juga membawa `is_sandbox`
# dan nilainya WAJIB cocok (mencegah kunci sandbox dipakai di produksi).
PAKASIR_SANDBOX = _env_bool('PAKASIR_SANDBOX', default=False)
PAKASIR_TIMEOUT_SECONDS = int(os.environ.get('PAKASIR_TIMEOUT_SECONDS', 8))
PAKASIR_MIN_AMOUNT = 500                 # minimum QRIS/payment link Pakasir
PAKASIR_MAX_AMOUNT = 50_000_000
# Metode yang dipakai: payment_link + `qris_only=1` (pelanggan hanya melihat QRIS).
PAKASIR_METHOD = 'payment_link'
PAYMENT_METHOD_PAKASIR = 'pakasir_qris'


# =============================================================================
# Aplikasi
# =============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
    # Minifikasi & penggabungan CSS/JS (Core Web Vitals)
    'compressor',
    # Manajemen 301 redirect (SEO) — syarat: django.contrib.sites
    'django.contrib.sites',
    'django.contrib.redirects',
    # Aplikasi lokal
    'core.apps.CoreConfig',
    'booking.apps.BookingConfig',
    'rental.apps.RentalConfig',
]

# ID baris situs di tabel django_site (dipakai django.contrib.redirects & sitemaps)
SITE_ID = 1

MIDDLEWARE = [
    # Buang X-Forwarded-Proto palsu dari klien non-proxy SEBELUM SecurityMiddleware.
    'core.middleware.TrustedProxyHeadersMiddleware',
    # Kompresi payload HTML/CSS/JSON (paling atas agar semua respons terkompres)
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # Header keamanan (CSP + hash inline script, Permissions-Policy, CORP, dll.)
    'core.middleware.SecurityHeadersMiddleware',
    # CORS eksplisit: tidak ada Access-Control-Allow-Origin kecuali diizinkan
    'core.middleware.CorsMiddleware',
    # Pembatas laju per IP (POST, login admin, cek booking, upload bukti)
    'core.middleware.RateLimitMiddleware',
    # Allowlist IP admin opsional (DJANGO_ADMIN_ALLOWED_IPS) — deny 404
    'core.middleware.AdminIPAllowlistMiddleware',
    # Source map (.map) tidak pernah disajikan
    'core.middleware.BlockSourceMapsMiddleware',
    # /BUS/ -> 301 /bus/ (path kapital tidak resmi; kode booking dipertahankan)
    'core.middleware.LowercasePathMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # Deteksi bahasa (/id/, /en/) — wajib sebelum CommonMiddleware
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Manajemen redirect 301 dari database (django.contrib.redirects).
    # Harus PALING BAWAH: hanya bertindak saat request tidak ditangani apa pun
    # (404) — URL lama yang berpindah tidak lagi menghasilkan broken link.
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    # Bot: X-Robots-Tag utk admin, media, & hasil pencarian dinamis
    'core.middleware.XRobotsTagMiddleware',
]

if SECURE_SSL_REDIRECT:
    MIDDLEWARE.append('django.middleware.clickjacking.XFrameOptionsMiddleware')

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Kustom
                'django.template.context_processors.media',
                'core.context_processors.site_settings',
                'core.context_processors.language_alternates',
                'core.context_processors.seo',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# =============================================================================
# Database: PostgreSQL murni (tidak ada fallback SQLite)
# - Docker Compose menyediakan service db (postgres:16-alpine) + REDIS_URL.
# - Tanpa Docker: isi POSTGRES_* di .env (lihat .env.example).
# - Produksi: sslmode=require & jangan expose port db.
# =============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'nusantartrans'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        # TIDAK ada password default. Docker Compose & produksi WAJIB mengisi
        # POSTGRES_PASSWORD; dev lokal boleh kosong bila server memakai trust
        # auth (peer/socket). System check core.E004 memblokir produksi kosong.
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 60,  # koneksi persisten — mengurangi overhead koneksi
        'OPTIONS': {'sslmode': os.environ.get('POSTGRES_SSLMODE', 'prefer')},
    }
}

# =============================================================================
# Email (dipakai reset password admin & notifikasi operasional)
# - Default pengembangan: console (email tercetak di terminal, bukan dikirim).
# - Produksi: SMTP via env; system check core.W021 memperingatkan bila masih
#   console, karena reset password tidak akan sampai ke admin.
# =============================================================================
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_PASSWORD', '')
EMAIL_USE_TLS = _env_bool('DJANGO_EMAIL_TLS', default=True)
EMAIL_TIMEOUT = int(os.environ.get('DJANGO_EMAIL_TIMEOUT', 10))
DEFAULT_FROM_EMAIL = os.environ.get(
    'DJANGO_DEFAULT_FROM_EMAIL', 'Nusantara Trans <no-reply@nusantartrans.example>')
SERVER_EMAIL = os.environ.get(
    'DJANGO_SERVER_EMAIL', 'server@nusantartrans.example')
# Tautan reset password kedaluwarsa cepat (default Django 3 hari terlalu lama).
PASSWORD_RESET_TIMEOUT = int(os.environ.get('DJANGO_PASSWORD_RESET_TIMEOUT', 3600))

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# Internasionalisasi (ID default di "/", EN di "/en/")
# =============================================================================
LANGUAGE_CODE = 'id'
LANGUAGES = [
    ('id', _('Bahasa Indonesia')),
    ('en', _('English')),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

# =============================================================================
# Statik & media
# =============================================================================
STATIC_URL = 'static/'
COMPRESS_OUTPUT_DIR = 'cache'  # huruf kecil — selaras LowercasePathMiddleware
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =============================================================================
# django-compressor: minifikasi + gabung CSS/JS menjadi satu berkas
# - DEBUG=1 (pengembangan): nonaktif → sumber asli, mudah di-debug
# - DEBUG=0 (produksi): aktif + mode offline → jalankan
#   `python manage.py compress` SEBELUM collectstatic (wajib!)
# =============================================================================
COMPRESS_ENABLED = os.environ.get('DJANGO_COMPRESS_ENABLED', '1' if not DEBUG else '0') == '1'
COMPRESS_OFFLINE = os.environ.get('DJANGO_COMPRESS_OFFLINE', '1' if not DEBUG else '0') == '1'

# Output compressor dibuat + pra-gzip (bekerja rapi dengan WhiteNoise & nginx gzip_static).
COMPRESS_STORAGE = 'compressor.storage.GzipCompressorFileStorage'

# =============================================================================
# Cache
# - REDIS_URL terisi  → Redis (produksi / docker-compose, service `redis`)
# - tanpa REDIS_URL  → LocMemCache (cukup utk dev single-process)
# Dipakai: cache queryset beranda/rute, template fragment, sitemap.
# =============================================================================
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': os.environ['REDIS_URL'],
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'nusantara-trans',
        }
    }
CACHE_TTL_DEFAULT = 600  # detik

# =============================================================================
# Logging — TIDAK pernah menulis password/token/cookie/DSN ke log.
# Filter RedactSecretsFilter berlaku untuk semua handler console, sehingga
# pesan dari Django, Gunicorn, maupun kode aplikasi disaring berlapis.
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'redact_secrets': {'()': 'core.logging.RedactSecretsFilter'},
    },
    'formatters': {
        'standard': {
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['redact_secrets'],
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        # Access log 4xx tidak perlu (bisa memuat kode booking di URL);
        # 5xx tetap dicatat untuk investigasi.
        'django.request': {
            'handlers': ['console'], 'level': 'ERROR', 'propagate': False,
        },
        'django.security': {
            'handlers': ['console'], 'level': 'WARNING', 'propagate': False,
        },
        # Audit terstruktur (tanpa PII/rahasia) — lihat core.audit.log_event.
        'audit': {
            'handlers': ['console'], 'level': 'INFO', 'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# Static files: WhiteNoise — kompresi gzip + header cache panjang untuk produksi
# (jalankan `python manage.py collectstatic` saat deploy; pratinjau DEBUG tak
# terpengaruh karena staticfiles menyajikan langsung dari STATICFILES_DIRS)
# =============================================================================
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# =============================================================================
# Konfigurasi bisnis (di-expose ke template via core.context_processors)
# =============================================================================
SITE_NAME = 'Nusantara Trans'
SITE_TAGLINE = 'Tiket Bus & Rental Mobil Terpercaya'

# Kontak
WHATSAPP_NUMBER = '6281234567890'  # format internasional tanpa "+"
CONTACT_EMAIL = 'halo@nusantartrans.example'
CONTACT_PHONE = '+62 812-3456-7890'
CONTACT_ADDRESS = 'Jl. Kalimantan No. 27, Sumbersari, Jember, Jawa Timur 68121'
CONTACT_HOURS = 'Setiap hari, 07.00–21.00 WIB'

# Metode pembayaran (transfer manual / QRIS statis, diverifikasi admin)
PAYMENT_METHODS = [
    ('bca', 'Transfer Bank BCA'),
    ('mandiri', 'Transfer Bank Mandiri'),
    ('qris', 'QRIS (semua e-wallet & m-banking)'),
]
PAYMENT_DETAILS = {
    'bca': {
        'label': 'Transfer Bank BCA',
        'account': '1234567890',
        'holder': 'PT Nusantara Trans Jaya',
        'icon': 'fa-building-columns',
    },
    'mandiri': {
        'label': 'Transfer Bank Mandiri',
        'account': '9876543210',
        'holder': 'PT Nusantara Trans Jaya',
        'icon': 'fa-building-columns',
    },
    'qris': {
        'label': 'QRIS — scan dengan GoPay/OVO/DANA/m-banking apa pun',
        'account': '',
        'holder': 'PT Nusantara Trans Jaya',
        'icon': 'fa-qrcode',
    },
}
# Gambarnya: static/img/qris-placeholder.png (ganti dengan QRIS asli Anda)

# Batas waktu pembayaran booking yang belum dibayar (jam) → otomatis EXPIRED
PAYMENT_TIMEOUT_HOURS = 2
MAX_SEATS_PER_BOOKING = 6

# =====================================================================
# CATATAN PRODUKSI:
# 1. python manage.py migrate && python manage.py compile_i18n
# 2. python manage.py collectstatic --noinput
# 3. gunicorn core.wsgi:application --bind 127.0.0.1:8001
# 4. Pasang deploy/nginx.conf sebagai reverse proxy (static/media disajikan Nginx)
# =====================================================================
