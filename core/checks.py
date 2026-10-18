"""System check: gagal cepat bila urutan deploy compress → collectstatic terbalik.

Saat COMPRESS_OFFLINE aktif (DEBUG=0), {% compress %} butuh manifest hasil
`manage.py compress`. Bila manifest tidak ada, setiap halaman akan 500 saat
produksi. Check ini menampilkan Error di `manage.py check` SEBELUM deploy.
Catatan: saat DEBUG=0 compressor membaca sumber dari STATIC_ROOT — urutan
yang benar adalah `collectstatic` DULULU, baru `compress --force`.
"""
from django.conf import settings
from django.core import checks


@checks.register()
def compress_offline_manifest(app_configs, **kwargs):
    if settings.DEBUG or not getattr(settings, 'COMPRESS_OFFLINE', False):
        return []
    try:
        from compressor.storage import default_offline_manifest_storage
        ada = default_offline_manifest_storage.exists(settings.COMPRESS_OFFLINE_MANIFEST)
    except Exception:
        return []  # compressor tidak terpasang — biarkan modul lain yang mengeluh
    if not ada:
        return [checks.Error(
            'Manifest django-compressor offline tidak ditemukan di STATIC_ROOT.',
            hint='Saat DEBUG=0 compressor membaca sumber dari STATIC_ROOT. Jalankan '
                 '"python manage.py collectstatic --noinput" lalu '
                 '"DJANGO_DEBUG=0 python manage.py compress --force".',
            id='core.E001',
        )]
    return []
