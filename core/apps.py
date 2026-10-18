from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Inti'

    def ready(self):
        from django.core.cache import cache
        from django.db.models.signals import post_delete, post_save

        from core import checks  # noqa: F401 — register system check core.E001
        from core.models import PageMeta

        # Metadata SEO diubah admin -> halaman cache_page(900) langsung segar.
        post_save.connect(lambda **kw: cache.clear(), sender=PageMeta, weak=False)
        post_delete.connect(lambda **kw: cache.clear(), sender=PageMeta, weak=False)
