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
