"""Uji manajemen redirect (django.contrib.redirects) & halaman inti."""
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.test import TestCase


class RedirectMiddlewareTest(TestCase):
    """RedirectFallbackMiddleware: URL lama -> 301 permanen, sisanya tetap 404."""

    @classmethod
    def setUpTestData(cls):
        cls.site = Site.objects.get_or_create(
            pk=1, defaults={'domain': 'testserver', 'name': 'test'})[0]

    def _buat(self, old, new):
        # Middleware bawaan selalu 301 (tidak ada field status_code)
        return Redirect.objects.create(site=self.site, old_path=old, new_path=new)

    def test_redirect_301(self):
        self._buat('/lama/', '/bus/')
        r = self.client.get('/lama/')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/bus/')

    def test_redirect_cocok_persis_termasuk_query(self):
        # Middleware mencocokkan full path PERSIS, termasuk query string.
        self._buat('/cari-lama/?origin=1', '/bus/')
        r = self.client.get('/cari-lama/?origin=1')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/bus/')
        # Query berbeda -> tidak cocok -> tetap 404
        r2 = self.client.get('/cari-lama/?origin=2')
        self.assertEqual(r2.status_code, 404)

    def test_path_tak_kenal_tetap_404(self):
        r = self.client.get('/tidak-ada-xyz/')
        self.assertEqual(r.status_code, 404)

    def test_url_baru_tidak_tertimpa_redirect(self):
        # Middleware hanya menyapa 404 — halaman nyata tetap 200.
        self._buat('/bus/', '/rental/')  # sengaja menabrak URL nyata
        r = self.client.get('/bus/')
        self.assertEqual(r.status_code, 200)

    def test_redirect_dari_host_lain_diabaikan(self):
        Site.objects.create(domain='situslain.com', name='lain')
        self._buat('/lama/', '/bus/')
        # Redirect terdaftar utk site lain: alihkan entri ke situs berbeda
        Redirect.objects.update(site=Site.objects.get(domain='situslain.com'))
        r = self.client.get('/lama/')
        self.assertEqual(r.status_code, 404)


class HalamanIntiTest(TestCase):
    """Asap halaman publik: semua 200 (mencegah regresi URL)."""

    def test_halaman_publik(self):
        for path in ('/', '/bus/', '/rental/', '/bus/cek-booking/',
                     '/tentang/', '/kontak/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)


class CompressOfflineManifestCheckTest(TestCase):
    """core.E001: system check gagal cepat bila urutan deploy terbalik."""

    def test_error_bila_manifest_hilang(self):
        from unittest.mock import patch
        from django.test import override_settings
        from core.checks import compress_offline_manifest
        with override_settings(DEBUG=False, COMPRESS_OFFLINE=True), \
                patch('compressor.storage.default_offline_manifest_storage') as st:
            st.exists.return_value = False
            errors = compress_offline_manifest(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'core.E001')
        self.assertIn('compress', errors[0].hint)

    def test_ok_bila_manifest_ada_atau_debug(self):
        from unittest.mock import patch
        from django.test import override_settings
        from core.checks import compress_offline_manifest
        with override_settings(DEBUG=False, COMPRESS_OFFLINE=True), \
                patch('compressor.storage.default_offline_manifest_storage') as st:
            st.exists.return_value = True
            self.assertEqual(compress_offline_manifest(None), [])
        # DEBUG=True -> check dilewati
        with override_settings(DEBUG=True, COMPRESS_OFFLINE=False):
            self.assertEqual(compress_offline_manifest(None), [])


class SEOTest(TestCase):
    """robots.txt dinamis, sitemap model-query, PageMeta, canonical, get_absolute_url."""

    def setUp(self):
        # cache_page tidak ikut rollback DB — bersihkan antar test
        from django.core.cache import cache
        cache.clear()

    @classmethod
    def setUpTestData(cls):
        from booking.models import City, Route
        from rental.models import Vehicle
        a = City.objects.create(name='Kota A', slug='kota-a')
        b = City.objects.create(name='Kota B', slug='kota-b')
        cls.route = Route.objects.create(
            origin=a, destination=b, distance_km=100, duration_minutes=120)
        cls.vehicle = Vehicle.objects.create(
            name='Toyota Avanza', slug='avanza', category='MPV',
            year=2022, seats=7, price_per_day=350000)

    def test_robots_txt_dinamis_menunjuk_sitemap(self):
        r = self.client.get('/robots.txt')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Sitemap: http://testserver/sitemap.xml')
        self.assertContains(r, 'Disallow: /admin/')

    def test_sitemap_berisi_url_model_dengan_lastmod(self):
        r = self.client.get('/sitemap.xml')
        self.assertEqual(r.status_code, 200)
        xml = r.content.decode()
        self.assertIn(self.route.get_absolute_url(), xml)
        self.assertIn(self.vehicle.get_absolute_url(), xml)
        self.assertIn('<lastmod>', xml)
        self.assertIn('<priority>0.9</priority>', xml)  # /bus/ & /rental/ statis

    def test_get_absolute_url(self):
        self.assertEqual(self.route.get_absolute_url(), '/bus/rute/kota-a-kota-b/')
        self.assertEqual(self.vehicle.get_absolute_url(), '/rental/mobil/avanza/')

    def test_pagemeta_menimpa_default_dan_fallback_ke_en(self):
        from core.models import PageMeta
        PageMeta.objects.create(
            path='/bus/', title='Judul Khusus Bus',
            description='Deskripsi khusus halaman bus.')
        html = self.client.get('/bus/').content.decode()
        self.assertIn('Judul Khusus Bus', html)
        self.assertIn('Deskripsi khusus halaman bus.', html)
        # baris tanpa prefiks berlaku juga untuk /en/
        html_en = self.client.get('/en/bus/').content.decode()
        self.assertIn('Judul Khusus Bus', html_en)

    def test_pagemeta_prefiks_en_menang_di_halaman_en(self):
        from core.models import PageMeta
        PageMeta.objects.create(path='/bus/', title='Judul ID')
        PageMeta.objects.create(path='/en/bus/', title='Custom EN title')
        self.assertIn('Custom EN title', self.client.get('/en/bus/').content.decode())
        self.assertIn('Judul ID', self.client.get('/bus/').content.decode())

    def test_pagemeta_noindex_dan_og_image(self):
        from core.models import PageMeta
        PageMeta.objects.create(
            path='/tentang/', noindex=True, og_image='meta/og.png')
        html = self.client.get('/tentang/').content.decode()
        self.assertIn('noindex', html)
        self.assertIn('og:image', html)

    def test_canonical_tag_pada_semua_halaman(self):
        html = self.client.get('/tentang/').content.decode()
        self.assertIn('rel="canonical" href="http://testserver/tentang/"', html)
        html = self.client.get('/').content.decode()
        self.assertIn('rel="canonical" href="http://testserver/"', html)


def _extract_jsonld(html):
    """Ambil & parse semua blok <script type="application/ld+json">."""
    import json
    import re
    bloks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [json.loads(b) for b in bloks]


class JSONLDTest(TestCase):
    """Structured data: Organization/LocalBusiness, BreadcrumbList, BusTrip,
    FAQPage, Product — semua JSON valid dari context view."""

    @classmethod
    def setUpTestData(cls):
        from booking.models import Bus, City, Route, Schedule
        from rental.models import Vehicle
        a = City.objects.create(name='Kota A', slug='kota-a')
        b = City.objects.create(name='Kota B', slug='kota-b')
        cls.route = Route.objects.create(
            origin=a, destination=b, distance_km=100, duration_minutes=120)
        bus = Bus.objects.create(
            code='NT-TEST', name='Bus Uji', plate_number='E 9000 UJI')
        Schedule.objects.create(
            route=cls.route, bus=bus, departure_time='07:30',
            arrival_time='09:30', price=150000)
        cls.vehicle = Vehicle.objects.create(
            name='Toyota Avanza', slug='avanza', category='MPV',
            year=2022, seats=7, price_per_day=350000, description='MPV nyaman.')

    def _types(self, url):
        data = _extract_jsonld(self.client.get(url).content.decode())
        types = []
        for d in data:
            t = d.get('@type')
            types.extend(t if isinstance(t, list) else [t])
        return data, types

    def test_home_local_business(self):
        data, types = self._types('/')
        self.assertIn('LocalBusiness', types)
        lb = next(d for d in data if 'LocalBusiness' in str(d.get('@type')))
        self.assertEqual(lb['name'], 'Nusantara Trans')
        self.assertIn('logo', lb)
        self.assertIn('openingHoursSpecification', lb)
        self.assertIn('contactPoint', lb)

    def test_breadcrumb_list_dinamis(self):
        data, types = self._types('/bus/rute/kota-a-kota-b/')
        self.assertIn('BreadcrumbList', types)
        bc = next(d for d in data if d['@type'] == 'BreadcrumbList')
        self.assertEqual(len(bc['itemListElement']), 3)
        self.assertEqual(bc['itemListElement'][0]['name'], 'Beranda')
        self.assertIn('item', bc['itemListElement'][1])  # URL absolut
        self.assertNotIn('item', bc['itemListElement'][2])  # halaman saat ini

    def test_route_bustrip_dan_faqpage(self):
        data, types = self._types('/bus/rute/kota-a-kota-b/')
        self.assertIn('BusTrip', types)
        self.assertIn('FAQPage', types)
        faq = next(d for d in data if d['@type'] == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 3)
        # FAQ harus juga terlihat di halaman (syarat kepatuhan Google)
        html = self.client.get('/bus/rute/kota-a-kota-b/').content.decode()
        self.assertIn('accordion', html)

    def test_vehicle_product_offer(self):
        data, types = self._types('/rental/mobil/avanza/')
        self.assertIn('Product', types)
        prod = next(d for d in data if d['@type'] == 'Product')
        self.assertEqual(prod['offers']['priceCurrency'], 'IDR')
        self.assertEqual(prod['offers']['price'], '350000')
        self.assertIn('/media/vehicles/', prod['image'])


class URLNormalizationTest(TestCase):
    """Standardisasi URL: trailing slash, huruf kecil, canonical bebas utm."""

    def test_tanpa_slash_redirect_301(self):
        r = self.client.get('/bus')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/bus/')

    def test_path_kapital_redirect_301_ke_kecil(self):
        r = self.client.get('/BUS/')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/bus/')
        r = self.client.get('/Tentang/?utm_source=ig')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], '/tentang/?utm_source=ig')  # query utuh

    def test_kode_booking_kapital_tidak_diredirect(self):
        # path resolve (kode NT-XXXXXX memang kapital) -> lewat ke view -> 404
        r = self.client.get('/bus/booking/NT-ABC123/')
        self.assertEqual(r.status_code, 404)
        self.assertNotIn('Location', r)

    def test_canonical_bebas_parameter_tracking(self):
        html = self.client.get('/tentang/?utm_source=ig&utm_campaign=x&page=3').content.decode()
        self.assertIn('rel="canonical" href="http://testserver/tentang/"', html)

    def test_setting_standar(self):
        from django.conf import settings
        self.assertTrue(settings.APPEND_SLASH)
        self.assertFalse(settings.PREPEND_WWW)
        self.assertFalse(settings.SECURE_SSL_REDIRECT)  # default env: mati (preview HTTP)


class ImagePipelineTest(TestCase):
    """Konversi otomatis unggahan -> WebP (resize, EXIF, hapus asli)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import tempfile
        cls._media = tempfile.mkdtemp()
        from django.test import override_settings
        cls._enable = override_settings(MEDIA_ROOT=cls._media)
        cls._enable.enable()

    @classmethod
    def tearDownClass(cls):
        cls._enable.disable()
        super().tearDownClass()

    @staticmethod
    def _jpg(width=2000, height=1200, color=(200, 30, 30)):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = io.BytesIO()
        Image.new('RGB', (width, height), color).save(buf, 'JPEG', quality=90)
        return SimpleUploadedFile('uji-foto.jpg', buf.getvalue(), 'image/jpeg')

    def test_upload_jpg_otomatis_webp_dan_resize(self):
        from django.core.files.storage import default_storage
        from rental.models import Vehicle
        v = Vehicle.objects.create(
            name='Mobil Uji', slug='mobil-uji', category='MPV', year=2023,
            seats=7, price_per_day=300000, image=self._jpg())
        v.refresh_from_db()
        self.assertTrue(v.image.name.endswith('.webp'))
        self.assertTrue(default_storage.exists(v.image.name))
        self.assertFalse(default_storage.exists('uji-foto.jpg'))  # asli dihapus
        from PIL import Image
        with default_storage.open(v.image.name) as f:
            w, _ = Image.open(f).size
        self.assertLessEqual(w, 1200)  # 2000px di-resize

    def test_upload_webp_tidak_disentuh(self):
        import io
        from PIL import Image
        from django.core.files.base import ContentFile
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rental.models import Vehicle
        buf = io.BytesIO()
        Image.new('RGB', (300, 200), (10, 120, 60)).save(buf, 'WEBP')
        v = Vehicle.objects.create(
            name='Mobil WebP', slug='mobil-webp', category='SUV', year=2023,
            seats=5, price_per_day=400000,
            image=SimpleUploadedFile('langsung.webp', buf.getvalue(), 'image/webp'))
        v.refresh_from_db()
        self.assertTrue(v.image.name.endswith('langsung.webp'))

    def test_pagemeta_og_image_juga_dikonversi(self):
        from django.core.files.storage import default_storage
        from core.models import PageMeta
        pm = PageMeta.objects.create(
            path='/uji-og/', og_image=self._jpg(width=2400, height=1260))
        pm.refresh_from_db()
        self.assertTrue(pm.og_image.name.endswith('.webp'))
        self.assertFalse(default_storage.exists('uji-foto.jpg'))


class PerformanceTest(TestCase):
    """Optimasi DB & cache: anti N+1, db_index, cache_page, popular routes."""

    @classmethod
    def setUpTestData(cls):
        from booking.models import Bus, City, Route, Schedule
        from rental.models import Vehicle
        a = City.objects.create(name='Kota A', slug='kota-a')
        b = City.objects.create(name='Kota B', slug='kota-b')
        cls.route = Route.objects.create(
            origin=a, destination=b, distance_km=100, duration_minutes=120)
        for i in range(1, 4):  # 3 jadwal -> N+1 lama: 3x COUNT + 6x City
            bus = Bus.objects.create(
                code=f'NT-00{i}', name=f'Bus {i}', plate_number=f'E 800{i} XX')
            Schedule.objects.create(
                route=cls.route, bus=bus, departure_time=f'0{i}:00',
                arrival_time=f'0{i+2}:00', price=100000 + i * 1000)
        cls.vehicle = Vehicle.objects.create(
            name='Mobil Kinerja', slug='mobil-kinerja', category='MPV',
            year=2023, seats=7, price_per_day=300000)

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_route_detail_tanpa_n_plus_1(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.client.get('/bus/rute/kota-a-kota-b/').status_code, 200)
        # Sebelum optimasi: 19 query (COUNT kursi per bus + City per baris).
        # Sesudah: <=5 query — agregasi & relasi digabung via annotate+select_related.
        self.assertLessEqual(len(ctx.captured_queries), 5)
        sql = ' '.join(q['sql'] for q in ctx.captured_queries)
        self.assertNotIn('SELECT COUNT(*) FROM "booking_seat"', sql)  # bukan COUNT per bus
        self.assertIn('bus_seat_count', sql)       # hasil COUNT digabung 1 query
        self.assertIn('INNER JOIN "booking_city"', sql)  # City via join

    def test_kolom_filter_memiliki_index(self):
        from booking.models import Booking, Schedule
        from rental.models import Vehicle
        self.assertTrue(Schedule._meta.get_field('departure_time').db_index)
        self.assertTrue(Schedule._meta.get_field('is_active').db_index)
        self.assertTrue(Vehicle._meta.get_field('is_available').db_index)
        self.assertTrue(Booking._meta.get_field('status').db_index)
        names = [ix.name for ix in Booking._meta.indexes]
        self.assertIn('booking_sched_date_ix', names)

    def test_cache_page_header_halaman_semi_statis(self):
        for url in ('/tentang/', '/kontak/', '/rental/', '/bus/rute/kota-a-kota-b/'):
            r = self.client.get(url)
            self.assertIn('max-age=900', r['Cache-Control'], url)

    def test_bus_memuat_rute_populer_dari_cache(self):
        html = self.client.get('/bus/').content.decode()
        self.assertIn('Kota A', html)  # kartu rute populer kini terisi
        # kedua kali: tetap 200 (dari cache)
        self.assertEqual(self.client.get('/bus/').status_code, 200)


class PasswordHashingTest(TestCase):
    """Keamanan password: bcrypt utama, hash lama PBKDF2 auto-upgrade."""

    def test_password_baru_terhash_bcrypt(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        u = User.objects.create_user('budi', password='RahasiaKuat#2026')
        self.assertTrue(u.password.startswith('bcrypt_sha256$'))
        self.assertIn('$12$', u.password)  # cost factor bcrypt
        self.assertTrue(u.check_password('RahasiaKuat#2026'))
        self.assertFalse(u.check_password('tebakan-salah'))

    def test_superuser_admin_pakai_bcrypt(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_superuser(
            'adminx', email='a@x.id', password='AdminPass#1')
        admin = User.objects.get(username='adminx')
        self.assertTrue(admin.password.startswith('bcrypt_sha256$'))

    def test_hash_pbkdf2_lama_masih_login_dan_auto_upgrade(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.hashers import PBKDF2PasswordHasher
        User = get_user_model()
        u = User.objects.create_user('sri', password='x')
        hasher = PBKDF2PasswordHasher()
        u.password = hasher.encode('RahasiaLama#1', hasher.salt())
        u.save()
        self.assertTrue(u.password.startswith('pbkdf2_sha256$'))
        # login sukses dengan hash lama...
        self.assertTrue(self.client.login(username='sri', password='RahasiaLama#1'))
        # ...dan hash otomatis di-upgrade ke bcrypt
        u.refresh_from_db()
        self.assertTrue(u.password.startswith('bcrypt_sha256$'))
