"""Model rental mobil: armada sewa & pemesanan sewa."""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from booking.models import TimeStampedModel, generate_code


class Vehicle(TimeStampedModel):
    """Armada mobil yang disewakan."""

    class Category(models.TextChoices):
        MPV = 'MPV', _('MPV (5–7 penumpang)')
        SUV = 'SUV', _('SUV (5–7 penumpang)')
        VAN = 'VAN', _('Van / Minibus (10–16 penumpang)')
        BUS = 'BUS', _('Bus Kecil (20+ penumpang)')

    name = models.CharField(_('nama mobil'), max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    category = models.CharField(
        _('kategori'), max_length=10, choices=Category.choices, db_index=True)
    year = models.PositiveSmallIntegerField(_('tahun'))
    transmission = models.CharField(
        _('transmisi'), max_length=10,
        choices=[('MATIC', _('Matic')), ('MANUAL', _('Manual'))], default='MATIC')
    seats = models.PositiveSmallIntegerField(_('kapasitas kursi'))
    price_per_day = models.DecimalField(_('harga per hari'), max_digits=12, decimal_places=0)
    driver_fee_per_day = models.DecimalField(
        _('biaya sopir per hari'), max_digits=12, decimal_places=0, default=0,
        help_text=_('Tambahan bila pelanggan minta disertai sopir. 0 = gratis.'))
    image = models.ImageField(
        _('foto mobil'), upload_to='vehicles/%Y/%m/',
        default='vehicles/default-vehicle.webp',
        help_text=_('Otomatis dikonversi ke WebP (maks. lebar 1200px).'))
    description = models.TextField(_('deskripsi'), blank=True)
    is_available = models.BooleanField(_('tersedia'), default=True, db_index=True)

    class Meta:
        verbose_name = _('mobil rental')
        verbose_name_plural = ('mobil rental')
        ordering = ['category', 'price_per_day']

    def save(self, *args, **kwargs):
        from django.utils.text import slugify
        if not self.slug:
            base = slugify(self.name)
            slug, i = base, 2
            while Vehicle.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
        # Pipeline gambar: unggahan jpg/png otomatis jadi WebP (LCP/CLS).
        if self.image and not str(self.image.name).lower().endswith('.webp'):
            from core.img_tools import convert_to_webp
            new_name = convert_to_webp(self.image)
            if new_name:
                self.image.name = new_name
                super().save(update_fields=['image'])

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('rental:detail', kwargs={'slug': self.slug})

    @property
    def spec_list(self):
        return [
            ('fa-users', f'{self.seats} ' + _('kursi')),
            ('fa-gear', self.get_transmission_display()),
            ('fa-calendar', str(self.year)),
            ('fa-suitcase-rolling', _('Bagasi luas')),
        ]

    def __str__(self):
        return self.name


class RentalBooking(TimeStampedModel):
    """Pemesanan sewa mobil (status dibuat → admin verifikasi pembayaran)."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Menunggu pembayaran')
        CONFIRMED = 'CONFIRMED', _('Terkonfirmasi')
        COMPLETED = 'COMPLETED', _('Selesai')
        CANCELLED = 'CANCELLED', _('Dibatalkan')
        EXPIRED = 'EXPIRED', _('Kedaluwarsa')

    # Status yang masih "memegang" unit pada rentang tanggalnya.
    # COMPLETED sudah selesai/dikembalikan & CANCELLED batal: tidak mengunci.
    LOCKING_STATUSES = [Status.PENDING, Status.CONFIRMED]

    code = models.CharField(_('kode sewa'), max_length=16, unique=True, db_index=True)
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.PROTECT, related_name='rentals', verbose_name=_('mobil'))
    pickup_date = models.DateField(_('tanggal ambil'))
    return_date = models.DateField(_('tanggal kembali'))
    pickup_location = models.CharField(_('lokasi ambil'), max_length=200)
    with_driver = models.BooleanField(_('dengan sopir'), default=False)
    contact_name = models.CharField(_('nama penyewa'), max_length=100)
    contact_phone = models.CharField(_('no. WhatsApp'), max_length=20)
    contact_email = models.EmailField(_('email'), blank=True)
    days = models.PositiveSmallIntegerField(_('lama sewa (hari)'))
    total_price = models.DecimalField(_('total harga'), max_digits=12, decimal_places=0)
    status = models.CharField(
        _('status'), max_length=12, choices=Status.choices, default=Status.PENDING,
        db_index=True)
    payment_method = models.CharField(_('metode pembayaran'), max_length=20, blank=True)
    payment_proof = models.ImageField(
        _('bukti pembayaran'), upload_to='rental_proofs/%Y/%m/', blank=True, null=True)
    paid_at = models.DateTimeField(_('dibayar pada'), null=True, blank=True)
    admin_note = models.TextField(_('catatan admin'), blank=True)

    class Meta:
        verbose_name = _('booking rental')
        verbose_name_plural = ('booking rental')
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.code:
            for _ in range(10):
                candidate = generate_code('SEWA')
                if not RentalBooking.objects.filter(code=candidate).exists():
                    self.code = candidate
                    break
        super().save(*args, **kwargs)

    @property
    def payment_deadline(self):
        return self.created_at + timedelta(hours=settings.PAYMENT_TIMEOUT_HOURS)

    @property
    def is_payment_overdue(self):
        return (
            self.status == self.Status.PENDING
            and timezone.now() > self.payment_deadline
        )

    def mark_confirmed(self):
        self.status = self.Status.CONFIRMED
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at', 'updated_at'])

    def __str__(self):
        return self.code


def has_overlapping_rental(vehicle, pickup_date, return_date, *, exclude_pk=None):
    """True bila unit sudah terpesan pada rentang yang tumpang tindih.

    Tanggal sewa bersifat INKLUSIF (selaras ``RentalForm``: ambil dan
    kembali pada hari yang sama dihitung 1 hari), jadi dua rentang yang
    berbagi satu tanggal pun bertabrakan:
    ``existing.pickup <= new.return AND existing.return >= new.pickup``.
    Hanya status pengunci (PENDING/CONFIRMED) yang diperiksa.
    """
    qs = RentalBooking.objects.filter(
        vehicle=vehicle,
        status__in=RentalBooking.LOCKING_STATUSES,
        pickup_date__lte=return_date,
        return_date__gte=pickup_date,
    )
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


def expire_stale_rental_bookings() -> int:
    """Tandai EXPIRED untuk sewa PENDING yang lewat batas bayar (unit lepas).

    Dipanggil dari management command ``expire_stale_rental_bookings``
    yang dijadwalkan cron/periodic task — BUKAN dari request handler,
    agar GET halaman publik tidak menulis (UPDATE) ke database.
    """
    deadline = timezone.now() - timedelta(hours=settings.PAYMENT_TIMEOUT_HOURS)
    return RentalBooking.objects.filter(
        status=RentalBooking.Status.PENDING, created_at__lt=deadline
    ).update(status=RentalBooking.Status.EXPIRED)
