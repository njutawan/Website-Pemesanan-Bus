# Changelog

Semua perubahan penting pada proyek **Nusantara Trans — Website Pemesanan Tiket Bus & Rental Mobil** dicatat di berkas ini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/id/1.1.0/) dan proyek ini menganut [Semantic Versioning](https://semver.org/lang/id/).

---

## [1.1.0] — 2026-10-19

Rilis minor pertama setelah v1.0.0. Fokus pada **stabilitas alur booking**, **hardening keamanan 20 kontrol**, **pembayaran QRIS online via Pakasir**, serta **upgrade dependensi ke Django 6.1**.

### Ditambahkan
- **Pembayaran QRIS online via Pakasir API v2** — modul `core/pakasir.py`, `core/payment_service.py`, `core/payment_views.py` dan model `PaymentTransaction` (`core/migrations/0005`). Panel “QRIS Online” di halaman detail booking bus & rental, endpoint `/pembayaran/{bus|rental}/<kode>/` + webhook terverifikasi `X-Secret` (constant-time) + sinkronisasi status dengan cooldown 4 detik. Fallback transfer manual/QRIS statis tetap tersedia.
- **Hardening keamanan 20 kontrol + audit 19 titik** — `core/middleware.py` (RateLimit, CORS allowlist ketat, CSP hash-based, HSTS, XFO DENY, COOP/CORP), `core/audit.py` + `AuditLog` (read-only superuser, redaksi PII), `core/validators.py`, `core/checks.py` (E019–E022/W023/W024 untuk Pakasir), `core/logging.py` (redaksi secret di log & traceback), `core/signals.py`, perintah `security_audit` (20 kontrol) & `security_review` (19 kontrol hardening), `purge_audit_logs`.
- **Panel admin & dasbor operasional** — kartu statistik, grafik Chart.js 14 hari, antrean verifikasi pembayaran 1-klik, okupansi keberangkatan hari ini, ekspor CSV (`;` + BOM), filter bukti pembayaran, branding navy/oranye, optimasi `list_select_related` & `autocomplete_fields`.
- **Backup & restore teruji** — `deploy/backup.sh`, `deploy/restore.sh`, `deploy/verify_backup.sh` (drill ke DB sementara + checksum, anti zip-slip), `deploy/BACKUP.md`, `deploy/db_setup.sql` (role `nt_app`/`nt_owner` non-superuser), `deploy/docker-compose.prod.yml` tanpa port DB publik, `deploy/nginx.conf` hardening, `deploy/scan_secrets.sh`.
- **Manajemen 301 redirect** (`django.contrib.redirects`) + `RedirectFallbackMiddleware` (paling bawah) — kelola via admin; seed `/tiket/`→`/bus/` dll.
- **SEO topic cluster / silo** — hub `/bus/rute/`, pillar per kota `/bus/rute/dari/<kota>/`, upward/downward/lateral linking, `SeoKeyword` + filter `auto_internal_link`, breadcrumb & JSON-LD 5 tingkat, URL hierarkis `/bus/rute/dari/jember/surabaya/` + 301 legacy flat.
- **Performa & media modern** — `django-compressor`, `WhiteNoise`, `GZipMiddleware`, konversi WebP otomatis (`convert_media_webp` + `seed_data`), `LowercasePathMiddleware`, `APPEND_SLASH`, `PREPEND_WWW=False`, `PrivateMediaView` dengan Nginx proxy untuk bukti pembayaran.
- **Perintah & utilitas baru** — `expire_stale_bookings`, `expire_stale_rental_bookings`, `compile_i18n` (polib), `convert_media_webp`, `purge_audit_logs`.
- **Dwibahasa ID/EN** — URL terpisah + hreflang, `locale/en` & `locale/id` diperbarui, `core/translations.py`.
- **Infrastruktur** — `Makefile` (dev/migrate/seed/check/test/audit/review/secrets/deploy-check/backup-verify), `.dockerignore`, `.env.example` lengkap, `SECURITY.md` sebagai bukti audit.
- **Versi aplikasi** — `VERSION` + `CHANGELOG.md` + `core/__init__.py:__version__` + `settings.APP_VERSION` + tampil di footer.

### Diperbaiki
- Alur booking kursi → penumpang (form GET, pertahankan `date` & `passengers` saat kursi diperebutkan, `MAX_SEATS_PER_BOOKING` dari settings, `?baru=1` untuk banner sukses).
- Logika rental — cegah tumpang tindih sewa kendaraan yang sama (`select_for_update`), status `EXPIRED` + command kadaluarsa periodik, pakai `PAYMENT_TIMEOUT_HOURS` dari settings.
- Keamanan media — bukti pembayaran tidak lagi publik; hanya staf / pemilik sesi; `payment_proofs/` & `rental_proofs/` diproxy Django via Nginx.
- Performa pencarian — hapus N+1 dengan anotasi & agregasi, cache `PageMeta` di context processor, `cache_page` halaman semi-statis, `convert_media_webp` di akhir `seed_data`.
- UI/UX — animasi `.needs-shake`, countdown ISO 8601 dengan offset timezone (benar di luar WIB), `async-css.js` + defer bundles, `rental-form.js` ikut di-compress.
- CI — ganti `pytest` dengan `python manage.py test` + PostgreSQL service, upgrade ke Python 3.12 (syarat Django 6.1).

### Keamanan
- `PASSWORD_HASHERS` = `BCryptSHA256PasswordHasher` (cost 12) + auto-upgrade dari PBKDF2.
- Rate limit per IP (429 + `Retry-After`), CORS ketat tanpa wildcard, CSRF dengan `enforce_csrf_checks` teruji.
- Header: `SECURE_CONTENT_TYPE_NOSNIFF`, `Referrer-Policy`, `HSTS 31536000` & `X-Frame-Options: DENY` saat produksi (`DJANGO_SSL_REDIRECT=1`), `X-Robots-Tag` untuk `/admin/`, `/media/` & halaman berparameter.
- `ADMIN_ALLOWED_IPS` (default `127.0.0.1/32,::1/128,192.168.0.0/16`), rate limit login admin, tanpa password default di produksi.
- `TRUSTED_PROXY_IPS` untuk `X-Forwarded-For/Proto`, blokir source map, allowlist ekstensi media + CSP sandbox.

### Diubah — Dependensi
- **Django `5.2.18` → `6.1.2`** (`>=6.1.2,<6.2`) — perbaikan CVE-2026-15830, CVE-2026-87975, CVE-2026-87890, CVE-2026-84429, CVE-2026-77050.
- **Python `3.11-slim` → `3.14-slim`** (Dockerfile) & CI `3.12` (minimum Django 6.1).
- `actions/checkout 4 → 7`, `actions/setup-python 5 → 7`, `flake8 7.3.0 → 7.4.1`, `pip-audit 2.9.0 → 2.10.1`, `Pillow>=13.0.0`, `gunicorn>=26.2.0`, `whitenoise>=6.12.0`, `psycopg>=3.3.6`, `redis>=8.1.0`, `polib>=1.2.0`, `bcrypt>=5.0.0`.
- `requirements-dev.txt` konflik digabung (flake8 7.4.1 + pip-audit 2.10.1).

### Teknis — Migrasi & Test
- Migrasi baru: `booking/0002`, `core/0003_auditlog`, `core/0004_alter_pagemeta_og_image`, `core/0005_payment_transaction`, `rental/0004_alter_rentalbooking_status`, `rental/0005_alter_vehicle_image`.
- Total test: **287 OK** (174 keamanan: 69 `tests_security` + 49 `tests_hardening` + 56 `tests_pakasir`).

---

## [1.0.0] — 2026-10-18

Rilis awal.

- Website pemesanan tiket bus antar kota & rental mobil (Django + Bootstrap 5 + Nginx).
- Modul `booking` (pencarian jadwal, denah kursi interaktif, anti double-booking `select_for_update`, kode `NT-XXXXXXXX`, pembayaran transfer/QRIS statis, verifikasi admin, kedaluwarsa 2 jam, cek booking, halaman SEO per rute) & `rental` (katalog MPV/SUV/Van/Bus kecil, estimasi harga live, kode `SEWA-XXXXXXXX`).
- Dwibahasa ID/EN (URL terpisah + hreflang), Open Graph/Twitter Card, `sitemap.xml`, `robots.txt`, JSON-LD terstruktur.
- Infrastruktur: `deploy/nginx.conf`, `docker-compose.yml`, `seed_data`, `compile_i18n` (378 string), 14 unit test awal.
- Dokumentasi README hero ala GitHub populer (badge, quick links, About & keywords).
- Lisensi MIT © 2026 njutawan.

[1.1.0]: https://github.com/njutawan/Website-Pemesanan-Bus/releases/tag/v1.1.0
[1.0.0]: https://github.com/njutawan/Website-Pemesanan-Bus/releases/tag/v1.0.0
