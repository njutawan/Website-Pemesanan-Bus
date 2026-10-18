"""
Seed data demo: kota, rute, armada bus + kursi, jadwal, mobil rental, admin.

Jalankan: python manage.py seed_data           (idempotent, aman diulang)
          python manage.py seed_data --flush   (hapus data demo dulu)
"""
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from booking.models import Bus, City, Route, Schedule
from rental.models import Vehicle

CITIES = [
    # nama, provinsi, populer
    ('Jember', 'Jawa Timur', True),
    ('Surabaya', 'Jawa Timur', True),
    ('Malang', 'Jawa Timur', True),
    ('Banyuwangi', 'Jawa Timur', False),
    ('Yogyakarta', 'DI Yogyakarta', True),
    ('Semarang', 'Jawa Tengah', False),
    ('Jakarta', 'DKI Jakarta', True),
    ('Bandung', 'Jawa Barat', False),
    ('Denpasar', 'Bali', True),
]

BUSES = [
    # kode, nama, plat, kelas, baris, fasilitas
    ('NT-01', 'Nusantara Ekonomi', 'N 1234 AB', 'EKONOMI', 10,
     'AC, Reclining Seat, Colokan USB'),
    ('NT-02', 'Nusantara AC', 'N 2345 AB', 'AC', 10,
     'AC, WiFi, Colokan USB, Air Mineral'),
    ('NT-03', 'Nusantara Eksekutif', 'N 3456 AB', 'EKSEKUTIF', 10,
     'AC, WiFi, Toilet, Snack, Selimut'),
    ('NT-04', 'Nusantara Sleeper', 'N 4567 AB', 'SLEEPER', 8,
     'AC, Kabin Tidur, Selimut, Toilet, WiFi'),
    ('NT-05', 'Nusantara Eksekutif 2', 'N 5678 AB', 'EKSEKUTIF', 10,
     'AC, WiFi, Toilet, Snack'),
    ('NT-06', 'Nusantara AC 2', 'N 6789 AB', 'AC', 10,
     'AC, WiFi, Colokan USB'),
]

ROUTES = [
    # asal, tujuan, km, menit, [(jam_berangkat, jam_tiba, kelas, harga), ...]
    ('jember', 'surabaya', 190, 240, [
        ('05:30', '09:30', 'EKONOMI', 120000),
        ('08:00', '12:00', 'AC', 150000),
        ('15:00', '19:00', 'EKSEKUTIF', 175000),
        ('21:00', '01:00', 'SLEEPER', 210000),
    ]),
    ('surabaya', 'jember', 190, 240, [
        ('06:00', '10:00', 'EKONOMI', 120000),
        ('14:00', '18:00', 'AC', 150000),
        ('21:30', '01:30', 'EKSEKUTIF', 175000),
    ]),
    ('jember', 'malang', 180, 240, [
        ('06:00', '10:00', 'EKONOMI', 100000),
        ('13:00', '17:00', 'AC', 135000),
        ('20:00', '00:00', 'EKSEKUTIF', 155000),
    ]),
    ('malang', 'jember', 180, 240, [
        ('06:30', '10:30', 'EKONOMI', 100000),
        ('14:30', '18:30', 'AC', 135000),
    ]),
    ('jember', 'banyuwangi', 110, 150, [
        ('07:00', '09:30', 'EKONOMI', 60000),
        ('16:00', '18:30', 'AC', 85000),
    ]),
    ('banyuwangi', 'jember', 110, 150, [
        ('07:30', '10:00', 'EKONOMI', 60000),
        ('16:30', '19:00', 'AC', 85000),
    ]),
    ('jember', 'yogyakarta', 400, 480, [
        ('06:30', '14:30', 'AC', 275000),
        ('17:00', '01:00', 'EKSEKUTIF', 310000),
        ('21:00', '05:00', 'SLEEPER', 345000),
    ]),
    ('yogyakarta', 'jember', 400, 480, [
        ('07:00', '15:00', 'AC', 275000),
        ('20:00', '04:00', 'SLEEPER', 345000),
    ]),
    ('jember', 'semarang', 490, 540, [
        ('07:00', '16:00', 'AC', 315000),
        ('19:00', '04:00', 'EKSEKUTIF', 355000),
    ]),
    ('semarang', 'jember', 490, 540, [
        ('08:00', '17:00', 'AC', 315000),
        ('19:30', '04:30', 'EKSEKUTIF', 355000),
    ]),
    ('jember', 'jakarta', 780, 840, [
        ('05:00', '19:00', 'AC', 395000),
        ('14:00', '04:00', 'EKSEKUTIF', 435000),
        ('18:00', '08:00', 'SLEEPER', 470000),
    ]),
    ('jakarta', 'jember', 780, 840, [
        ('06:00', '20:00', 'AC', 395000),
        ('15:00', '05:00', 'EKSEKUTIF', 435000),
        ('19:00', '09:00', 'SLEEPER', 470000),
    ]),
    ('jember', 'bandung', 920, 960, [
        ('06:00', '22:00', 'AC', 455000),
        ('16:00', '08:00', 'EKSEKUTIF', 495000),
    ]),
    ('bandung', 'jember', 920, 960, [
        ('07:00', '23:00', 'AC', 455000),
        ('17:00', '09:00', 'EKSEKUTIF', 495000),
    ]),
    ('jember', 'denpasar', 400, 540, [
        ('07:00', '16:00', 'AC', 185000),
        ('20:00', '05:00', 'SLEEPER', 255000),
        ('21:00', '06:00', 'EKSEKUTIF', 225000),
    ]),
    ('denpasar', 'jember', 400, 540, [
        ('08:00', '17:00', 'AC', 185000),
        ('21:00', '06:00', 'SLEEPER', 255000),
    ]),
]

VEHICLES = [
    # nama, kategori, tahun, transmisi, kursi, harga/hari, sopir/hari, gambar, deskripsi
    ('Toyota Innova Zenix', 'MPV', 2023, 'MATIC', 7, 550000, 250000,
     'vehicles/toyota-innova-zenix.jpg',
     'MPV premium dengan mesin hybrid, interior kulit, dan bagasi luas. '
     'Nyaman untuk keluarga maupun perjalanan dinas jarak jauh.'),
    ('Toyota Avanza', 'MPV', 2022, 'MATIC', 7, 400000, 250000,
     'vehicles/toyota-avanza.jpg',
     'Mobil keluaran paling populer untuk perjalanan keluarga. IRIT, '
     'ringan dikendarai, dan mudah diparkir di perkotaan. Pilihan utama '
     'rental mobil dari Jember ke Surabaya, Malang, dan Banyuwangi.'),
    ('Mitsubishi Pajero Sport', 'SUV', 2022, 'MATIC', 7, 950000, 300000,
     'vehicles/pajero-sport.jpg',
     'SUV diesel tangguh untuk medan berat maupun tol. Cocok untuk trip '
     'gunung, pantai selatan, hingga luar kota.'),
    ('Toyota HiAce Premio', 'VAN', 2023, 'MANUAL', 14, 1250000, 350000,
     'vehicles/hiace-premio.jpg',
     'Van premium 14 kursi dengan kabin tinggi, AC ganda, dan USB di tiap '
     'baris. Favorit untuk rombongan keluarga & perusahaan.'),
    ('Isuzu Elf NLR Microbus', 'VAN', 2021, 'MANUAL', 16, 1400000, 350000,
     'vehicles/isuzu-elf.jpg',
     'Microbus 16 kursi yang tangguh. Pilihan hemat untuk akad nikah, '
     'ziarah, dan wisata rombongan.'),
    ('Bus Kecil 31 Kursi', 'BUS', 2020, 'MANUAL', 31, 2500000, 500000,
     'vehicles/bus-kecil.jpg',
     'Bus kecil untuk rombongan besar: karaoke, toilet, dan bagasi luas. '
     'Sertifikasi KIR & uji berkala. Alternatif nyaman tiket bus untuk '
     'rombongan Surabaya, Denpasar, dan Yogyakarta.'),
]

# Redirect lama -> baru (django.contrib.redirects via RedirectFallbackMiddleware).
# Catatan: middleware bawaan Django SELALU memancarkan 301 (pindah permanen —
# terbaik untuk SEO). Hanya berlaku untuk URL yang TIDAK dikenai view apa pun
# (aman, tidak akan menimpa halaman nyata).
PAGE_META = [
    # (path, title, description)
    ('/', 'Nusantara Trans — Tiket Bus Online & Rental Mobil',
     'Pesan tiket bus antar kota dan sewa mobil dengan mudah, aman, dan harga '
     'terbaik. Pilih kursi, bayar via transfer/QRIS, e-tiket instan.'),
    ('/bus/', 'Cari & Pesan Tiket Bus Antar Kota — Nusantara Trans',
     'Jadwal bus lengkap antar kota Jawa. Pilih kursi favorit, bayar transfer '
     'atau QRIS, e-tiket langsung terbit.'),
    ('/bus/rute/', 'Semua Rute Bus Antar Kota — Nusantara Trans',
     'Daftar lengkap semua rute bus antar kota: jadwal keberangkatan, durasi '
     'perjalanan, dan harga tiket mulai per kelas armada.'),
    ('/rental/', 'Rental Mobil Lepas Kunci & Dengan Sopir — Nusantara Trans',
     'Sewa mobil harian: MPV, SUV, hingga minibus. Harga transparan per hari, '
     'bebas pilih lepas kunci atau dengan sopir.'),
    ('/tentang/', 'Tentang Kami — Nusantara Trans',
     'Kenali Nusantara Trans: layanan transportasi antar kota dan rental mobil '
     'yang mengutamakan kenyamanan serta keselamatan.'),
    ('/kontak/', 'Kontak & Bantuan — Nusantara Trans',
     'Hubungi tim Nusantara Trans untuk bantuan pemesanan tiket bus dan rental '
     'mobil: email, telepon, dan WhatsApp.'),
]

REDIRECTS = [
    # (path lama, path baru)
    ('/tiket/', '/bus/'),
    ('/sewa-mobil/', '/rental/'),
    ('/travel/', '/bus/'),
    ('/jadwal/', '/bus/'),
    ('/cek/', '/bus/cek-booking/'),
    ('/tentang-kami/', '/tentang/'),
    ('/hubungi/', '/kontak/'),
]


class Command(BaseCommand):
    help = 'Mengisi data demo: kota, rute, bus, jadwal, mobil rental, akun admin.'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Hapus data demo sebelum mengisi ulang.')

    @staticmethod
    def _pick_bus(bus_class, counter):
        buses = [b for b in BUSES if b[3] == bus_class]
        kode = buses[counter % len(buses)][0]
        return Bus.objects.get(code=kode)

    def handle(self, *args, **options):
        if options['flush']:
            Schedule.objects.all().delete()
            Route.objects.all().delete()
            Bus.objects.all().delete()
            City.objects.all().delete()
            Vehicle.objects.all().delete()
            self.stdout.write(self.style.WARNING('Data demo dihapus.'))

        # ---- Kota ----
        cities = {}
        for name, province, popular in CITIES:
            from django.utils.text import slugify
            city, _ = City.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name), 'province': province,
                          'is_popular': popular},
            )
            cities[name] = city
        self.stdout.write(self.style.SUCCESS(f'✔ Kota: {City.objects.count()}'))

        # ---- Bus + kursi otomatis ----
        for kode, nama, plat, kelas, rows, fasilitas in BUSES:
            Bus.objects.get_or_create(
                code=kode,
                defaults={'name': nama, 'plate_number': plat, 'bus_class': kelas,
                          'rows': rows, 'amenities': fasilitas},
            )
        self.stdout.write(self.style.SUCCESS(f'✔ Bus: {Bus.objects.count()}'))

        # ---- Rute + jadwal ----
        class_counter = {}
        n_schedules = 0
        for origin_slug, dest_slug, km, minutes, jadwal in ROUTES:
            origin = City.objects.get(slug=origin_slug)
            dest = City.objects.get(slug=dest_slug)
            route, _ = Route.objects.get_or_create(
                origin=origin, destination=dest,
                defaults={'distance_km': km, 'duration_minutes': minutes},
            )
            for dep, arr, kelas, harga in jadwal:
                key = kelas
                class_counter[key] = class_counter.get(key, 0) + 1
                bus = self._pick_bus(kelas, class_counter[key] - 1)
                _, created = Schedule.objects.get_or_create(
                    route=route, bus=bus, departure_time=dep,
                    defaults={'arrival_time': arr, 'price': harga},
                )
                n_schedules += int(created)
        self.stdout.write(self.style.SUCCESS(
            f'✔ Rute: {Route.objects.count()} | Jadwal baru: {n_schedules} '
            f'(total {Schedule.objects.count()})'))

        # ---- Mobil rental (foto demo disalin dari static/img/vehicles) ----
        import shutil

        from django.conf import settings

        src_dir = settings.BASE_DIR / 'static' / 'img' / 'vehicles'
        dst_dir = settings.MEDIA_ROOT / 'vehicles'
        dst_dir.mkdir(parents=True, exist_ok=True)
        for nama, kategori, tahun, transmisi, kursi, harga, sopir, gambar, deskripsi in VEHICLES:
            src = src_dir / Path(gambar).name
            dst = dst_dir / Path(gambar).name
            if src.exists() and not dst.exists():
                shutil.copy(src, dst)
            Vehicle.objects.get_or_create(
                name=nama,
                defaults={
                    'category': kategori, 'year': tahun, 'transmission': transmisi,
                    'seats': kursi, 'price_per_day': harga,
                    'driver_fee_per_day': sopir, 'image': gambar,
                    'description': deskripsi,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'✔ Mobil rental: {Vehicle.objects.count()}'))

        # ---- Admin ----
        # TIDAK ada password default. Di produksi (DEBUG=0) env wajib diisi;
        # di pengembangan password acak dibuat & ditampilkan sekali.
        User = get_user_model()
        username = os.environ.get('DJANGO_ADMIN_USERNAME', 'admin').strip()
        email = os.environ.get('DJANGO_ADMIN_EMAIL',
                               'admin@nusantartrans.example').strip()
        existing = User.objects.filter(username=username).first()
        if existing is None:
            password, generated = _resolve_admin_password()
            User.objects.create_superuser(username, email=email, password=password)
            if generated:
                self.stdout.write(self.style.WARNING(
                    f'✔ Admin dibuat: username={username} password={password} '
                    '— HANYA ditampilkan sekali. Simpan di password manager.'))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'✔ Admin dibuat: username={username} '
                    '(password dari DJANGO_ADMIN_PASSWORD).'))
        else:
            if existing.check_password('admin123'):
                self.stdout.write(self.style.ERROR(
                    '✖ Admin masih memakai password default "admin123"! '
                    'Jalankan: python manage.py changepassword '
                    f'{username}'))
            else:
                self.stdout.write('• Admin sudah ada, dilewati.')

        # ---- Redirect 301 (SEO) + record Site ----
        from django.contrib.redirects.models import Redirect
        from django.contrib.sites.models import Site
        site, _ = Site.objects.get_or_create(
            pk=getattr(settings, 'SITE_ID', 1),
            defaults={'domain': 'localhost:8000', 'name': 'Nusantara Trans'},
        )
        if site.domain == 'example.com':
            site.domain = 'localhost:8000'
            site.name = 'Nusantara Trans'
            site.save()
        n_red = 0
        for old_path, new_path in REDIRECTS:
            _, created = Redirect.objects.update_or_create(
                site=site, old_path=old_path,
                defaults={'new_path': new_path},
            )
            n_red += int(created)
        self.stdout.write(self.style.SUCCESS(
            f'✔ Redirect: {Redirect.objects.count()} aturan '
            f'({n_red} baru)'))

        from core.models import PageMeta, SeoKeyword
        for phrase, url in [('tiket bus', '/bus/'),
                            ('rental mobil', '/rental/'),
                            ('sewa mobil', '/rental/')]:
            SeoKeyword.objects.update_or_create(
                phrase=phrase, defaults={'url': url})
        self.stdout.write(self.style.SUCCESS(
            f'✔ SEO: {SeoKeyword.objects.count()} kata kunci + '
            f'{PageMeta.objects.count()} metadata halaman'))
        for path, title, description in PAGE_META:
            PageMeta.objects.update_or_create(
                path=path, defaults={'title': title, 'description': description})
        self.stdout.write(self.style.SUCCESS(
            f'✔ SEO: {PageMeta.objects.count()} metadata halaman'))

        # Foto demo disalin sebagai .jpg; hasilkan varian WebP-nya agar
        # <source srcset="...|webp_url"> tidak 404. Konversi juga
        # menjangkau kendaraan lama yang luput dari hook konversi model
        # (mis. baris yang sudah ada tidak ter-save ulang oleh get_or_create).
        call_command('convert_media_webp', stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS('Seed selesai. 🚍'))


WEAK_ADMIN_PASSWORDS = {
    'admin', 'admin123', 'password', 'password123', '12345678',
    '123456789', 'qwerty123', 'nusantar', 'changeme', 'letmein123',
}


def _resolve_admin_password():
    """(password, generated). Produksi wajib env; dev boleh acak."""
    password = os.environ.get('DJANGO_ADMIN_PASSWORD', '')
    if password:
        if len(password) < 12 or password.lower() in WEAK_ADMIN_PASSWORDS:
            raise CommandError(
                'DJANGO_ADMIN_PASSWORD terlalu lemah (min. 12 karakter, '
                'bukan password umum).')
        return password, False
    if not (settings.DEBUG or getattr(settings, 'RUNNING_TESTS', False)):
        raise CommandError(
            'DJANGO_ADMIN_PASSWORD wajib diisi saat DEBUG=0. '
            'Gunakan: openssl rand -base64 24')
    return secrets.token_urlsafe(18), True
