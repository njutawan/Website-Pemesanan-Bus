<div align="center">

<img src="static/img/logo.png" width="90" alt="Nusantara Trans">

# 🚌 Nusantara Trans — Website Pemesanan Tiket Bus & Rental Mobil

Pesan **tiket bus antar kota** dengan denah kursi interaktif & pembayaran QRIS,
plus **rental mobil** — lengkap dengan panel admin, SEO siap ranking, dan dwibahasa ID/EN.

**Dibangun dengan [Django 5.2](https://www.djangoproject.com/) + [PostgreSQL](https://www.postgresql.org/) + [Bootstrap 5](https://getbootstrap.com/). Didukung [Docker](https://www.docker.com/), [Nginx](https://nginx.org/) & [Redis](https://redis.io/) — demo data Jember & sekitarnya.**

<br>

<a href="#quick-start">
  <img height="42" src="https://img.shields.io/badge/GETTING%20STARTED-24292e?style=for-the-badge&amp;logo=github&amp;logoColor=white" alt="Getting Started">
  <img height="42" src="https://img.shields.io/badge/MULAI%20SEKARANG-2ea44f?style=for-the-badge" alt="Mulai Sekarang">
</a>
<a href="#deploy">
  <img height="42" src="https://img.shields.io/badge/DEPLOY%20PRODUKSI-24292e?style=for-the-badge&amp;logo=docker&amp;logoColor=white" alt="Deploy Produksi">
  <img height="42" src="https://img.shields.io/badge/DOCKER%20%26%20NGINX-1f6feb?style=for-the-badge" alt="Docker & Nginx">
</a>

<br>

<a href="#quick-start"><strong>Mulai Cepat</strong></a> · <a href="#fitur"><strong>Fitur</strong></a> · <a href="#alur-pemesanan"><strong>Alur Pemesanan</strong></a> · <a href="#deploy"><strong>Deploy</strong></a> · <a href="#stack"><strong>Stack</strong></a>

<br><br>

<img src="https://img.shields.io/badge/framework-Django-0C4B33" alt="framework Django">
<img src="https://img.shields.io/badge/database-PostgreSQL-4169E1" alt="database PostgreSQL">
<img src="https://img.shields.io/badge/ui-Bootstrap%205-7952B3" alt="ui Bootstrap 5">
<img src="https://img.shields.io/badge/python-3.11%2B-3776AB" alt="python 3.11+">
<img src="https://img.shields.io/badge/language-ID%20%7C%20EN-6e40c9" alt="language ID | EN">
<img src="https://img.shields.io/github/stars/njutawan/Website-Pemesanan-Bus?label=stars&amp;color=2ea44f" alt="stars">

<br><br>

<table>
  <tr>
    <td align="center" width="50%">
      <sub>⚡ <b>CEPAT DIJALANKAN</b></sub><br><br>
      <strong>4 Perintah ke Demo Lokal</strong><br>
      <sub>install → migrate → seed → runserver</sub>
    </td>
    <td align="center" width="50%">
      <sub>🔍 <b>SEO &amp; PERFORMA</b></sub><br><br>
      <strong>JSON-LD · Sitemap · WebP · Cache</strong><br>
      <sub>TTFB ~5–10 ms · Core Web Vitals terjaga</sub>
    </td>
  </tr>
</table>

<br>

<img src="static/img/hero-bus-900.webp" width="100%" alt="Nusantara Trans — tiket bus antar kota & rental mobil">

</div>

> 📍 Demo data: kota **Jember & sekitarnya** (Jawa Timur). Rute, jadwal, armada, dan mobil rental sudah diisi lewat perintah `seed_data`.

---

<a id="fitur"></a>

## ✨ Fitur

### Tiket Bus
- Pencarian jadwal (kota asal, tujuan, tanggal, jumlah penumpang)
- **Denah kursi interaktif** — layout mengikuti kelas bus (Ekonomi 2-2, AC 2-2,
  Eksekutif 2-1, Sleeper 1-1), kursi terisi otomatis terkunci
- Kode booking unik (format `NT-XXXXXX`), ringkasan harga real-time
- **Pembayaran transfer manual / QRIS** + unggah bukti (JPG/PNG)
- Verifikasi admin 1-klik dari panel admin (aksi *Konfirmasi pembayaran*)
- Kedaluwarsa otomatis: kursi dilepas jika tidak dibayar dalam 2 jam (bisa diatur)
- Halaman **cek booking** via kode
- Halaman SEO per rute: `/bus/rute/jember-surabaya/`

### Rental Mobil
- Katalog mobil dengan filter kategori (MPV / SUV / Van / Bus kecil)
- Detail unit + spesifikasi + estimasi harga live (hari × harga + opsi sopir)
- Pemesanan sewa → kode `SEWA-XXXXXX` → upload bukti → verifikasi admin

### Umum
- **Dwibahasa**: Indonesia (`/`) & English (`/en/`) — URL terpisah, ramah SEO
- **Open Graph** + Twitter Card di semua halaman, `sitemap.xml`, `robots.txt`
- Desain responsif Bootstrap 5.3 + tema kustom (navy/oranye)

### 🎛️ Panel Admin & Dasbor Operasional (`/admin/`)
- **Dasbor kustom**: kartu statistik (booking hari ini, menunggu verifikasi,
  belum bayar, pendapatan bulan ini, sewa pending, keberangkatan hari ini)
- **Grafik Chart.js**: booking & pendapatan 14 hari terakhir + donat status booking
- **Antrean verifikasi pembayaran** langsung dari dasbor + tombol
  **Konfirmasi 1-klik** di halaman edit booking/sewa (via `response_change`)
- **Okupansi keberangkatan hari ini**: kursi terjual/total per jadwal dengan bar warna
- Rute terpopuler 30 hari, booking & sewa terbaru, aksi cepat tambah data
- Optimasi performa: `list_select_related` (anti N+1), `autocomplete_fields`
  untuk jadwal/bus/mobil (tidak lagi memuat semua opsi sekaligus), `list_per_page`
- **Ekspor CSV** booking & sewa (delimiter `;` + BOM UTF-8, siap Excel Indonesia)
- Filter **bukti pembayaran** (sudah/belum unggah) + kolom status bukti
- Branding admin kustom (header navy/oranye, ikon Font Awesome)

### 🔀 Manajemen 301 Redirect (`django.contrib.redirects`)
- `RedirectFallbackMiddleware` terpasang (paling bawah di MIDDLEWARE):
  URL lama yang 404 dicek ke tabel redirect → jawab **301 permanen** ke URL
  baru, sehingga perpindahan URL tidak jadi broken link di mata mesin pencari
- Kelola lewat panel admin: **/admin/ → Redirects** (old path → new path)
- Contoh seed: `/tiket/` → `/bus/`, `/sewa-mobil/` → `/rental/`,
  `/cek/` → `/bus/cek-booking/`, dll. (`seed_data`)
- Perilaku bawaan Django yang perlu diketahui: pencocokan old_path **persis
  termasuk query string** (daftarkan old_path dengan query bila perlu), dan
  redirect selalu 301 (middleware hanya menyapa respons 404 — halaman nyata
  tidak akan tertimpa)

### 🔍 SEO
- **Topic cluster / silo (arsitektur kategori)** — piramida tertutup
  per kota asal, aturan aliran link dipatuhi & dijaga test:
  * **Pillar/hub**: `/bus/rute/` (global) + **pillar per kota**
    `/bus/rute/dari/<kota>/` (masuk sitemap 0.7/weekly, kota tanpa rute
    aktif = 404 jujur, bukan halaman kosong)
  * **Upward (wajib)**: semua halaman rute selalu menautkan ke pillar
    kotanya & hub — tanpa syarat
  * **Downward**: hub & pillar menautkan ke seluruh rute di bawahnya
  * **Lateral**: antar-rute hanya se-silo (kota asal sama, maks 4);
    pillar antar-kota saling menyandingkan (link antar-kategori)
  * **Anchor & in-text linking**: tanpa anchor generik (audit "klik di
    sini" = nihil; semua anchor deskriptif: nama rute, "Bus dari {kota}");
    filter **`auto_internal_link`** (`core/templatetags/seo_internal_links.py`)
    menautkan istilah kunci pada **pemunculan pertama** (FAQ, deskripsi
    mobil). Sumber istilah: model **`SeoKeyword`** (dikelola /admin/,
    sinyal hapus cache otomatis) + pillar kota ber-rute aktif.
    HTML-safe: escape dulu, tak menyusup ke `<a>` existing; **anti
    self-link** via `request.path`; **batas densitas** 1 link/250 kata
    (rentang 1-4 per blok ≈ 2-4 per 1000 kata); URL dinormalisasi
    slash-akhir (APPEND_SLASH) & divalidasi path internal; anchor
    distyling `.ilink` (garis bawah titik-titik)
  * **Homepage PageRank**: pillar kategori kini **1 klik** via grid
    "Pilih kota keberangkatan" (9 pillar, anchor "Bus dari {kota}") di
    samping kartu rute populer & armada unggulan; **tanpa link non-SEO**
    (audit: tak ada login/privacy/terms di homepage; Cek Booking =
    utility tetap ada karena kebutuhan pelanggan)
  * **Komponen otomatis**: breadcrumb terlihat + JSON-LD di semua halaman
    dalam (upward link + data terstruktur SERP, markup = konten terlihat);
    lateral terkunci per silo (sibling rute se-kota, "Mobil lainnya" rental —
    tanpa widget acak); **navigasi prev/next** antar-rute dalam silo yang
    sama (urut kota tujuan, 0 query — dari katalog cache) agar rute lama
    tidak menjadi deep page
  * **Anti lintas-silo**: link kontekstual dalam `<main>` halaman rute
    tidak pernah keluar ke silo lain (dijaga test; navbar/footer = global
    chrome di luar cakupan)
  * **Model kategori**: kategori = kota asal, **1 level (flat)** —
    `ForeignKey` standar (`Route.origin → City`) sudah cukup;
    django-mptt/treebeard tidak diperlukan (sub-kategori bertingkat tidak
    ada). Keunikan pasangan dijamin `unique_together (origin, destination)`
  * **URL hierarkis** (struktur `/kategori/artikel`): artikel rute
    bersarang di silonya — `/bus/rute/dari/jember/surabaya/`; breadcrumb
    terlihat & JSON-LD kini 5 tingkat (Beranda → Tiket Bus → Semua Rute →
    Dari {kota} → rute). URL lama flat (`/bus/rute/jember-surabaya/`)
    otomatis **301 permanen** ke struktur baru (equity tidak hilang)
  * Semua tautan dari satu katalog cache `hub:routes` (0 query hangat);
    filter `?kategori=` rental diberi `noindex, follow` (konsolidasi kanonik)
- **Halaman error terindeks bersih**: `404.html` & `500.html` branded —
  status HTTP **tetap 404/500** (tanpa redirect — redirect dianggap
  *soft 404* oleh Google dan merusak reputasi domain). Halaman 404
  menyertakan navigasi utama, **form pencarian jadwal** (asal/tujuan/tanggal),
  tombol pintasan, dan saran rute populer untuk menekan bounce rate
- **robots.txt dinamis** (TemplateView): baris `Sitemap:` menunjuk URL absolut
  `/sitemap.xml` secara otomatis + `Disallow` untuk halaman transaksi
  (`/bus/kursi/`, `/bus/booking/`, `/rental/sewa/` — termasuk varian `/en/`)
- **sitemap.xml** (`django.contrib.sitemaps`): halaman statis + seluruh rute
  bus & armada rental dari query model — URL baru **otomatis terdaftar**
  lengkap `lastmod` (field `updated_at`), `changefreq`, dan `priority` per URL;
  respons di-cache 30 menit
- **Metadata halaman di `/admin/`** (menu *Metadata halaman (SEO)*,
  model `core.PageMeta`): kelola `title`, meta description, gambar Open Graph,
  dan flag noindex per path. Baris tanpa prefiks (`/bus/`) berlaku untuk ID &
  EN; buat `/en/bus/` bila ingin judul khusus EN. Prioritas:
  **PageMeta > judul halaman/objek > default templat**
- **Security & bot headers**: `SECURE_CONTENT_TYPE_NOSNIFF` +
  Referrer-Policy selalu aktif; **HSTS 31536000** & `X-Frame-Options: DENY`
  otomatis saat produksi (`DJANGO_SSL_REDIRECT=1` — XFO env-gated agar
  pratinjau sandbox yang berbasis iframe tidak rusak).
  `GZipMiddleware` mengompres payload dinamis (statik via WhiteNoise/Nginx).
  `X-Robots-Tag`: `noindex, nofollow` utk `/admin/` & `/media/` (juga di
  Nginx), `noindex, follow` utk halaman berparameter pencarian
  (`?origin=…&destination=…`) — kendali perayapan per-respons
- **Password bcrypt**: `PASSWORD_HASHERS` memakai
  `BCryptSHA256PasswordHasher` (cost 12, pre-hash SHA-256 agar password
  panjang tidak terpotong 72-byte) untuk semua password baru — termasuk
  admin. Hash PBKDF2 lama tetap bisa login dan **otomatis ter-upgrade**
  ke bcrypt pada login berikutnya
- **Standardisasi URL (anti-duplikat kanonik)**: `APPEND_SLASH = True`
  (`/bus` → 301 `/bus/`), middleware `LowercasePathMiddleware`
  (`/BUS/` → 301 `/bus/`; kode booking kapital `NT-XXXXXX` tidak disentuh),
  standar domain **tanpa www** (`PREPEND_WWW = False`; `www` → apex 301 di
  Nginx), dan paksa HTTPS via env `DJANGO_SSL_REDIRECT=1` (lapis kedua —
  redirect utama HTTP→HTTPS ada di blok Nginx, lengkap HSTS). Canonical
  selalu self-referential **tanpa parameter tracking** (`?utm_*`, `?page`
  otomatis gugur karena memakai `request.path`)
- **Structured data (JSON-LD)**: dibangun sebagai dict Python di context view,
  dirender via filter aman `jsonld` (escaping `</`, `<`, `&` — pola `json_script`
  bawaan Django) melalui `{% block schema_json %}` di `<head>`. Tipe per halaman:
  `Organization`+`LocalBusiness` (beranda: nama, logo, kontak, alamat,
  jam buka), `BreadcrumbList` dinamis (semua halaman dalam, hierarki tampil
  rapi di SERP), `BusTrip`+`FAQPage` (rute — FAQ-nya benar-benar tampil di
  halaman, syarat kepatuhan Google), `Product`+`Offer` IDR (detail mobil —
  kandidat rich result harga)
- **Canonical & slug**: `<link rel="canonical">` otomatis (dari `request.path`,
  bersih dari query string) di semua halaman; `Route` & `Vehicle` memakai
  `SlugField` unique dengan generator anti-bentrok + method `get_absolute_url()`
  yang jadi sumber tunggal tautan internal & sitemap
- Seed menyertakan 5 contoh metadata (beranda, /bus/, /rental/, /tentang/,
  /kontak/) — langsung bisa diedit di admin

### ⚡ Optimasi Core Web Vitals
- **LCP**: gambar hero WebP dua ukuran (`srcset` 900w/1600w) + `fetchpriority="high"`
  + `<link rel="preload" imagesrcset>`; gambar WebP untuk semua foto (hero 222→92KB,
  QRIS 123→7KB, mobil ±120→20-30KB); CSS non-kritis (Font Awesome, Google Fonts)
  dimuat async; preconnect ke CDN
- **CLS**: atribut `width`/`height` di semua `<img>`, `aspect-ratio` pembungkus
  gambar mobil, angka countdown `tabular-nums`
- **INP**: semua JavaScript `defer` (Bootstrap bundle + skrip kustom),
  `content-visibility: auto` untuk section di bawah lipatan
- **Server**: WhiteNoise (gzip + cache header panjang static), Nginx
  `gzip_static` + `open_file_cache` (`deploy/nginx.conf`)
- **Pipeline unggahan WebP otomatis**: setiap foto mobil & og:image yang
  diunggah otomatis diputar sesuai EXIF, di-resize (maks 1200px, og 1600px),
  dan dikonversi ke **WebP q82** — berkas asli dihapus
  (`core/img_tools.py`, lewat storage API sehingga aman untuk storage remote).
  Media lama: backfill sekali dengan `python manage.py convert_media_webp`.
  Bukti pembayaran sengaja tidak dikonversi (dokumen legal, disimpan asli).
- **Minifikasi & penggabungan (`django-compressor`)**: Bootstrap 5.3.3
  di-vendor lokal (`static/vendor/bootstrap/`, tanpa CDN jsdelivr) lalu
  digabung + diminifikasi dengan CSS/JS tema via `{% compress %}` — beranda
  hanya memuat **1 berkas CSS + 1 berkas JS** (CSS 244KB → 34KB, JS 82KB →
  24KB setelah gzip). Output di-pra-gzip otomatis
  (`COMPRESS_STORAGE = GzipCompressorFileStorage`) sehingga cocok dengan
  WhiteNoise dan `gzip_static` Nginx. `rental-form.js` sengaja di luar blok
  compress karena butuh atribut `data-*` per-request.
- **Optimasi database (anti N+1)**: semua queryset publik memakai
  `select_related` (rute+kota+bus) dan agregasi `annotate(Count)` untuk jumlah
  kursi bus — halaman rute turun dari **19 → 3 query**. Kolom filter/sortir
  terindeks: `schedule.departure_time`, `schedule.is_active`,
  `vehicle.is_available`, `vehicle.category`, `booking.status` (+ index
  komposit `schedule, travel_date` untuk cek ketersediaan kursi)
- **Caching (TTFB ~5–10 ms)**: cache backend Redis bila `REDIS_URL`
  terisi (otomatis di Docker Compose), selain itu LocMem. Level aplikasi:
  beranda `home:data` (10 mnt), jadwal per rute `route:<slug>:schedules`
  (5 mnt) — **0 query DB** saat cache hangat; level fragment: grid jadwal
  rute (`{% cache 300 %}`) dan grid armada rental (`{% cache 600 %}`);
  sitemap `cache_page(1800)`; halaman semi-statis `@cache_page(60×15)`
  (tentang, kontak, katalog rental, detail rute, robots.txt) dan otomatis
  segar saat `PageMeta` disimpan (signal). Halaman dinamis pribadi (detail
  booking & sewa) `never_cache` agar tidak bocor ke cache bersama.
- **Mode produksi (`DJANGO_DEBUG=0`)**: compressor berjalan offline —
  jalankan `DJANGO_DEBUG=0 python3 manage.py compress --force` **sebelum**
  `collectstatic` (manifest 4 blok: CSS base, JS base, seat-map, countdown).

---

<a id="quick-start"></a>

## 🚀 Menjalankan Proyek

### 1. Instalasi

```bash
cd Website-Pemesanan-Bus
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Setup database & data demo

```bash
python manage.py migrate
python manage.py seed_data          # kota, rute, bus, jadwal, mobil, akun admin
python manage.py compile_i18n       # ekstrak + kompilasi katalog ID/EN (via polib)
python manage.py runserver
```

Buka http://127.0.0.1:8000 — beranda Indonesia, http://127.0.0.1:8000/en/ untuk Inggris.

**Akun admin demo**: username `admin` · password `admin123` → http://127.0.0.1:8000/admin/
(ganti segera di produksi, atau set env `DJANGO_ADMIN_PASSWORD` sebelum seed).

Perintah lain: `python manage.py seed_data --flush` (hapus data demo),
`python manage.py test` (14 unit test).

### 2b. Alternatif: Docker Compose (PostgreSQL)

```bash
cp .env.example .env      # opsional — sesuaikan password dulu
docker compose up --build
```

Compose menjalankan dua service:

| Service | Isi | Port |
|---|---|---|
| `db` | PostgreSQL 16 + volume `pgdata` + healthcheck | `127.0.0.1:5432` |
| `web` | Django: migrate → compile_i18n → seed_data → runserver (hot-reload) | `8000` |

Proyek memakai **PostgreSQL murni** (tidak ada fallback SQLite). Di dalam
compose, host db = `db`. Tanpa Docker, jalankan PostgreSQL sendiri lalu set
env `POSTGRES_*` (lihat `.env.example`). Koneksi dari host (psql/DBeaver):
host `localhost`, user/pass `nusantar`/`nusantar`, db `nusantartrans`.

```bash
docker compose logs -f web                 # ikuti log
docker compose exec web python manage.py shell
docker compose down                        # berhenti
docker compose down -v                     # berhenti + hapus data database
```

<a id="alur-pemesanan"></a>

### 3. Alur pemesanan (untuk dicoba)

1. Beranda → cari `Jember → Surabaya` → pilih jadwal
2. Pilih kursi di denah (kursi merah = terisi) → **Lanjut Isi Data**
3. Isi nama + WhatsApp → **Buat Booking** → kode `NT-XXXXXX` terbit
4. Transfer/QRIS sesuai instruksi → unggah bukti
5. Login admin → menu *Booking tiket* → pilih booking → aksi
   **Konfirmasi pembayaran yang dipilih** → e-tiket aktif di halaman booking

---

## ⚙️ Konfigurasi

Semua konstanta bisnis ada di [`core/settings.py`](core/settings.py):

| Kunci | Arti | Default |
|---|---|---|
| `SITE_NAME` | Nama situs | `Nusantara Trans` |
| `WHATSAPP_NUMBER` | Nomor CS (format `62…`) | `6281234567890` |
| `PAYMENT_METHODS` / `PAYMENT_DETAILS` | Bank/QRIS & nomor rekening | BCA, Mandiri, QRIS |
| `PAYMENT_TIMEOUT_HOURS` | Batas waktu bayar booking | `2` jam |
| `MAX_SEATS_PER_BOOKING` | Batas kursi per transaksi | `6` |

Ganti gambar `static/img/qris-placeholder.png` dengan QRIS asli Anda, serta
rekening pada `PAYMENT_DETAILS`.

Variabel environment produksi: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`.

---

## 🌍 Terjemahan (ID / EN)

String diterjemahkan lewat kamus di [`core/translations.py`](core/translations.py)
(`TRANSLATIONS_ID` & `TRANSLATIONS_EN`). Setelah mengubah kode/template:

```bash
python manage.py compile_i18n
```

Perintah ini mengekstrak ulang semua `{% trans %}` / `gettext()` dan menulis
`locale/id/LC_MESSAGES/django.{po,mo}` + `locale/en/…`. String baru yang belum
ada kamusnya terdaftar sebagai *fallback* di output perintah — tinggal tambahkan.

---

<a id="deploy"></a>

## 🖥️ Deploy Produksi (Gunicorn + Nginx)

```bash
python manage.py migrate && python manage.py compile_i18n
python manage.py collectstatic --noinput                # 1) salin sumber ke STATIC_ROOT...
DJANGO_DEBUG=0 python manage.py compress --force        # 2) ...baru minifikasi offline (baca dari STATIC_ROOT)
gunicorn core.wsgi:application --bind 127.0.0.1:8001 --workers 3
```

> `manage.py check` gagal dengan error `core.E001` bila langkah 2 terlewat —
> gagal cepat sebelum traffic produksi menghantam halaman 500.

Konfigurasi Nginx reverse proxy lengkap (static/media/cache/gzip/HTTPS) tersedia di
[`deploy/nginx.conf`](deploy/nginx.conf). Produksi sebaiknya juga:
- Ganti `DJANGO_SECRET_KEY` & `DJANGO_DEBUG=0`
- PostgreSQL murni: sesuaikan env `POSTGRES_*` (lihat `.env.example`), `sslmode=require` di produksi
- Cache bersama: set `REDIS_URL` (otomatis di Docker Compose) — tanpa ini LocMem per-proses
- Aktifkan kembali `XFrameOptionsMiddleware` di `core/settings.py`
- Ganti password admin demo

---

## 📁 Struktur Proyek

```
├── core/                  # Settings, URL induk, halaman statis, sitemap,
│   │                      # context processor, perintah compile_i18n
│   └── translations.py    # Kamus ID & EN
├── booking/               # Tiket bus: City, Route, Bus, Seat, Schedule,
│   │                      # Booking + denah kursi + alur pembayaran
│   └── management/commands/seed_data.py
├── rental/                # Rental: Vehicle, RentalBooking
├── templates/             # Base + includes (navbar/footer/steps/kartu) + halaman
├── static/                # CSS tema, JS (seat-map, countdown, rental), gambar
├── locale/                # django.po/mo (id, en) — dihasilkan compile_i18n
├── media/                 # Unggahan runtime (bukti bayar, foto mobil) — gitignored
└── deploy/nginx.conf      # Config Nginx produksi
```

<a id="stack"></a>

## 🧰 Stack

| Lapisan | Teknologi |
|---|---|
| Bahasa | Python 3.11+ |
| Framework | Django 5.2 |
| UI | Bootstrap 5.3, Font Awesome 6.7, Plus Jakarta Sans |
| Web server | Nginx (reverse proxy) + Gunicorn + WhiteNoise |
| Database | **PostgreSQL 16 (murni)** via psycopg 3 — docker-compose tersedia; tanpa fallback SQLite |
| SEO | Open Graph, Twitter Card, sitemap.xml, robots.txt, hreflang |
| i18n | Django LocaleMiddleware + katalog gettext (ID/EN) |
| Redirect | `django.contrib.redirects` + `RedirectFallbackMiddleware` (301 dari DB) |
| Pembayaran | Transfer manual / QRIS + verifikasi admin |

---

## 🏷️ About & Kata Kunci Repository

Salin-tempel ke **GitHub → Settings → General**:

**Description (About)** — maks. 350 karakter:

> 🚌 Nusantara Trans — website pemesanan tiket bus antar kota (denah kursi interaktif, bayar QRIS, e-tiket) & rental mobil. Dibangun dengan Django 5.2 + PostgreSQL + Bootstrap 5: panel admin + grafik, SEO lengkap (JSON-LD, sitemap, topic cluster), dwibahasa ID/EN, siap deploy Docker & Nginx.

**Topics (kata kunci)**:

`django` `python` `django-app` `bus-booking` `ticket-booking` `booking-system` `car-rental` `postgresql` `bootstrap` `seo` `open-graph` `docker` `nginx` `gunicorn` `qris` `indonesia` `web-application` `i18n`
