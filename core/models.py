"""Model inti: metadata SEO per halaman, audit keamanan, dikelola lewat /admin/."""
from django.conf import settings
from django.core.exceptions import ValidationError
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
        help_text=_("URL halaman, contoh '/bus/'. Baris '/en/bus/' khusus EN; tanpa prefiks berlaku untuk kedua bahasa."))
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
        help_text=_('Tandai halaman <meta name="robots" content="noindex"> agar tidak diindeks mesin pencari.'))
    updated_at = models.DateTimeField(_('diperbarui'), auto_now=True)

    class Meta:
        verbose_name = _('Metadata halaman (SEO)')
        verbose_name_plural = _('Metadata halaman (SEO)')
        ordering = ['path']

    def clean(self):
        path = (self.path or '').strip()
        if not path.startswith('/') or path.startswith('//'):
            raise ValidationError({
                'path': _('Path internal wajib diawali satu "/" (bukan URL penuh).')
            })
        if '://' in path or '\\' in path:
            raise ValidationError({
                'path': _('Skema/domain luar dan backslash tidak diizinkan.')
            })
        self.path = path

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.og_image and not str(self.og_image.name).lower().endswith('.webp'):
            from core.img_tools import convert_to_webp
            new_name = convert_to_webp(self.og_image, max_width=1600)
            if new_name:
                self.og_image.name = new_name
                super().save(update_fields=['og_image'])

    def __str__(self):
        return self.path


class SeoKeyword(models.Model):
    """Kata kunci -> URL internal utk auto-linking konten (in-text link).

    Dikelola lewat /admin/: perubahan apapun otomatis menghapus cache
    peta kata kunci (sinyal di core.apps.CoreConfig.ready). URL wajib
    path internal relatif dengan slash-akhir konsisten (APPEND_SLASH).
    """

    phrase = models.CharField('frasa', max_length=100, unique=True)
    url = models.CharField('URL internal', max_length=300)
    is_active = models.BooleanField('aktif', default=True)
    updated = models.DateTimeField('diperbarui', auto_now=True)

    class Meta:
        verbose_name = 'kata kunci SEO'
        verbose_name_plural = 'kata kunci SEO'
        ordering = ('phrase',)

    def __str__(self):
        return f'{self.phrase} → {self.url}'

    def clean(self):
        u = (self.url or '').strip()
        if not u.startswith('/'):
            raise ValidationError({'url': 'Wajib path internal relatif yang '
                                          'diawali "/" (tanpa domain luar).'})
        if '://' in u or u.startswith('//'):
            raise ValidationError({'url': 'Skema/domain luar tidak diizinkan.'})
        # Normalisasi: path selalu berakhir "/" (konsisten APPEND_SLASH);
        # query (?) dan fragment (#) diletakkan setelah slash.
        frag = ''
        if '#' in u:
            u, _, frag = u.partition('#')
            frag = '#' + frag
        query = ''
        if '?' in u:
            u, _, query = u.partition('?')
            query = '?' + query
        if not u.endswith('/'):
            u += '/'
        self.url = u + query + frag


class AuditLog(models.Model):
    """Jejak audit keamanan — hanya superuser yang boleh membacanya.

    Data sensitif (password, token, email, telepon, nama, URL bukti bayar)
    TIDAK disimpan di sini. Kode booking disamarkan oleh ``core.audit``;
    metadata hanya berisi field operasional yang aman. Retensi default 180
    hari (``AUDIT_RETENTION_DAYS``).
    """

    class Action(models.TextChoices):
        LOGIN_SUCCESS = 'LOGIN_SUCCESS', _('Login berhasil')
        LOGIN_FAILED = 'LOGIN_FAILED', _('Login gagal')
        LOGOUT = 'LOGOUT', _('Logout')
        BOOKING_CREATED = 'BOOKING_CREATED', _('Booking dibuat')
        PROOF_UPLOADED = 'PROOF_UPLOADED', _('Bukti bayar diunggah')
        PAYMENT_CONFIRMED = 'PAYMENT_CONFIRMED', _('Pembayaran dikonfirmasi')
        PAYMENT_CANCELLED = 'PAYMENT_CANCELLED', _('Booking dibatalkan')
        EXPORT = 'EXPORT', _('Ekspor data admin')
        RATE_LIMITED = 'RATE_LIMITED', _('Rate limit terlampaui')
        ADMIN_IP_DENIED = 'ADMIN_IP_DENIED', _('Akses admin ditolak (IP)')
        WEBHOOK_REJECTED = 'WEBHOOK_REJECTED', _('Webhook ditolak')
        SECURITY_EVENT = 'SECURITY_EVENT', _('Peristiwa keamanan lain')

    created_at = models.DateTimeField(_('waktu'), auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('pelaku'), null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_events')
    action = models.CharField(
        _('aksi'), max_length=32, choices=Action.choices, db_index=True)
    success = models.BooleanField(_('berhasil'), default=True)
    target = models.CharField(_('target (disamarkan)'), max_length=120, blank=True)
    ip = models.GenericIPAddressField(_('IP'), null=True, blank=True)
    user_agent = models.CharField(_('user agent'), max_length=255, blank=True)
    request_id = models.CharField(_('request id'), max_length=64, blank=True)
    metadata = models.JSONField(_('metadata aman'), default=dict, blank=True)

    class Meta:
        verbose_name = _('log audit')
        verbose_name_plural = _('log audit')
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['action', 'created_at'], name='audit_action_time_ix'),
            models.Index(fields=['ip', 'created_at'], name='audit_ip_time_ix'),
        ]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.target}'
