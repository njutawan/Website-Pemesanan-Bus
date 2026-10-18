# 🚌 Nusantara Trans — Website Pemesanan Tiket Bus & Rental Mobil

Aplikasi web pemesanan **tiket bus antar kota** (dengan pemilihan kursi) dan **rental mobil**,
dibangun dengan **Python (Django)**, **Bootstrap 5**, **Font Awesome 6**, siap di-deploy
di belakang **Nginx**, dengan SEO **Open Graph** + `sitemap.xml` + `hreflang`, dan
dwibahasa **Indonesia / English**.

> Demo data: kota Jember & sekitarnya (Jawa Timur). Rute, jadwal, armada, dan mobil
> rental sudah diisi lewat perintah seed.

---

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
- Panel admin Django untuk: kota, rute, bus, jadwal, booking, mobil, sewa
- Desain responsif Bootstrap 5.3 + tema kustom (navy/oranye)

---

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

## 🖥️ Deploy Produksi (Gunicorn + Nginx)

```bash
python manage.py migrate && python manage.py compile_i18n
python manage.py collectstatic --noinput
gunicorn core.wsgi:application --bind 127.0.0.1:8001 --workers 3
```

Konfigurasi Nginx reverse proxy lengkap (static/media/cache/gzip/HTTPS) tersedia di
[`deploy/nginx.conf`](deploy/nginx.conf). Produksi sebaiknya juga:
- Ganti `DJANGO_SECRET_KEY` & `DJANGO_DEBUG=0`
- Gunakan PostgreSQL (ganti `DATABASES`)
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

## 🧰 Stack

| Lapisan | Teknologi |
|---|---|
| Bahasa | PHP *(tidak dipakai — final: Python)*, Python 3.11+ |
| Framework | Django 5.2 |
| UI | Bootstrap 5.3, Font Awesome 6.7, Plus Jakarta Sans |
| Web server | Nginx (reverse proxy) + Gunicorn |
| Database | SQLite (dev) → PostgreSQL (produksi) |
| SEO | Open Graph, Twitter Card, sitemap.xml, robots.txt, hreflang |
| i18n | Django LocaleMiddleware + katalog gettext (ID/EN) |
| Pembayaran | Transfer manual / QRIS + verifikasi admin |
