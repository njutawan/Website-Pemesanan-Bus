# Laporan Keamanan — Nusantara Trans

Audit 20 kontrol keamanan untuk Website Pemesanan Bus & Rental Mobil.
Dokumen ini adalah **bukti audit** yang dapat dilampirkan saat go-live;
setiap kontrol menyebutkan implementasi, test otomatis, dan sisa risiko.

- Tanggal audit: **2026-10-18**
- Basis kode: branch `arena/0fe36235-website-pemesanan-bus`
- Stack: Django 5.2.18, PostgreSQL 16, Gunicorn, Nginx, Redis (opsional)
- Hasil test: **181 test OK** (termasuk 68 test keamanan khusus)
- Hasil `security_audit`: **PASS 16, WARN 2, FAIL 0, N/A 2**

Perintah verifikasi ulang:

```bash
python manage.py test
python manage.py check
python manage.py security_audit          # exit ≠ 0 bila ada FAIL
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
| 4 | SSRF | ✅ PASS (N/A) | Tidak ada outbound HTTP/subprocess; URL internal divalidasi |
| 5 | Path traversal | ✅ PASS | Normalisasi media, allowlist ekstensi, 404 + CSP sandbox |
| 6 | Validasi input | ✅ PASS | `core/validators.py`, form Django, batas upload |
| 7 | Validasi output | ✅ PASS | Autoescape, JSON-LD `\u003c`, `csv_safe`, escape URL |
| 8 | Proteksi admin | ⚠️ PASS (WARN IP) | Login staf, rate limit, audit; allowlist IP opsional belum diset |
| 9 | Password default & data sensitif | ✅ PASS | Tidak ada password bawaan; seed wajib env di produksi |
| 10 | Audit endpoint | ✅ PASS | `core.AuditLog`, admin read-only, PII disamarkan |
| 11 | Verifikasi webhook | ✅ PASS (siap) | HMAC-SHA256, timestamp, anti-replay (`core/payments.py`) |
| 12 | Payment server | ✅ PASS (N/A) | Transfer manual/QRIS; tidak ada data kartu |
| 13 | Anti-tamper harga | ✅ PASS | Harga dihitung server, `select_for_update`, field klien diabaikan |
| 14 | IDOR | ✅ PASS | Kode acak 8 karakter, grant media per sesi, upload hanya status pending |
| 15 | Log tidak bocorkan secret | ✅ PASS | `RedactSecretsFilter`, audit masking, log Nginx disamarkan |
| 16 | Source map privat | ✅ PASS | Tidak ada `.map`; middleware & Nginx 404 |
| 17 | Update dependency | ✅ PASS | Patch keamanan minimum, Dependabot, `pip-audit` di CI |
| 18 | Test backup restore | ✅ PASS | `deploy/*.sh` + drill otomatis di CI |
| 19 | Security header | ✅ PASS | CSP hash, HSTS, XFO, nosniff, Referrer/Permissions-Policy, COOP/CORP |
| 20 | Test keamanan pra-rilis | ✅ PASS (WARN lokal) | 181 test + CI; `DEBUG=0` wajib saat go-live |

### Hasil audit mode produksi

Dengan `DJANGO_DEBUG=0`, HTTPS/cookie Secure, `POSTGRES_SSLMODE=require`,
`REDIS_URL` terisi, dan `DJANGO_ADMIN_ALLOWED_IPS` diisi CIDR LAN/loopback:

```text
python manage.py security_audit --no-fail
→ 20 kontrol — PASS 18, WARN 0, FAIL 0, N/A 2

python manage.py check --deploy --fail-level WARNING
→ System check identified no issues (0 silenced).
```

Nilai `127.0.0.1/32,::1/128,192.168.0.0/16` dipakai saat drill (loopback + LAN).
**Ganti dengan CIDR VPN/kantor Anda yang sebenarnya** — jangan hardcode
`0.0.0.0/0`. Tanpa nilai itu, audit lokal akan tetap menampilkan WARN poin 8
(itu memang disengaja: panel admin belum dibatasi).

---

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

**Implementasi** — Aplikasi **tidak melakukan request HTTP keluar** sama
sekali: tidak ada `requests`, `urllib.request`, `httpx`, `aiohttp`,
`socket`, `subprocess`, atau `eval` di kode aplikasi. URL yang dapat
diadministrasikan (`SeoKeyword.url`, `PageMeta.path`,
`django.contrib.redirects.new_path`) divalidasi sebagai **path internal**
(`/...`, bukan `//host`, bukan skema apa pun) sehingga tidak bisa dipakai
mengalihkan pengunjung ke domain luar.

**Test** — `SsrfTest`: validator menolak `https://`, `//host`,
`javascript:`; `SafeRedirectForm` menolak tujuan eksternal; pemindai kode
memastikan tidak ada HTTP client keluar.

**Status** — N/A untuk SSRF klasik (tidak ada URL yang di-fetch server),
tetapi kontrol open-redirect tetap diuji.

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

**Implementasi** — `core/payments.py`:

- `verify_webhook_signature(payload, header, secret, now, tolerance)`:
  HMAC-SHA256 atas `"{timestamp}.{payload}"`, format `t=…,v1=…`,
  perbandingan `hmac.compare_digest`, toleransi waktu default 300 detik,
  tolak secret kosong/header rusak;
- `parse_event`: hanya JSON objek, tolak array/XML/body besar;
- `claim_webhook_event`: anti-replay idempoten (event ID diklaim sekali;
  cache atomik), aman untuk retry gateway.

**Status** — **N/A saat ini**: situs memakai transfer manual/QRIS tanpa
callback. Helper sudah siap dan diuji agar integrasi gateway berikutnya
tidak mengulang kesalahan umum (tanpa verifikasi signature/replay).

**Test** — `WebhookTest`: signature valid, secret salah, timestamp basi,
secret kosong, replay ditolak, payload non-objek ditolak.

**Saat gateway diaktifkan** — audit berpindah otomatis dari N/A ke kontrol
aktif. Sudah diuji:

| Kondisi | Hasil |
|---|---|
| `PAYMENT_GATEWAY_PROVIDER=midtrans` + `PAYMENT_WEBHOOK_SECRET` terisi | butir 11 **PASS**, ringkasan `PASS 19, WARN 0, FAIL 0, N/A 1` |
| `PAYMENT_GATEWAY_PROVIDER=midtrans` tanpa secret | `manage.py check` **gagal** (`core.E015`), audit **FAIL** (exit 1) |

Artinya konfigurasi gateway tidak bisa "lupa verifikasi": sistem menolak
hidup tanpa secret. Checklist integrasi saat memakai Midtrans/Xendit:

1. `PAYMENT_GATEWAY_PROVIDER=midtrans` (atau `xendit`), `PAYMENT_WEBHOOK_SECRET`
   acak ≥ 32 byte dari dashboard gateway.
2. Buat view webhook `@csrf_exempt` yang membaca `request.body` **mentah**,
   panggil `verify_webhook_signature()` → `parse_event()` →
   `claim_webhook_event(event['id'])`, lalu cocokkan `order_id`/nominal
   dengan `Booking.code` + `total_price` di database.
3. Jangan pernah memakai nominal/status dari payload untuk membuat booking
   baru; payload hanya memverifikasi pembayaran yang sudah ada.
4. Balas `2xx` hanya setelah status tersimpan; selain itu `4xx` agar gateway
   tidak retry tanpa henti. Retry ganda aman karena idempoten.
5. Tambahkan endpoint ke `RATELIMIT_EXEMPT_PREFIXES` (gateway punya IP
   dinamis) dan batasi dengan signature, bukan rate limit.
6. Uji di sandbox gateway sebelum produksi; pantau audit `PAYMENT_VERIFIED`.

**Sisa risiko** — endpoint webhook adalah permukaan serangan baru: wajib
HTTPS, secret kuat, toleransi waktu kecil (300 s), dan log tidak boleh
memuat secret/header signature.

---

## 12. Pemeriksaan payment server

**Implementasi** — Alur pembayaran adalah **transfer manual / QRIS**:
pelanggan mengunggah bukti, staf memverifikasi di admin. Tidak ada server
pembayaran, callback, atau penyimpanan data kartu. Status booking hanya
bisa diubah oleh staf melalui admin (aksi "Konfirmasi pembayaran"), yang
memicu audit `PAYMENT_VERIFIED`.

**Status** — **N/A** (tidak ada payment server). Bila gateway ditambahkan,
wajib: signature (butir 11), idempotensi, rekonsiliasi nominal server-side,
dan jangan pernah menyimpan PAN/CVV. Karena situs tidak menyimpan data kartu
dan tidak menerima callback, tidak ada PCIDSS scope saat ini; memakai
halaman pembayaran hosted (Midtrans Snap / Xendit Checkout) menjaga kondisi
ini — jangan membuat form kartu sendiri.

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
4. `python manage.py test` (181 test, termasuk 68 test keamanan);
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
- [ ] `PAYMENT_WEBHOOK_SECRET` diisi bila gateway diaktifkan
- [ ] `python manage.py check --deploy --fail-level WARNING` → 0 issue
- [ ] `python manage.py security_audit` → FAIL 0, WARN ditinjau
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
