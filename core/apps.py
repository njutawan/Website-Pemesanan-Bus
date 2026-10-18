from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Inti'

    def ready(self):
        from django.conf import settings
        from django.core.cache import cache
        from django.db.models.signals import post_delete, post_save

        from core import checks  # noqa: F401 — register system check core.E001
        from core import signals  # noqa: F401 — audit login/gagal/logout
        from core.models import PageMeta, SeoKeyword

        # Anti decompression bomb: batasi piksel gambar yang dibuka Pillow.
        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = getattr(settings, 'IMAGE_MAX_PIXELS', 25_000_000)
        except Exception:  # pragma: no cover — Pillow selalu terpasang di produksi
            pass

        # Metadata SEO diubah admin -> halaman cache_page(900) langsung segar.
        post_save.connect(lambda **kw: cache.clear(), sender=PageMeta, weak=False)
        post_delete.connect(lambda **kw: cache.clear(), sender=PageMeta, weak=False)

        # Kata kunci auto-link diubah admin -> peta istilah langsung segar.
        def _clear_keyword_cache(**kw):
            cache.delete('seo:db_keywords')
        post_save.connect(_clear_keyword_cache, sender=SeoKeyword, weak=False)
        post_delete.connect(_clear_keyword_cache, sender=SeoKeyword, weak=False)
