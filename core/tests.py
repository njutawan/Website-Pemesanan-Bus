from django.test import TestCase, override_settings
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
        self.assertEqual(self.route.get_absolute_url(), '/bus/rute/dari/kota-a/kota-b/')
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


class PageMetaCacheTest(TestCase):
    """SEO context processor: PageMeta dimuat 1 query per TTL, bukan per request."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)

    def test_cache_dingin_1_query_lalu_0_dan_segar_setelah_simpan(self):
        from django.test import RequestFactory
        from core.context_processors import seo
        from core.models import PageMeta
        pm = PageMeta.objects.create(path='/bus/', title='Judul ID')
        PageMeta.objects.create(path='/en/bus/', title='Custom EN title')
        factory = RequestFactory()

        # Cache dingin: satu query memuat seluruh peta PageMeta.
        with self.assertNumQueries(1):
            ctx_en = seo(factory.get('/en/bus/'))
        self.assertEqual(ctx_en['page_meta'].title, 'Custom EN title')

        # Request berikutnya — path lain maupun tanpa PageMeta — 0 query.
        with self.assertNumQueries(0):
            ctx_id = seo(factory.get('/bus/'))
            ctx_missing = seo(factory.get('/path-tanpa-meta/'))
        self.assertEqual(ctx_id['page_meta'].title, 'Judul ID')
        self.assertIsNone(ctx_missing['page_meta'])

        # Simpan/hapus via model memberi sinyal invalidasi cache
        # (core.apps) -> request berikutnya memuat ulang sekali.
        pm.title = 'Judul Baru'
        pm.save()
        with self.assertNumQueries(1):
            self.assertEqual(
                seo(factory.get('/bus/'))['page_meta'].title, 'Judul Baru')
        pm.delete()
        with self.assertNumQueries(1):
            self.assertIsNone(seo(factory.get('/bus/'))['page_meta'])


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

    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # LocMem tidak ikut rollback DB antar test class

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
        data, types = self._types('/bus/rute/dari/kota-a/kota-b/')
        self.assertIn('BreadcrumbList', types)
        bc = next(d for d in data if d['@type'] == 'BreadcrumbList')
        self.assertEqual(len(bc['itemListElement']), 5)  # beranda..semua rute..pillar..artikel
        self.assertEqual(bc['itemListElement'][0]['name'], 'Beranda')
        self.assertIn('item', bc['itemListElement'][1])  # URL absolut
        self.assertIn('item', bc['itemListElement'][3])  # URL pillar
        self.assertNotIn('item', bc['itemListElement'][4])  # halaman saat ini

    def test_route_bustrip_dan_faqpage(self):
        data, types = self._types('/bus/rute/dari/kota-a/kota-b/')
        self.assertIn('BusTrip', types)
        self.assertIn('FAQPage', types)
        faq = next(d for d in data if d['@type'] == 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 3)
        # FAQ harus juga terlihat di halaman (syarat kepatuhan Google)
        html = self.client.get('/bus/rute/dari/kota-a/kota-b/').content.decode()
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
        # path resolve (kode NT-XXXXXXXX memang kapital) -> lewat ke view -> 404
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
        from django.core.cache import cache
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        cache.clear()  # deterministik: hitung dgn cache istilah dingin
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.client.get('/bus/rute/dari/kota-a/kota-b/').status_code, 200)
        # Sebelum optimasi: 19 query (COUNT kursi per bus + City per baris).
        # Sesudah: <=6 query — agregasi digabung (annotate+select_related);
        # +2 dgn cache dingin: peta kata kunci SEO & pillar kota (cache 600s,
        # render berikutnya 0 query tambahan).
        self.assertLessEqual(len(ctx.captured_queries), 6)
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
        for url in ('/tentang/', '/kontak/', '/rental/', '/bus/rute/dari/kota-a/kota-b/'):
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


class SecurityHeadersTest(TestCase):
    """Header keamanan & bot: nosniff, gzip, X-Robots-Tag, frame DENY produksi."""

    def test_nosniff_selalu_aktif(self):
        r = self.client.get('/')
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r['Referrer-Policy'], 'strict-origin-when-cross-origin')

    def test_gzip_middleware(self):
        r = self.client.get('/', HTTP_ACCEPT_ENCODING='gzip, deflate, br')
        self.assertEqual(r['Content-Encoding'], 'gzip')
        self.assertIn('Accept-Encoding', r['Vary'])

    def test_x_robots_admin_dan_media(self):
        r = self.client.get('/admin/login/')
        self.assertEqual(r['X-Robots-Tag'], 'noindex, nofollow')
        r = self.client.get('/media/vehicles/toyota-avanza.webp')
        self.assertEqual(r['X-Robots-Tag'], 'noindex, nofollow')

    def test_x_robots_hasil_pencarian_dinamis(self):
        r = self.client.get('/bus/?origin=1&destination=2&date=2026-12-01')
        self.assertEqual(r['X-Robots-Tag'], 'noindex, follow')
        # halaman publik normal bebas header (tetap dapat diindeks)
        for url in ('/', '/bus/', '/tentang/', '/robots.txt'):
            self.assertNotIn('X-Robots-Tag', self.client.get(url))

    def test_frame_deny_hsts_di_produksi(self):
        from django.conf import settings
        mw = [m for m in settings.MIDDLEWARE
              if 'XFrameOptions' not in m] + ['django.middleware.clickjacking.XFrameOptionsMiddleware']
        with override_settings(MIDDLEWARE=mw, X_FRAME_OPTIONS='DENY',
                               SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=31536000,
                               SECURE_HSTS_INCLUDE_SUBDOMAINS=True):
            r = self.client.get('/', secure=True)
            self.assertEqual(r['X-Frame-Options'], 'DENY')
            self.assertEqual(r['Strict-Transport-Security'],
                             'max-age=31536000; includeSubDomains')

    def test_preview_tanpa_x_frame_options(self):
        # mode default (tanpa DJANGO_SSL_REDIRECT): tidak ada header XFO
        r = self.client.get('/')
        self.assertNotIn('X-Frame-Options', r)


class PrivateMediaTest(TestCase):
    """Bukti pembayaran di /media/ privat; foto kendaraan & OG tetap publik."""

    FILES = {
        'vehicles/uji-publik.webp': b'publik-mobil',
        'meta/uji-og.webp': b'publik-og',
        'payment_proofs/2026/10/bukti-bus.jpg': b'rahasia-bus',
        'rental_proofs/2026/10/bukti-rental.jpg': b'rahasia-rental',
        'dokumen-lain/uji.txt': b'rahasia-lain',
    }

    def setUp(self):
        import tempfile
        from pathlib import Path
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._override = override_settings(MEDIA_ROOT=self._tmp.name)
        self._override.enable()
        self.addCleanup(self._override.disable)
        root = Path(self._tmp.name)
        for relative, content in self.FILES.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    @staticmethod
    def _content(response):
        if response.streaming:
            return b''.join(response.streaming_content)
        return response.content

    def test_media_publik_bebas_diakses(self):
        for relative in ('vehicles/uji-publik.webp', 'meta/uji-og.webp'):
            with self.subTest(relative=relative):
                r = self.client.get(f'/media/{relative}')
                self.assertEqual(r.status_code, 200)
                self.assertEqual(self._content(r), self.FILES[relative])

    def test_bukti_bayar_anonim_dan_non_staf_ditolak(self):
        for relative in ('payment_proofs/2026/10/bukti-bus.jpg',
                         'rental_proofs/2026/10/bukti-rental.jpg',
                         'dokumen-lain/uji.txt'):
            with self.subTest(relative=relative):
                r = self.client.get(f'/media/{relative}')
                self.assertEqual(r.status_code, 404)
                self.assertNotIn(self.FILES[relative], self._content(r))

        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username='pengguna-biasa', password='RahasiaUji#123')
        self.client.force_login(user)
        r = self.client.get('/media/payment_proofs/2026/10/bukti-bus.jpg')
        self.assertEqual(r.status_code, 404)

    def test_bukti_bayar_staf_bisa_diakses_tanpa_cache(self):
        from django.contrib.auth import get_user_model
        staff = get_user_model().objects.create_user(
            username='staf-uji', password='RahasiaUji#123', is_staff=True)
        self.client.force_login(staff)
        r = self.client.get('/media/payment_proofs/2026/10/bukti-bus.jpg')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            self._content(r), self.FILES['payment_proofs/2026/10/bukti-bus.jpg'])
        self.assertEqual(r['Cache-Control'], 'private, no-store')

    def test_alias_traversal_tidak_bisa_menyelundup_ke_bukti(self):
        r = self.client.get('/media/vehicles/../payment_proofs/2026/10/bukti-bus.jpg')
        self.assertEqual(r.status_code, 404)
        self.assertNotIn(
            self.FILES['payment_proofs/2026/10/bukti-bus.jpg'], self._content(r))

    def test_sesi_pemilik_detail_rental_bisa_memuat_thumbnail_sendiri(self):
        from datetime import date
        from django.test import Client
        from rental.models import RentalBooking, Vehicle
        vehicle = Vehicle.objects.create(
            name='Toyota Bukti', category='MPV', year=2023,
            transmission='MATIC', seats=7, price_per_day=400000)
        booking = RentalBooking.objects.create(
            vehicle=vehicle, pickup_date=date.today(), return_date=date.today(),
            pickup_location='Jember', contact_name='Uji',
            contact_phone='081234567890', days=1, total_price=400000,
            payment_proof='rental_proofs/2026/10/bukti-rental.jpg')
        url = '/media/rental_proofs/2026/10/bukti-rental.jpg'

        # Tanpa sesi pemilik (belum membuka detail berkode) tetap tertolak.
        self.assertEqual(Client().get(url).status_code, 404)

        r = self.client.get(f'/rental/sewa/{booking.code}/')
        self.assertEqual(r.status_code, 200)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            self._content(r), self.FILES['rental_proofs/2026/10/bukti-rental.jpg'])
        # Izin sesi hanya untuk berkas persis itu, bukan bukti booking lain.
        self.assertEqual(
            self.client.get(
                '/media/payment_proofs/2026/10/bukti-bus.jpg').status_code, 404)

    def test_sesi_pemilik_detail_booking_bus_bisa_memuat_thumbnail_sendiri(self):
        from datetime import date, timedelta
        from booking.models import Booking, Bus, City, Route, Schedule
        asal = City.objects.create(name='Kota Bukti A', slug='kota-bukti-a', province='Jawa Timur')
        tujuan = City.objects.create(name='Kota Bukti B', slug='kota-bukti-b', province='Jawa Timur')
        route = Route.objects.create(
            origin=asal, destination=tujuan, distance_km=100, duration_minutes=120)
        bus = Bus.objects.create(
            code='NT-BUKTI', name='Bus Bukti', plate_number='N 1111 BK',
            bus_class='EKONOMI', rows=2)
        schedule = Schedule.objects.create(
            route=route, bus=bus, departure_time='08:00',
            arrival_time='10:00', price=50000)
        booking = Booking.objects.create(
            schedule=schedule, travel_date=date.today() + timedelta(days=1),
            contact_name='Uji', contact_phone='081234567890', seats_qty=1,
            total_price=50000,
            payment_proof='payment_proofs/2026/10/bukti-bus.jpg')
        url = '/media/payment_proofs/2026/10/bukti-bus.jpg'

        self.assertEqual(self.client.get(url).status_code, 404)
        r = self.client.get(f'/bus/booking/{booking.code}/')
        self.assertEqual(r.status_code, 200)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            self._content(r), self.FILES['payment_proofs/2026/10/bukti-bus.jpg'])
        self.assertEqual(
            self.client.get(
                '/media/rental_proofs/2026/10/bukti-rental.jpg').status_code, 404)


class ErrorPagesTest(TestCase):
    """404/500 kustom: status jujur (anti soft-404), nav + form pencarian."""

    def test_404_status_jujur_tanpa_redirect(self):
        r = self.client.get('/halaman-tidak-ada-x/')
        self.assertEqual(r.status_code, 404)  # langsung 404, BUKAN 301/302
        self.assertNotIn('Location', r)

    def test_404_memuat_nav_form_dan_saran_rute(self):
        html = self.client.get('/halaman-tidak-ada-x/').content.decode()
        self.assertIn('nt-navbar', html)          # navigasi utama (extends base)
        self.assertIn('id="id_origin"', html)     # form pencarian
        self.assertIn('id="id_destination"', html)
        self.assertIn('id="id_date"', html)
        self.assertIn('/bus/rute/dari/jember/surabaya/', html)  # saran rute populer

    def test_404_url_model_tak_ada_juga_branded(self):
        r = self.client.get('/bus/rute/tidak-ada-999/')
        self.assertEqual(r.status_code, 404)
        self.assertIn(b'nt-navbar', r.content)

    def test_500_branded_dengan_status_500(self):
        import sys
        import types
        from django.urls import path
        mod = types.ModuleType('boom_urls')

        def boom(request):
            raise RuntimeError('uji halaman 500')

        # urlconf uji = view pemancing exception + SELURUH url asli,
        # agar template 500 (navbar: {% url 'home' %}) tetap bisa di-reverse.
        from core import urls as core_urls_mod
        mod.urlpatterns = [path('boom/', boom)] + list(core_urls_mod.urlpatterns)
        sys.modules['boom_urls'] = mod
        from django.test import Client
        with override_settings(ROOT_URLCONF='boom_urls'):
            # raise_request_exception = param KONSTRUKTOR Client (Django 5)
            r = Client(raise_request_exception=False).get('/boom/')
        self.assertEqual(r.status_code, 500)
        self.assertIn('Ada gangguan', r.content.decode())
        self.assertIn('nt-navbar', r.content.decode())


class InternalLinkingTest(TestCase):
    """Arsitektur hub & sibling: PageRank menyebar ke semua halaman rute."""

    @classmethod
    def setUpTestData(cls):
        from booking.models import Bus, City, Route, Schedule
        a = City.objects.create(name='Kota A', slug='kota-a')
        b = City.objects.create(name='Kota B', slug='kota-b')
        c = City.objects.create(name='Kota C', slug='kota-c')
        bus = Bus.objects.create(code='NT-INT', name='Bus Inti', plate_number='E 7000 XX')
        for dest, km, menit in ((b, 100, 120), (c, 80, 90)):
            r = Route.objects.create(
                origin=a, destination=dest, distance_km=km, duration_minutes=menit)
            Schedule.objects.create(
                route=r, bus=bus, departure_time='07:00',
                arrival_time='09:00', price=90000)

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_hub_semua_rute_dikelompokkan_per_kota(self):
        r = self.client.get('/bus/rute/')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('Dari Kota A', html)                 # regroup per kota asal
        self.assertIn('href="/bus/rute/dari/kota-a/kota-b/"', html)
        self.assertIn('href="/bus/rute/dari/kota-a/kota-c/"', html)
        self.assertIn('BreadcrumbList', html)

    def test_hub_di_sitemap(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        # domain-agnostic: Site bawaan test = example.com
        self.assertIn('/bus/rute/</loc>', xml)

    def test_route_detail_memuat_link_sibling_dan_hub(self):
        html = self.client.get('/bus/rute/dari/kota-a/kota-b/').content.decode()
        self.assertIn('Rute lain dari Kota A', html)
        self.assertIn('href="/bus/rute/dari/kota-a/kota-c/"', html)  # sibling
        self.assertIn('href="/bus/rute/"', html)                 # ke hub

    def test_footer_beranda_menunjuk_hub(self):
        html = self.client.get('/').content.decode()
        self.assertIn('href="/bus/rute/"', html)

    def test_filter_kategori_rental_noindex_follow(self):
        r = self.client.get('/rental/?kategori=MPV')
        self.assertEqual(r['X-Robots-Tag'], 'noindex, follow')


class SiloArchitectureTest(TestCase):
    """Topic cluster/silo: pillar per kota, upward/downward/lateral wajib,
    tanpa link lintas-silo dari halaman artikel."""

    @classmethod
    def setUpTestData(cls):
        from booking.models import Bus, City, Route, Schedule
        from rental.models import Vehicle
        a = City.objects.create(name='Kota A', slug='kota-a')
        b = City.objects.create(name='Kota B', slug='kota-b')
        c = City.objects.create(name='Kota C', slug='kota-c')
        bus = Bus.objects.create(code='NT-SIL', name='Bus Silo', plate_number='E 6000 XX')
        for dest, slug, km in ((b, 'kota-a-kota-b', 100), (c, 'kota-a-kota-c', 80)):
            r = Route.objects.create(
                origin=a, destination=dest, distance_km=km, duration_minutes=120)
            Schedule.objects.create(
                route=r, bus=bus, departure_time='07:00', arrival_time='09:00',
                price=90000)
        Vehicle.objects.create(
            name='Mobil Silo', slug='mobil-silo', category='MPV',
            year=2023, seats=7, price_per_day=300000)

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_pillar_downward_link_semua_rute_sekota(self):
        r = self.client.get('/bus/rute/dari/kota-a/')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('Bus dari Kota A', html)
        self.assertIn('href="/bus/rute/dari/kota-a/kota-b/"', html)   # downward
        self.assertIn('href="/bus/rute/dari/kota-a/kota-c/"', html)   # downward
        self.assertIn('href="/bus/rute/"', html)                 # upward ke hub

    def test_pillar_kota_tanpa_rute_404_jujur(self):
        r = self.client.get('/bus/rute/dari/kota-c/')  # kota-c hanya tujuan
        self.assertEqual(r.status_code, 404)
        r = self.client.get('/bus/rute/dari/nggak-ada/')
        self.assertEqual(r.status_code, 404)

    def test_upward_link_wajib_di_semua_rute(self):
        for slug, dest in (('kota-a-kota-b', 'kota-b'), ('kota-a-kota-c', 'kota-c')):
            html = self.client.get(f'/bus/rute/dari/kota-a/{dest}/').content.decode()
            # upward: pillar silo & hub — tanpa syarat sibling ada/tidak
            self.assertIn('href="/bus/rute/dari/kota-a/"', html, slug)
            self.assertIn('href="/bus/rute/"', html, slug)

    def test_lateral_hanya_dalam_silo_yang_sama(self):
        html = self.client.get('/bus/rute/dari/kota-a/kota-b/').content.decode()
        self.assertIn('href="/bus/rute/dari/kota-a/kota-c/"', html)  # se-silo

    def test_tidak_ada_link_lintas_silo_dari_artikel(self):
        # Link KONTEKSTUAL (dalam <main>) di halaman rute tidak boleh keluar silo.
        # Navbar/footer = global chrome semua situs — di luar cakupan aturan.
        import re
        html = self.client.get('/bus/rute/dari/kota-a/kota-b/').content.decode()
        main = re.search(r'<main id="main">(.*?)</main>', html, re.S).group(1)
        tautan = set(re.findall(r'href="(/[^"]*)"', main))
        liar = [t for t in tautan if t.startswith('/rental/')]
        self.assertFalse(liar, f'Link lintas-silo di konten: {liar}')
        # semua tautan rute dalam konten = se-silo kota A (lateral) atau ke atas
        for t in (t for t in tautan if t.startswith('/bus/rute/')):
            self.assertTrue(
                t in ('/bus/rute/', '/bus/rute/dari/kota-a/',
                      '/bus/rute/dari/kota-a/kota-b/', '/bus/rute/dari/kota-a/kota-c/'),
                f'Tautan keluar silo: {t}')


    def test_prev_next_dalam_silo(self):
        """C: pagination linking — prev/next hanya di dalam silo yang sama."""
        # rute PERTAMA (Kota B urut lebih dulu): tanpa prev, ada next
        h1 = self.client.get('/bus/rute/dari/kota-a/kota-b/').content.decode()
        self.assertNotIn('Rute sebelumnya', h1)
        self.assertIn('Rute selanjutnya', h1)
        self.assertIn('href="/bus/rute/dari/kota-a/kota-c/"', h1)
        # rute TERAKHIR: ada prev, tanpa next
        h2 = self.client.get('/bus/rute/dari/kota-a/kota-c/').content.decode()
        self.assertIn('Rute sebelumnya', h2)
        self.assertIn('href="/bus/rute/dari/kota-a/kota-b/"', h2)
        self.assertNotIn('Rute selanjutnya', h2)

    def test_breadcrumb_komponen_di_semua_halaman_seo(self):
        """A: breadcrumb terlihat + JSON-LD hadir di semua halaman dalam."""
        for url in ('/bus/rute/dari/kota-a/kota-b/', '/bus/rute/dari/kota-a/',
                    '/bus/rute/', '/rental/mobil/mobil-silo/'):
            html = self.client.get(url).content.decode()
            self.assertIn('class="breadcrumb', html, url)      # terlihat (upward link)
            self.assertIn('"BreadcrumbList"', html, url)       # data terstruktur

    def test_pillar_di_sitemap(self):
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn('/bus/rute/dari/kota-a/</loc>', xml)

    def test_hub_link_ke_pillar_per_kota(self):
        html = self.client.get('/bus/rute/').content.decode()
        self.assertIn('href="/bus/rute/dari/kota-a/"', html)  # downward ke pillar


class InTextLinkingTest(TestCase):
    """Auto-linking internal: model SeoKeyword, self-link, densitas, HTML-safe."""

    def setUp(self):
        from django.core.cache import cache
        from core.models import SeoKeyword
        SeoKeyword.objects.update_or_create(
            phrase='tiket bus', defaults={'url': '/bus/'})
        cache.clear()

    def _filter(self):
        from core.templatetags.seo_internal_links import auto_internal_link
        return auto_internal_link

    def test_filter_pemunculan_pertama_saja(self):
        hasil = str(self._filter()('Tiket bus murah. Tiket bus cepat.'))
        self.assertEqual(hasil.count('<a '), 1)
        self.assertIn('href="/bus/"', hasil)
        self.assertIn('>Tiket bus<', hasil)  # anchor = teks asli (deskriptif)

    def test_filter_tak_menautkan_di_dalam_anchor_ada(self):
        hasil = str(self._filter()('lihat <a href="/x/">Tiket bus</a> murah'))
        self.assertEqual(hasil.count('<a '), 1)  # yang lama tidak digandakan

    def test_filter_aman_terhadap_html(self):
        hasil = str(self._filter()('<script>alert("tiket bus")</script>'))
        self.assertNotIn('<script>', hasil)  # ter-escape

    def test_keyword_dari_db_dan_sinyal_invalidate_cache(self):
        from core.models import SeoKeyword
        kw, _ = SeoKeyword.objects.get_or_create(
            phrase='panduan pesan', defaults={'url': '/bus/'})
        from django.core.cache import cache
        cache.clear()
        hasil = str(self._filter()('baca panduan pesan tiket dulu'))
        self.assertIn('href="/bus/"', hasil)
        kw.url = '/rental/'          # save -> sinyal hapus cache
        kw.save()
        hasil = str(self._filter()('baca panduan pesan tiket dulu'))
        self.assertIn('href="/rental/"', hasil)
        self.assertNotIn('href="/bus/"', hasil)

    def test_keyword_nonaktif_dilewati(self):
        from core.models import SeoKeyword
        SeoKeyword.objects.update_or_create(
            phrase='paket wisata', defaults={'url': '/rental/',
                                             'is_active': False})
        hasil = str(self._filter()('paket wisata murah'))
        self.assertNotIn('<a ', hasil)

    def test_anti_self_link(self):
        from booking.models import Bus, City, Route, Schedule
        a = City.objects.create(name='Kota S', slug='kota-s')
        b = City.objects.create(name='Kota T', slug='kota-t')
        bus = Bus.objects.create(code='NT-SLF', name='Bus Self',
                                 plate_number='E 4000 XX')
        r = Route.objects.create(origin=a, destination=b, distance_km=70,
                                 duration_minutes=90)
        Schedule.objects.create(route=r, bus=bus, departure_time='07:00',
                                arrival_time='08:30', price=80000)
        from django.core.cache import cache
        cache.clear()
        f = self._filter()
        # halaman pillar Kota S tidak menautkan "Kota S" ke dirinya sendiri
        hasil = str(f('Kota S adalah hub.', '/bus/rute/dari/kota-s/'))
        self.assertNotIn('<a ', hasil)
        # halaman lain tetap menautkan
        hasil = str(f('Kota S adalah hub.', '/bus/rute/'))
        self.assertIn('href="/bus/rute/dari/kota-s/"', hasil)
        # url "/" tidak pernah ditautkan (beranda = self di mana-mana jika kosong)
        SeoKeyword = self._kw()
        SeoKeyword.objects.update_or_create(
            phrase='beranda', defaults={'url': '/'})
        from django.core.cache import cache as c2
        c2.delete('seo:db_keywords')
        self.assertNotIn('<a ', str(f('kunjungi beranda kami')))

    def _kw(self):
        from core.models import SeoKeyword
        return SeoKeyword

    def test_url_dinormalisasi_slash_konsisten(self):
        kw = self._kw()(phrase='bus akap', url='/bus')
        kw.full_clean()  # validasi + normalisasi
        kw.save()
        self.assertEqual(kw.url, '/bus/')  # APPEND_SLASH-consistent
        from django.core.cache import cache
        cache.clear()
        hasil = str(self._filter()('bus akap nyaman'))
        self.assertIn('href="/bus/"', hasil)

    def test_url_luar_ditolak(self):
        from django.core.exceptions import ValidationError
        for jahat in ('https://luar.com/', '//luar.com/',
                      'javascript:alert(1)'):
            with self.assertRaises(ValidationError):
                kw = self._kw()(phrase='jes', url=jahat)
                kw.full_clean()

    def test_batas_densitas_link(self):
        kw = self._kw()
        istilah = ['alpha beta', 'gamma delta', 'epsilon', 'zeta eta',
                   'theta', 'iota']
        target = ['/bus/', '/rental/', '/tentang/', '/kontak/',
                  '/bus/rute/', '/cek-booking/']
        for frasa, url in zip(istilah, target):
            kw.objects.update_or_create(phrase=frasa, defaults={'url': url})
        from django.core.cache import cache
        cache.clear()
        f = self._filter()
        # teks pendek (~90 kata): budget 1 link
        pendek = 'teks ' * 80 + ' '.join(istilah)
        self.assertEqual(str(f(pendek)).count('<a '), 1)
        # teks panjang (1000+ kata): maksimum 4 link (2-4 per 1000 kata)
        panjang = 'teks ' * 1000 + ' '.join(istilah)
        self.assertLessEqual(str(f(panjang)).count('<a '), 4)
        self.assertEqual(str(f(panjang)).count('<a '), 4)

    def test_faq_jawaban_tertautinkonten(self):
        from booking.models import Bus, City, Route, Schedule
        a = City.objects.create(name='Kota A', slug='kota-a')
        b = City.objects.create(name='Kota B', slug='kota-b')
        bus = Bus.objects.create(code='NT-INT2', name='Bus I2', plate_number='E 3000 XX')
        r = Route.objects.create(origin=a, destination=b, distance_km=90, duration_minutes=110)
        Schedule.objects.create(route=r, bus=bus, departure_time='08:00',
                                arrival_time='10:00', price=95000)
        from django.core.cache import cache
        cache.clear()
        html = self.client.get('/bus/rute/dari/kota-a/kota-b/').content.decode()
        # "Kota A" di jawaban FAQ otomatis jadi link ke pillar kota (class ilink)
        self.assertIn('<a class="ilink" href="/bus/rute/dari/kota-a/">Kota A</a>', html)

    def test_homepage_grid_kategori_semua_pillar(self):
        from booking.models import Bus, City, Route, Schedule
        a = City.objects.create(name='Kota A', slug='kota-a')
        b = City.objects.create(name='Kota B', slug='kota-b')
        bus = Bus.objects.create(code='NT-GRD', name='Bus Grid', plate_number='E 2000 XX')
        r = Route.objects.create(origin=a, destination=b, distance_km=50, duration_minutes=60)
        Schedule.objects.create(route=r, bus=bus, departure_time='06:00',
                                arrival_time='07:00', price=50000)
        from django.core.cache import cache
        cache.clear()
        html = self.client.get('/').content.decode()
        self.assertIn('Pilih kota keberangkatan', html)
        self.assertIn('href="/bus/rute/dari/kota-a/"', html)   # pillar 1 klik
        self.assertIn('Bus dari Kota A', html)                 # anchor deskriptif

    def test_homepage_tanpa_link_non_seo(self):
        html = self.client.get('/').content.decode()
        for jelek in ('/admin/', 'privacy', 'terms', 'login'):
            self.assertNotIn(f'href="{jelek}', html)


class LowercaseMiddlewareTest(TestCase):
    """LowercasePathMiddleware: halaman kapital -> 301; aset tidak disentuh."""

    def test_aset_static_media_tak_dialihkan(self):
        from django.http import HttpResponse
        from django.test import RequestFactory
        from core.middleware import LowercasePathMiddleware
        rf = RequestFactory()
        for pth in ('/static/IMG/hero-bus.webp', '/media/vehicles/X.webp'):
            resp = LowercasePathMiddleware(
                lambda r: HttpResponse(status=404))(rf.get(pth))
            self.assertEqual(resp.status_code, 404)  # lolos, tanpa 301

    def test_halaman_kapital_tetap_301(self):
        resp = self.client.get('/BUS/')
        self.assertEqual(resp.status_code, 301)
        self.assertEqual(resp['Location'], '/bus/')
