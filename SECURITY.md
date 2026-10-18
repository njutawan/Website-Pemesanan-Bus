# Laporan Keamanan — Nusantara Trans

Audit 20 kontrol keamanan untuk Website Pemesanan Bus & Rental Mobil.
Dokumen ini adalah **bukti audit** yang dapat dilampirkan saat go-live;
setiap kontrol menyebutkan implementasi, test otomatis, dan sisa risiko.

- Tanggal audit: **2026-10-18** · pembaruan integrasi Pakasir: **2026-10-19**
- Basis kode: branch `arena/0fe36235-website-pemesanan-bus`
- Stack: Django 5.2.18, PostgreSQL 16, Gunicorn, Nginx, Redis (opsional)
- Hasil test: **287 test OK** (termasuk 174 test keamanan khusus:
  69 `core/tests_security.py` + 49 `core/tests_hardening.py` +
  56 `core/tests_pakasir.py`)
- Hasil `security_audit`: **PASS 16, WARN 2, FAIL 0, N/A 2**
- Hasil `security_review` (19 kontrol hardening): **PASS 19, WARN 0, FAIL 0**
  dengan role DB non-superuser + SMTP

Perintah verifikasi ulang:

```bash
python manage.py test
python manage.py check
python manage.py security_audit          # exit ≠ 0 bila ada FAIL
python manage.py security_review         # 19 kontrol hardening
./deploy/scan_secrets.sh                 # rahasia di HEAD + riwayat git
python manage.py check --deploy --fail-level WARNING   # dengan env produksi
```

> Dua WARN pada audit adalah **kondisi lingkungan pengembangan**, bukan
> celah kode: (8) `ADMIN_ALLOWED_IPS` kosong dan (20) `DEBUG=1`. Keduanya
> wajib diset sebelum go-live — lihat checklist di bagian akhir.

---

## Ringkasan 20 kontrol

| # | Kontrol | Status | Bukti utama |
|---|---|---|---|
| 1 | Rate limit API/endpoint | ✅ PASS | `core/middleware.py` `RateLimitMiddleware`, `RATELIMIT_RULES`, Nginx `limit_req` |
| 2 | CORS ketat | ✅ PASS | `CorsMiddleware`, allowlist eksplisit, wildcard ditolak |
| 3 | CSRF | ✅ PASS | `CsrfViewMiddleware`, token semua form, cookie SameSite/Secure |
| 4 | SSRF | ✅ PASS | Satu HTTP client keluar (Pakasir) dengan host tetap `https://app.pakasir.com`, path tervalidasi, tanpa redirect; URL internal divalidasi |
| 5 | Path traversal | ✅ PASS | Normalisasi media, allowlist ekstensi, 404 + CSP sandbox |
| 6 | Validasi input | ✅ PASS | `core/validators.py`, form Django, batas upload |
| 7 | Validasi output | ✅ PASS | Autoescape, JSON-LD `\u003c`, `csv_safe`, escape URL |
| 8 | Proteksi admin | ⚠️ PASS (WARN IP) | Login staf, rate limit, audit; allowlist IP opsional belum diset |
| 9 | Password default & data sensitif | ✅ PASS | Tidak ada password bawaan; seed wajib env di produksi |
| 10 | Audit endpoint | ✅ PASS | `core.AuditLog`, admin read-only, PII disamarkan |
| 11 | Verifikasi webhook | ✅ PASS (aktif/N/A) | Pakasir v2: `X-Secret` constant-time + verifikasi ulang status API + idempoten (`core/payment_service.py`) |
| 12 | Payment server | ✅ PASS (aktif/N/A) | QRIS hosted Pakasir; tanpa data kartu, API key hanya di server; transfer manual tetap tersedia |
| 13 | Anti-tamper harga | ✅ PASS | Harga dihitung server, `select_for_update`, field klien diabaikan |
| 14 | IDOR | ✅ PASS | Kode acak 8 karakter, grant media per sesi, upload hanya status pending |
| 15 | Log tidak bocorkan secret | ✅ PASS | `RedactSecretsFilter`, audit masking, log Nginx disamarkan |
| 16 | Source map privat | ✅ PASS | Tidak ada `.map`; middleware & Nginx 404 |
| 17 | Update dependency | ✅ PASS | Patch keamanan minimum, Dependabot, `pip-audit` di CI |
| 18 | Test backup restore | ✅ PASS | `deploy/*.sh` + drill otomatis di CI |
| 19 | Security header | ✅ PASS | CSP hash, HSTS, XFO, nosniff, Referrer/Permissions-Policy, COOP/CORP |
| 20 | Test keamanan pra-rilis | ✅ PASS (WARN lokal) | 287 test + CI; `DEBUG=0` wajib saat go-live |

### Hasil audit mode produksi

Dengan `DJANGO_DEBUG=0`, HTTPS/cookie Secure, `POSTGRES_SSLMODE=require`,
`REDIS_URL` terisi, dan `DJANGO_ADMIN_ALLOWED_IPS` diisi CIDR LAN/loopback:

```text
python manage.py security_audit --no-fail
→ 20 kontrol — PASS 18, WARN 0, FAIL 0, N/A 2   # gateway manual

PAYMENT_GATEWAY_PROVIDER=pakasir \
PAKASIR_SLUG=… PAKASIR_API_KEY=… PAKASIR_WEBHOOK_SECRET=… \
python manage.py security_audit --no-fail
→ 20 kontrol — PASS 20, WARN 0, FAIL 0, N/A 0   # QRIS online aktif

python manage.py check --deploy --fail-level WARNING
→ System check identified no issues (0 silenced).
```

Nilai `127.0.0.1/32,::1/128,192.168.0.0/16` dipakai saat drill (loopback + LAN).
**Ganti dengan CIDR VPN/kantor Anda yang sebenarnya** — jangan hardcode
`0.0.0.0/0`. Tanpa nilai itu, audit lokal akan tetap menampilkan WARN poin 8
(itu memang disengaja: panel admin belum dibatasi).

---

## Audit lanjutan — 19 titik hardening

Pemeriksaan kedua dengan sudut pandang berbeda: bukan lagi "apakah ada
kontrol", tetapi "apakah nilainya benar di berkas, riwayat git, dan server".
Dijalankan otomatis lewat `python manage.py security_review` (exit 1 bila ada
FAIL) dan `deploy/scan_secrets.sh` (pemindai rahasia HEAD + riwayat git).

| # | Titik periksa | Hasil | Bukti |
|---|---|---|---|
| 1 | API key aman | ✅ PASS | Tidak ada key literal; `PAKASIR_API_KEY`/`PAKASIR_WEBHOOK_SECRET`/`EMAIL_PASSWORD` hanya dari env; dikirim lewat header & disamarkan di log |
| 2 | File `.env` tidak publik | ✅ PASS | `.gitignore` + tidak ter-track; Nginx `location ~ /\.` → 404; `deploy/scan_secrets.sh` |
| 3 | Tidak ada secret hardcoded | ✅ PASS (prod) | `SECRET_KEY` hanya placeholder dev (WARN lokal, `core.E002` menolak di produksi); password DB/email dari env |
| 4 | Secret di riwayat git | ✅ PASS | 2 commit dipindai; tanpa kunci/token/privat key. Password demo lama (`admin123`) hanya di `.env.example` pra-hardening, sudah dihapus di HEAD — bukan secret produksi |
| 5 | Debug OFF | ✅ PASS | `DEBUG = _env_bool('DJANGO_DEBUG', default=False)` — fail-closed; lupa set env tetap produksi. `check --deploy` (`security.W018`) menandai DEBUG=1 |
| 6 | Error tidak bocorkan detail | ✅ PASS | `handler400/403/404/500` → template sendiri; tidak ada traceback/settings/nama tabel di respons |
| 7 | Validasi input | ✅ PASS | `clean_public_code`, `clean_seat_labels`, `clean_phone`, `validate_travel_date`, `validate_image_upload`; `max_length` + rentang di form, divalidasi ulang di server |
| 8 | Sanitasi input | ✅ PASS | `clean_text()` membuang NUL/C0/C1 dan merapatkan spasi; charset kode dibatasi; autoescape template |
| 9 | Anti SQL injection | ✅ PASS | ORM berparameter; tanpa `.raw()`, `.extra()`, `RawSQL`, `cursor.execute` (dipindai otomatis) |
| 10 | Anti XSS | ✅ PASS | Autoescape aktif, tanpa `\|safe` pada data pengguna; JSON-LD `\u003c`; CSP hash + `script-src-attr 'none'` |
| 11 | Auth di server | ✅ PASS | Login/izin diperiksa Django; media privat lewat ACL sesi/staf; tombol UI bukan kontrol akses |
| 12 | Cek akses objek (IDOR) | ✅ PASS | Booking/sewa dicari via kode acak 8 karakter, bukan ID sekuensial; bukti bayar butuh staf/grant sesi |
| 13 | Role admin aman | ✅ PASS | `is_staff` + `is_active`; allowlist IP; `AuditLog` read-only; `User`/`Group` tidak didaftarkan di panel kustom |
| 14 | Database tidak publik | ✅ PASS | Dev: `127.0.0.1:5432`. Produksi: `docker-compose.prod.yml` tanpa `ports:` untuk db/redis; Nginx tidak mem-proxy 5432 |
| 15 | Izin database ketat | ✅ PASS (prod) | `deploy/db_setup.sql`: role `nt_app` `NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS`; runtime ≠ owner migrasi. WARN lokal bila memakai superuser |
| 16 | Hash password | ✅ PASS | `BCryptSHA256PasswordHasher` (cost 12) + 4 validator (panjang ≥ 12, kemiripan, password umum, numerik) |
| 17 | Session aman | ✅ PASS | `HttpOnly`, `Secure`, `SameSite=Lax`, umur 8 jam, sesi di DB (cookie hanya berisi ID), rotasi kunci saat login |
| 18 | Reset password aman | ✅ PASS | Tidak ada route reset publik (anti-enumerasi); ganti password via `/admin/` butuh sesi; token (bila dipakai) 60 menit, sekali pakai, di-hash |
| 19 | Batasi file upload | ✅ PASS | ≤ 6 MB/berkas, ≤ 5 berkas/request, ekstensi allowlist, `Pillow.verify()`, format JPEG/PNG/WEBP, batas 25 MP, Nginx 10M |

### Perintah & hasil

```text
python manage.py security_review
→ 19 kontrol — PASS 19, WARN 0, FAIL 0     (role nt_app non-superuser + SMTP, env produksi)

./deploy/scan_secrets.sh
→ ✔ Tidak ada rahasia terdeteksi.          (HEAD + riwayat git)
```

Di mesin pengembangan nilai yang sama akan menghasilkan WARN pada poin 3
(`SECRET_KEY` placeholder), 13 (allowlist IP kosong), 15 (role DB superuser),
dan 17 (cookie belum `Secure`/`SameSite=None`) — semuanya **kondisi lokal,
bukan celah kode**, dan hilang saat env produksi diisi (lihat
`deploy/db_setup.sql` untuk role `nt_app`).

**Catatan 11/12:** saat ini QRIS online **Pakasir** aktif, sehingga kedua
kontrol pada audit 20-kontrol berstatus PASS (webhook `X-Secret` +
verifikasi ulang status API). Bila gateway dimatikan, keduanya kembali N/A
dan transfer manual/QRIS statis tetap berfungsi.

### Perubahan kode pada pass ini

- `DEBUG` default **False** — produksi aman meski env lupa diisi; lokal pakai
  `DJANGO_DEBUG=1` atau `make dev`.
- Handler error `400`/`403` baru + template bermerek, tanpa detail internal.
- `clean_text()` dan `validate_image_upload()` di `core/validators.py`,
  dipasang pada `PageMeta.og_image` dan `Vehicle.image`
  (migrasi `core.0004`, `rental.0005`).
- `core/checks.py`: `W020` (izin `.env` ≠ 600), `W021` (email console di
  produksi → reset password tidak terkirim), `W022` (timeout reset > 24 jam).
- Email/`PASSWORD_RESET_TIMEOUT` eksplisit; upload limit terpusat di settings.
- `deploy/db_setup.sql` + `deploy/docker-compose.prod.yml` untuk pemisahan
  role owner/app dan DB tanpa port publik.
- `deploy/scan_secrets.sh`, `make` targets, `core/tests_hardening.py` (49 test).

### Integrasi QRIS Pakasir (2026-10-19)

- `core/pakasir.py` — klien API v2 (`create-transaction`,
  `transaction-status`): host tetap `https://app.pakasir.com`, timeout,
  respons ≤ 64 KiB, tanpa redirect, `X-Api-Key` header-only, error disanitasi.
- `core/models.PaymentTransaction` (migrasi `core.0005`) — order_id unik,
  nominal, status, expiry, sandbox, `needs_review`; read-only di admin.
- `core/payment_service.py` — pembuatan link idempoten (maks. 5 percobaan),
  sinkronisasi status manual (cooldown 4 detik), settlement atomik
  `select_for_update`, penanganan pembayaran terlambat.
- `core/payment_views.py` — `POST /pembayaran/{bus|rental}/<kode>/`,
  `/status/`, dan webhook `POST /pembayaran/pakasir/webhook/`.
- Template: panel “QRIS Online” di halaman booking bus & sewa; QRIS statis
  manual disembunyikan saat gateway aktif.
- `core/tests_pakasir.py` — 56 test (klien, webhook, settlement, IDOR/CSRF,
  konfigurasi, admin read-only).

## 1. Rate limit API/endpoint

**Implementasi** — `core/middleware.py::RateLimitMiddleware` menerapkan
`settings.RATELIMIT_RULES` per IP (menghormati `TRUSTED_PROXY_IPS`):

| Scope | Batas | Endpoint |
|---|---|---|
| `global` | 600 / 60 dtk | semua request |
| `unsafe` | 60 / 60 dtk | POST/PUT/PATCH/DELETE |
| `admin_login` | 8 / 300 dtk | `/admin/login/` per IP |
| `admin_login_user` | 5 / 300 dtk | per username (menahan password spraying) |
| `booking_create` | 15 / 3600 dtk | buat booking bus & rental |
| `proof_upload` | 15 / 3600 dtk | unggah bukti bayar |
| `lookup` | 120 / 600 dtk | cek booking via kode |
| `payment_create` | 10 / 3600 dtk | buat link bayar QRIS (per IP) |
| `payment_sync` | 30 / 600 dtk | cek status transaksi ke Pakasir |
| `payment_webhook` | 120 / 60 dtk | webhook Pakasir |

Respons `429` menyertakan header **`Retry-After`** dan `Cache-Control:
no-store`; pelanggaran pertama per jendela dicatat ke audit
(`RATE_LIMITED`). Tanpa Redis, batas berlaku per proses Gunicorn —
karena itu produksi wajib `REDIS_URL` (check `core.W013`).

**Test** — `core/tests_security.py::RateLimitTest`
(`test_lookup_dibatasi_dan_mengirim_retry_after`,
`test_ip_lain_tidak_terkena`, `test_bisa_dinonaktifkan_untuk_maintenance`),
`AdminProtectionTest.test_login_admin_dibatasi`.

**Berlapis di Nginx** — `limit_req_zone` general 20 r/s, form 20 r/m,
login 5 r/m; `limit_conn` 30 per IP; `limit_req_status 429`.

**Sisa risiko** — serangan terdistribusi (botnet) tidak sepenuhnya dicegah
oleh rate limit per IP; pertimbangkan WAF/Cloudflare saat trafik besar.

---

## 2. CORS ketat

**Implementasi** — `core/middleware.py::CorsMiddleware`. Header
`Access-Control-Allow-Origin` **hanya** dikirim bila `Origin` persis ada di
`CORS_ALLOWED_ORIGINS` (env `DJANGO_CORS_ALLOWED_ORIGINS`, dipisah koma).
Nilai `*` diabaikan; preflight dari origin asing dijawab **403**; respons
selalu `Vary: Origin`. Default: tidak ada origin lintas-domain.

**Test** — `CorsTest` (4 test): default tanpa header, echo hanya origin
eksplisit, preflight 403, wildcard diabaikan.

**Catatan** — API publik situs ini same-origin (HTML + form), sehingga CORS
memang tidak dibutuhkan; allowlist hanya untuk integrasi masa depan.

---

## 3. Proteksi CSRF

**Implementasi** — `django.middleware.csrf.CsrfViewMiddleware` aktif di
`MIDDLEWARE`. Semua form POST (booking, rental, cek booking, upload bukti,
form admin) memakai `{% csrf_token %}`. Cookie:

- Produksi HTTPS: `SameSite=Lax`, `Secure=True`.
- Pengembangan/preview HTTP: `SameSite=None` agar iframe preview tetap
  berfungsi — **hanya** saat `SECURE_SSL_REDIRECT=0`.
- `CSRF_TRUSTED_ORIGINS` eksplisit (env), bukan wildcard.

**Test** — `CsrfTest`: POST tanpa token → **403** dengan
`Client(enforce_csrf_checks=True)`; POST dengan token valid → lolos (404
karena kode uji tidak ada); pemindai template memastikan setiap `<form
method="post">` memiliki token.

**Sisa risiko** — `SameSite=None` di dev adalah kompromi preview; jangan
pernah dipakai di produksi. Check `core.E006` menolak `SameSite=None`
tanpa `Secure` pada mode produksi.

---

## 4. Pencegahan SSRF

**Implementasi** — Hanya ada **satu** HTTP client keluar: klien Pakasir di
`core/pakasir.py`. Pengamanannya:

- Host **dikunci** ke `https://app.pakasir.com` (konstanta + validasi
  `PAKASIR_BASE_URL`); tidak ada URL yang bisa dikendalikan pengguna.
- `slug`, `order_id`, dan `txn_id` dicocokkan regex lalu di-`quote()` sebelum
  masuk path; tidak ada query/URL bebas.
- `http.client` **tidak mengikuti redirect**; respons dibatasi 64 KiB;
  timeout 1–30 detik; TLS default (verifikasi sertifikat & hostname).
- API key hanya header `X-Api-Key`; pesan error disanitasi dari kredensial.
- Tidak ada `requests`, `urlopen`, `httpx`, `aiohttp`, `socket`, `subprocess`,
  atau `eval` di kode aplikasi lain. URL yang dapat diadministrasikan
  (`SeoKeyword.url`, `PageMeta.path`, `django.contrib.redirects.new_path`)
  divalidasi sebagai **path internal** (`/...`, bukan `//host`, bukan skema).

**Test** — `SsrfTest`: validator menolak `https://`, `//host`,
`javascript:`; `SafeRedirectForm` menolak tujuan eksternal; pemindai kode
memastikan hanya `core/pakasir.py` yang memuat `http.client`, dan klien
tersebut memakai host tetap serta header `X-Api-Key`.

**Status** — **PASS**: risiko SSRF dikendalikan dengan host tetap dan input
tervalidasi, bukan dengan menghilangkan seluruh outbound HTTP.

---

## 5. Pencegahan path traversal

**Implementasi** — `core/private_media.py::serve_media`:

1. `unquote` + `posixpath.normpath`, tolak NUL/backslash/`../`;
2. allowlist ekstensi (`MEDIA_ALLOWED_EXTENSIONS`: jpg/jpeg/png/webp) —
   `.html`, `.svg`, `.js`, `.php` → **404**;
3. media publik hanya `vehicles/`, `meta/`; bukti bayar
   (`payment_proofs/`, `rental_proofs/`) butuh staf atau grant sesi;
4. respons media selalu `X-Content-Type-Options: nosniff` +
   `Content-Security-Policy: default-src 'none'; sandbox`.

Nginx menolak `.php/.phtml/.html/.htm/.js/.svg/.xml/.json/.css/.map` di
bawah `/media/` dan mem-proxy direktori privat ke view Django.

**Test** — `MediaSecurityTest`: traversal polos, `%2e%2e`, double-encode,
`..%2f`, `%00`, ekstensi berbahaya, `nosniff`/CSP, bukti privat 404 untuk
anonim dan 200 untuk staf, source map 404.

---

## 6. Validasi input API/form

**Implementasi** — `core/validators.py`:

- `clean_public_code`: 4–20 karakter alfanumerik/strip (kode yang dihasilkan
  berformat `NT-[A-Z2-9]{8}` / `SEWA-[A-Z2-9]{8}`), batas panjang, normalisasi
  spasi/kapital;
- `clean_seat_labels`: format label, duplikat, jumlah maksimum
  (`MAX_SEATS_PER_BOOKING`), batas panjang;
- `validate_travel_date`: tidak boleh masa lalu, maksimum 1 tahun;
- `PaymentProofForm`: metode pembayaran hanya pilihan server, ukuran file
  ≤ 6 MB, ekstensi & content-type allowlist, `IMAGE_MAX_PIXELS` (anti
  decompression bomb);
- Form Django lain memakai validasi tipe/panjang; tanggal, kursi, dan
  ketersediaan dicek ulang di server saat POST (bukan hanya di UI).

**Test** — `InputValidationTest`, `PaymentAndPriceTest`, plus test form di
`booking/tests.py` & `rental/tests.py`.

---

## 7. Validasi output

**Implementasi** —

- Autoescape Django aktif; tidak ada `|safe` pada input pengguna.
- JSON-LD (`templatetags/booking_extras.py::jsonld`) meng-escape `<`, `>`,
  `&` menjadi `\u003c` dkk. sehingga `</script>` tidak bisa keluar dari blok.
- Ekspor CSV memakai `csv_safe` (prefix `'` untuk `= + - @`) — anti formula
  injection di Excel.
- `auto_internal_link` meng-escape URL sebelum menyisipkan `href`, hanya
  menerima path internal.
- Header `Content-Type` eksplisit + `nosniff`.

**Test** — `OutputValidationTest`: JSON-LD tidak menghasilkan `</script>`,
CSV menetralkan 4 formula, atribut `onmouseover` tidak bisa disusupkan,
nama pemesan `<script>` tampil sebagai teks.

---

## 8. Proteksi route admin

**Implementasi** —

- `/admin/` memerlukan `is_staff` + `is_active` (Django auth), password
  minimum 12 karakter (validator Django), dan `admin_login` rate limit.
- `AdminIPAllowlistMiddleware` mendukung `DJANGO_ADMIN_ALLOWED_IPS` (CIDR);
  IP di luar allowlist mendapat **404** (bukan 403, agar tidak membocorkan
  keberadaan admin).
- Semua percobaan login sukses/gagal dicatat ke `AuditLog`
  (`LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGIN_LOCKED`).
- Cookie sesi `HttpOnly`, `Secure` di produksi, `SameSite` ketat.

**Test** — `AdminProtectionTest`: anonim → redirect login; non-staf tidak
bisa masuk; staf bisa; allowlist IP (404 vs 200); login dibatasi 429.

**⚠️ WARN (lokal)** — nilai sudah disiapkan di `.env.example`
(`127.0.0.1/32,::1/128,192.168.0.0/16`), tetapi shell lokal belum
mengekspornya, jadi audit lokal tetap WARN. Audit mode produksi dengan env
tersebut menghasilkan PASS 18/WARN 0. Ganti CIDR LAN bila jaringan kantor
berbeda; jangan gunakan `0.0.0.0/0`.

---

## 9. Password default & data sensitif

**Implementasi** — `booking/management/commands/seed_data.py`:

- Tidak ada password bawaan di kode, `.env.example`, compose, atau README.
- `DJANGO_ADMIN_PASSWORD` (min. 12 karakter, bukan blocklist) dipakai bila
  diisi; `DEBUG=0` **menolak membuat admin** tanpa variabel ini
  (`CommandError`), sedangkan seed data non-admin tetap bisa berjalan.
- `DEBUG=1` tanpa env membuat password acak `secrets.token_urlsafe(18)` dan
  mencetaknya **sekali**; tidak pernah disimpan di repo.
- Bila akun admin lama masih memakai password bawaan versi sebelumnya,
  seed memberi peringatan agar `changepassword` dijalankan.
- Audit menyamarkan email, telepon, kode booking, dan path bukti bayar.
- `.env.example` tidak memuat secret apa pun; compose memakai
  `${POSTGRES_PASSWORD:?…}` sehingga gagal cepat bila kosong.

**Test** — `DefaultPasswordTest`: tidak ada string password lama di
`.env.example`/compose/README; password lemah ditolak; `DEBUG=0` tanpa env
menghasilkan `CommandError`; mode dev menghasilkan password acak ≥ 16
karakter.

---

## 10. Audit endpoint / jejak audit

**Implementasi** — `core/models.py::AuditLog` (migration
`core/0003_auditlog.py`) mencatat:

- autentikasi: login sukses/gagal, logout, akun terkunci;
- booking: dibuat, bukti diunggah, pembayaran diverifikasi, ekspor CSV;
- rate limit: pelanggaran pertama per jendela;
- metadata terstruktur (JSON) + IP + user agent, dengan masking PII.

`core/admin.py::AuditLogAdmin` **read-only** untuk superuser: tidak ada
tambah/ubah/hapus. Retensi dapat diatur `DJANGO_AUDIT_RETENTION_DAYS`
(default 180) dan dibersihkan oleh perintah
`python manage.py purge_audit_logs` (jadwalkan harian via cron).

**Test** — `AuditTest`: PII/secret disamarkan; kode booking menjadi
`NT-AB****`; login sukses/gagal tercatat; admin audit read-only dan hanya
superuser.

**Catatan** — "endpoint audit" berupa halaman admin
`/admin/core/auditlog/`, bukan API publik; akses mengikuti kontrol admin
(butir 8).

---

## 11. Verifikasi webhook

**Implementasi** — `core/payment_views.py`, `core/payment_service.py`,
`core/pakasir.py`:

- Endpoint `POST /pembayaran/pakasir/webhook/` (`@csrf_exempt`, hanya POST,
  di luar `i18n_patterns` agar URL stabil).
- Header `X-Secret` dari halaman proyek Pakasir dibandingkan dengan
  `hmac.compare_digest`; secret kosong/berbeda → **401** dan audit
  `WEBHOOK_REJECTED`. Tanpa secret, QRIS online tidak diaktifkan sama sekali.
- Body dibatasi **16 KiB** dan wajib JSON objek; `order_id`, `txn_id`,
  `amount`, `status`, `is_sandbox` divalidasi tipenya (bukan mempercayai
  string/boolean palsu). Content-Type tidak dijadikan gerbang karena contoh
  resmi Pakasir memakai `curl --data` (form-urlencoded) dengan body JSON.
- `order_id` dicari ke `PaymentTransaction`; `txn_id`, nominal, dan mode
  sandbox harus cocok dengan yang tercatat di database.
- **Verifikasi ulang wajib:** server memanggil
  `GET /api/v2/transaction-status/{slug}/{txn_id}` dengan `X-Api-Key` dan
  mensyaratkan `status=completed`, `order_id` sama, `amount` sama. Body
  webhook saja **tidak pernah** cukup untuk mengonfirmasi booking.
- Settlement atomik (`select_for_update` pada transaksi + booking),
  idempoten; audit `PAYMENT_RECEIVED` / `PAYMENT_UNMATCHED`.
- Balasan: `200` sukses/duplikat, `400` payload/nominal/status salah,
  `401` secret salah, `404` order tak dikenal, `409` belum lunas menurut API,
  `503` API tidak terjangkau (Pakasir retry).

**Status** — **PASS** saat gateway Pakasir aktif; **N/A** bila memakai
transfer manual. Hasil uji konfigurasi:

| Kondisi | Hasil |
|---|---|
| `PAYMENT_GATEWAY_PROVIDER=pakasir` + slug/API key/webhook secret | butir 11 & 12 **PASS**, ringkasan `PASS 20, WARN 0, FAIL 0, N/A 0` |
| `pakasir` tanpa kredensial lengkap | `manage.py check` **gagal** (`core.E020`), audit **FAIL** |
| Provider tak dikenal (`midtrans`, dll.) | `core.E019`, audit **FAIL** |
| Tanpa provider (transfer manual) | **N/A** (2 kontrol), alur lama tetap berjalan |

**Test** — `core/tests_pakasir.WebhookTest` (22 test): secret salah/kosong,
GET ditolak, JSON rusak, body > 16 KiB, `order_id`
tidak dikenal, `txn_id`/nominal/sandbox tidak cocok, API masih pending,
API error → 503 tanpa konfirmasi, webhook ganda idempoten, pembayaran
setelah EXPIRED/melewati batas waktu → `needs_review`, webhook sewa,
amount numerik berbentuk string, dan CSRF-exempt.

**Sisa risiko** — `X-Secret` bersifat statis (bukan signature per-request
seperti HMAC). Bila secret bocor, penyerang bisa mengirim event palsu;
karena itu setiap event tetap diverifikasi ulang ke API dengan API key
server-side. Rotasi secret dari dashboard bila dicurigai bocor, wajib HTTPS,
dan pantau audit `WEBHOOK_REJECTED`. Endpoint publik dibatasi 120
permintaan/menit per IP (di samping batas global).

---

## 12. Pemeriksaan payment server

**Implementasi** — QRIS diproses di **halaman hosted Pakasir**
(`payment_link` + `qris_only=1`). Situs tidak menerima, memproses, atau
menyimpan PAN/CVV/data kartu apa pun. Yang disimpan hanya `txn_id`,
`order_id`, nominal, `fee`, `total_payment`, status, `expires_at`,
`is_sandbox`, dan URL pembayaran resmi (`https://app.pakasir.com/pay-v2/…`).

- API key hanya dikirim dari server lewat header `X-Api-Key` (tidak pernah ke
  browser, template, URL, atau log).
- `PaymentTransaction` read-only untuk superuser; tidak ada tombol
  "tandai lunas" manual. Pembayaran yang tidak bisa dicocokkan ditandai
  `needs_review` dan tidak mengubah status booking.
- Transfer bank manual + verifikasi admin tetap tersedia sebagai fallback
  bila gateway mati atau pelanggan memilih bank transfer.
- Nominal tidak pernah berasal dari klien: dibuat dari `total_price` di
  database; nominal di webhook/API dicocokkan dengan nilai tersebut.

**Status** — **PASS** saat gateway aktif; **N/A** saat hanya transfer manual.

**Sisa risiko** — ketersediaan pihak ketiga: bila API Pakasir down, pembuatan
link dan sinkronisasi status gagal dengan pesan aman (booking tetap PENDING
dan dapat dibayar via transfer manual). Biaya gateway (`total_payment =
amount + fee`) ditanggung pembeli dan ditampilkan di halaman Pakasir. Link
berlaku 24 jam, sedangkan booking kedaluwarsa 2 jam — pembayaran setelah
EXPIRED tidak dikonfirmasi otomatis dan perlu refund/tinjauan admin. Karena
halaman pembayaran di-host Pakasir, scope PCI DSS tetap di sisi mereka;
jangan pernah membuat form kartu sendiri di situs ini.

---

## 13. Anti-tamper harga

**Implementasi** —

- Booking bus: `total_price = schedule.price × jumlah kursi` dihitung di
  `CreateBookingView.post` dari objek `Schedule` yang dikunci
  `select_for_update()`; field `total_price`/`price` dari klien diabaikan.
- Rental: `total_price` dihitung dari `vehicle.price_per_day × hari`
  (+ driver fee bila dipilih) di view; `days`, `price_per_day`, dan
  `total_price` dari klien tidak dipercaya; tanggal divalidasi ulang.
- Ketersediaan kursi dicek ulang di dalam transaksi (anti balapan/oversell).
- Status awal selalu `PENDING`; klien tidak bisa mengirim `status=CONFIRMED`.

**Test** — `PaymentAndPriceTest.test_harga_booking_tidak_bisa_ditimpa_klien`
dan `test_harga_rental_tidak_bisa_ditimpa_klien`: POST berisi harga palsu
tetap menghasilkan 50.000 (bus) dan 800.000 (rental 2 hari), status tetap
`PENDING`.

**Sisa risiko** — perubahan harga oleh admin setelah booking dibuat tidak
mengubah booking lama (memang disengaja); pastikan proses refund manual.

---

## 14. Cek IDOR

**Implementasi** —

- Kode booking **acak 8 karakter** dari alfabet 32 (`NT-`/`SEWA-`),
  ~40 bit entropy, bukan ID sekuensial; pencarian memakai `code`,
  bukan `pk`.
- Endpoint cek booking dibatasi rate limit (120/10 menit) untuk menahan
  enumerasi.
- Detail booking/sewa hanya menampilkan data untuk kode yang diberikan;
  tidak ada parameter `user_id`/`booking_id` yang bisa ditukar.
- Bukti bayar privat: grant per sesi **per path persis** (maks. 20),
  staf boleh akses, anonim 404. Upload hanya untuk booking berstatus
  `PENDING` dan belum lewat batas bayar.
- Ekspor CSV hanya untuk staf dan memakai `csv_safe`.

**Test** — `PaymentAndPriceTest.test_idor_kode_tidak_valid_dan_upload_bukan_pending`,
`MediaSecurityTest.test_bukti_privat_tetap_tertutup`, `RateLimitTest`.
Kode acak diverifikasi formatnya di test booking/rental.

**Sisa risiko** — kode booking berfungsi sebagai *bearer token* (pemilik
halaman); jangan membagikan kode. Untuk keamanan lebih tinggi, tambahkan
PIN/OTP atau login pelanggan.

---

## 15. Log tidak membocorkan secret

**Implementasi** —

- `core/logging.py::RedactSecretsFilter` dipasang pada handler `console`
  (semua log Django/aplikasi): menyamarkan password, token, API key,
  `Authorization: Bearer/Basic`, DSN `postgres://user:pass@…`,
  `django-insecure-…`, email, dan nomor telepon.
- `core/audit.py` menyamarkan target (email/telepon/kode booking) dan
  metadata sensitif (`password`, `token`, `email`, `phone`, `proof`).
- Nginx `log_format` mengganti kode booking di URL dengan `[REDACTED]`.
- Tidak ada `print()`/log yang menulis `request.POST` mentah.

**Test** — `LogRedactionTest` (filter + konfigurasi handler),
`AuditTest.test_audit_menyamarkan_pii_dan_secret`.

**Sisa risiko** — log akses Nginx tetap memuat IP & User-Agent (perlu untuk
operasi); atur retensi dan akses file log. `error_log` Nginx pada level
`warn`/`error` dapat memuat request line (termasuk kode booking) saat ada
gangguan upstream; batasi akses file log (root, 640) dan rotasi cepat,
atau turunkan level error log bila tidak diperlukan. Bila mengaktifkan
access log Gunicorn, gunakan format kustom yang menyamarkan `/bus/booking/`
dan `/rental/sewa/` (Nginx sudah melakukannya).

---

## 16. Source map privat

**Implementasi** —

- Tidak ada berkas `*.map` di repo (`static/`), dan `collectstatic` tidak
  menyalinnya.
- `BlockSourceMapsMiddleware` mengembalikan **404** untuk path berakhiran
  `.map` (case-insensitive).
- Nginx: `location ~* \.map$ { return 404; }`.
- Aset pihak ketiga (Bootstrap 5.3.8, Chart.js 4.5.1) di-vendor **tanpa**
  source map dan tanpa CDN.

**Test** — `SourceMapAndDependencyTest.test_tidak_ada_source_map_di_static`,
`MediaSecurityTest.test_source_map_selalu_404`, serta pemeriksaan konfigurasi
Nginx.

---

## 17. Update dependency

**Implementasi** — `requirements.txt` mematok **versi minimum patch
keamanan** (per 2026-10-18):

| Paket | Minimum |
|---|---|
| Django | 5.2.18,<5.3 (LTS) |
| Pillow | 13.0.0 |
| gunicorn | 26.2.0 |
| whitenoise | 6.12.0 |
| psycopg[binary] | 3.3.6 |
| django-compressor | 4.6.0 |
| redis | 8.1.0 |
| polib | 1.2.0 |
| bcrypt | 5.0.0 |

- `.github/dependabot.yml`: update mingguan untuk pip, GitHub Actions, dan
  Docker.
- `requirements-dev.txt`: `pip-audit`, `flake8`; CI menjalankan
  `pip-audit -r requirements.txt` dan `pip check`.
- Bootstrap 5.3.8 & Chart.js 4.5.1 di-vendor (bukan CDN) + LICENSE.

**Test** — `SourceMapAndDependencyTest.test_requirements_memakai_versi_patch_keamanan`.

**Sisa risiko** — `pip-audit` bergantung pada database CVE; jalankan juga
`pip list --outdated` dan review Dependabot PR secara berkala. Django 6.x
belum dipakai (tetap di LTS 5.2).

---

## 18. Test backup & restore

**Implementasi** — `deploy/`:

- `backup.sh`: `pg_dump --format=custom`, tar media, `SHA256SUMS`,
  enkripsi GPG opsional, retensi harian, symlink `latest`, hapus backup
  setengah jadi bila gagal.
- `restore.sh`: verifikasi checksum, tolak tar dengan path absolut/`..`,
  dekripsi GPG, drop/create database, `pg_restore --exit-on-error`, simpan
  media lama sebagai `media.pre-restore-<stamp>`.
- `verify_backup.sh`: **drill restore** ke database sementara, hitung
  `django_migrations`/booking/rental/audit, uji arsip media, lalu hapus
  database sementara — database asli tidak disentuh.
- `deploy/BACKUP.md`: cron harian, drill bulanan, prosedur insiden, checklist
  bukti audit (RPO ≤ 24 jam, RTO ≤ 2 jam).

**Bukti** — drill dijalankan pada PostgreSQL 16 lokal:
`db.dump: OK`, `media.tar.gz: OK`, `migrasi=31`, **`✔ Drill restore
BERHASIL`**. CI (`.github/workflows/python-app.yml`) mengulang drill yang
sama pada setiap push/PR.

**Test** — `BackupTest`: ketiga skrip ada, executable, `bash -n` valid, dan
`BACKUP.md` menyebut prosedur drill.

**Sisa risiko** — backup di host yang sama tidak melindungi dari
ransomware/kehilangan disk; wajib salinan off-site (S3/B2/rsync) dan uji
restore tahunan di staging.

---

## 19. Security header

**Implementasi** — `core/middleware.py::SecurityHeadersMiddleware` +
`SECURE_*` Django:

- **CSP**: `default-src 'self'`, `object-src 'none'`,
  `script-src 'self' 'sha256-…'` (hash inline script dihitung per respons;
  tanpa `unsafe-inline`), `style-src 'self' 'unsafe-inline'` (Bootstrap),
  `img-src 'self' data:`, `frame-ancestors 'none'` di produksi.
  Admin memakai CSP terpisah (izinkan inline untuk admin Django).
- `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  strict-origin-when-cross-origin`, `Permissions-Policy` (kamera/mic/geo
  dimatikan), `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`.
- Produksi: `Strict-Transport-Security` (1 tahun, preload), `X-Frame-Options:
  DENY`, `SECURE_SSL_REDIRECT`, cookie `Secure`.
- Header `Server` Django dihapus; Nginx memakai `server_tokens off` sehingga versi tidak dibocorkan.
- Nginx menambahkan set header yang sama sebagai lapisan kedua.

**Test** — `SecurityHeadersTest` (5 test): header wajib, hash CSP cocok
dengan isi `<script>`, tidak ada `unsafe-inline` di `script-src` publik,
CSP admin terpisah, frame/HSTS di mode produksi, dan tidak ada
`on*=` inline di template.

**Catatan preview** — di HTTP/dev, `frame-ancestors`/XFO sengaja tidak
dipasang agar preview iframe Arena bisa dibuka. Produksi
(`SECURE_SSL_REDIRECT=1`) selalu `DENY`. Jangan go-live dengan
`DJANGO_SSL_REDIRECT=0`.

---

## 20. Test keamanan sebelum go-live

**Implementasi** — `.github/workflows/python-app.yml` menjalankan pada
setiap push/PR:

1. `pip check` + `pip-audit -r requirements.txt`;
2. `flake8` (error sintaks/undefined name);
3. `python manage.py check`;
4. `python manage.py test` (287 test, termasuk 174 test keamanan);
5. `python manage.py security_audit --no-fail`;
6. `python manage.py check --deploy --fail-level WARNING` dengan env
   produksi (DEBUG=0, HTTPS, cookie Secure, admin IP, Redis, `sslmode=require`);
7. `migrate` + `seed_data` + backup + **drill restore**.

**Test** — `PreLiveGateTest`: audit menampilkan 20 kontrol dengan FAIL 0;
`check --deploy` menolak konfigurasi tidak aman (SECRET_KEY lemah,
`ALLOWED_HOSTS=*`, password DB lemah/kosong, `sslmode=disable`,
SameSite=None tanpa Secure, cookie tidak Secure); konfigurasi aman lolos
tanpa ERROR.

**⚠️ WARN** — di lingkungan lokal `DEBUG=1`, sehingga `check --deploy`
belum menjadi gerbang penuh. **Sebelum go-live**, jalankan dengan env
produksi dan pastikan:

```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY=… DJANGO_ALLOWED_HOSTS=… \
DJANGO_SSL_REDIRECT=1 DJANGO_COOKIE_SECURE=1 \
POSTGRES_PASSWORD=… POSTGRES_SSLMODE=require \
REDIS_URL=… DJANGO_ADMIN_ALLOWED_IPS=… \
python manage.py check --deploy --fail-level WARNING
python manage.py security_audit
```

---

## Checklist go-live

- [ ] `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` acak ≥ 50 karakter
- [ ] `DJANGO_ALLOWED_HOSTS` domain eksplisit (tanpa `*`)
- [ ] `DJANGO_SSL_REDIRECT=1`, `DJANGO_COOKIE_SECURE=1`,
      `DJANGO_COOKIE_SAMESITE=Lax`
- [ ] `POSTGRES_PASSWORD` kuat + `POSTGRES_SSLMODE=require`
- [ ] `REDIS_URL` terisi (rate limit lintas worker)
- [ ] `DJANGO_ADMIN_ALLOWED_IPS` diisi (loopback + CIDR LAN kantor)
- [ ] Password admin diganti; `DJANGO_ADMIN_PASSWORD` tidak ada di repo
- [ ] `CORS_ALLOWED_ORIGINS` kosong atau origin eksplisit (tanpa `*`)
- [ ] QRIS online: `PAYMENT_GATEWAY_PROVIDER=pakasir`, `PAKASIR_SLUG`,
      `PAKASIR_API_KEY`, `PAKASIR_WEBHOOK_SECRET`, `PAKASIR_SANDBOX=0`
- [ ] Webhook URL di dashboard Pakasir =
      `https://domain-anda/pembayaran/pakasir/webhook/` (HTTPS)
- [ ] Uji 1 pembayaran QRIS nyata bernominal kecil + 1 transaksi sandbox;
      pastikan booking otomatis `CONFIRMED`
- [ ] Transfer manual + unggah bukti tetap berfungsi saat gateway dimatikan
- [ ] `python manage.py check --deploy --fail-level WARNING` → 0 issue
- [ ] `python manage.py security_audit` → FAIL 0, WARN ditinjau
      (`PASS 20` bila Pakasir aktif; `N/A 2` bila manual)
- [ ] `python manage.py test` → semua lulus
- [ ] Backup harian + drill restore ≤ 30 hari, salinan off-site
- [ ] Nginx `server_tokens off`, HSTS, TLS 1.2/1.3, `nginx -t` lulus
- [ ] Log & audit dibatasi aksesnya, retensi sesuai kebijakan
- [ ] Uji beban ringan (rate limit tidak memblokir pengguna wajar)

---

## Pelaporan kerentanan

Temukan masalah keamanan? Jangan buka issue publik. Hubungi pemilik
repository secara privat (atau `security@` domain produksi) dengan:
langkah reproduksi, dampak, dan versi/commit. Target respons: 3 hari kerja.
