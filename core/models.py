"""Model inti: metadata SEO per halaman, dikelola lewat /admin/."""
from django.db import models
from django.utils.translation import gettext_lazy as _


class PageMeta(models.Model):
    """Metadata SEO per halaman — menimpa nilai default templat.

    `path` dicocokkan persis dengan URL. Baris tanpa prefiks bahasa
    (mis. '/bus/') berlaku untuk ID dan EN; buat baris berprefiks
    (mis. '/en/bus/') bila ingin judul khusus bahasa Inggris.

    Prioritas judul/deskripsi: objek (halaman detail) > PageMeta >
    default templat. Halaman yang menimpa blok meta sendiri tetap
    memakai versinya.
    """

    path = models.CharField(
        _('path'), max_length=200, unique=True,
        help_text=_("URL halaman, contoh '/bus/'. Baris '/en/bus/' khusus EN; "
                    "tanpa prefiks berlaku untuk kedua bahasa."))
    title = models.CharField(
        _('judul (title & og:title)'), max_length=180, blank=True)
    description = models.TextField(
        _('meta description'), blank=True,
        help_text=_('Disarankan 120–160 karakter.'))
    og_image = models.ImageField(
        _('gambar Open Graph'), upload_to='meta/', blank=True,
        help_text=_('Idealnya rasio 1.91:1, minimal 1200×630 px.'))
    noindex = models.BooleanField(
        _('noindex'), default=False,
        help_text=_('Tandai halaman <meta name="robots" content="noindex"> '
                    'agar tidak diindeks mesin pencari.'))
    updated_at = models.DateTimeField(_('diperbarui'), auto_now=True)

    class Meta:
        verbose_name = _('Metadata halaman (SEO)')
        verbose_name_plural = _('Metadata halaman (SEO)')
        ordering = ['path']

    def __str__(self):
        return self.path
