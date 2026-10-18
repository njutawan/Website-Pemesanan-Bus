"""
Settings proyek "Nusantara Trans" — Website Pemesanan Tiket Bus & Rental Mobil.

Stack: Python (Django) + Bootstrap 5 + Nginx (lihat deploy/nginx.conf untuk produksi).
"""
import os
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# Keamanan dasar — di produksi set DJANGO_SECRET_KEY & DJANGO_DEBUG=0 via env
# =============================================================================
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-ganti-di-produksi-kunci-rahasia-ini',
)
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# Pratinjau sandbox (https://<port>-<sandbox>.e2b.app) + host produksi via env
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'DJANGO_CSRF_TRUSTED_ORIGINS', 'https://*.e2b.app'
).split(',')

# ---------------------------------------------------------------------------
# Cookie & CSRF — pratinjau sandbox tampil dalam iframe HTTPS sehingga cookie
# Default SameSite=Lax diblokir browser sebagai cookie pihak ketiga (muncul
# 403 "CSRF cookie not set" saat submit form). SameSite=None + Secure membuat
# cookie tetap diterima di konteks iframe; http://localhost tetap aman karena
# browser memperlakukannya sebagai secure context. Untuk produksi HTTPS ini
# juga konfigurasi yang benar.
# ---------------------------------------------------------------------------
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_FAILURE_VIEW = 'core.views.csrf_failure'

# Di belakang proxy Nginx/preview: hormati proto asli agar request.scheme = https
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
    # Aplikasi lokal
    'core.apps.CoreConfig',
    'booking.apps.BookingConfig',
    'rental.apps.RentalConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # Deteksi bahasa (/id/, /en/) — wajib sebelum CommonMiddleware
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Catatan: XFrameOptionsMiddleware sengaja dilepas agar pratinjau sandbox
    # bisa ditampilkan dalam iframe. Untuk produksi, aktifkan kembali:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# =============================================================================
# Database
# - Default  : SQLite (cukup untuk pengembangan tanpa Docker)
# - PostgreSQL set DJANGO_DB_ENGINE=postgres (dipakai docker-compose.yml
#   dan produksi). Lihat .env.example untuk daftar variabelnya.
# =============================================================================
if os.environ.get('DJANGO_DB_ENGINE') == 'postgres':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'nusantartrans'),
            'USER': os.environ.get('POSTGRES_USER', 'nusantar'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'nusantar'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': 60,  # koneksi persisten — mengurangi overhead koneksi
            'OPTIONS': {'sslmode': os.environ.get('POSTGRES_SSLMODE', 'prefer')},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
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
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

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
