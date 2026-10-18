"""Model inti pemesanan tiket bus: kota, rute, bus, kursi, jadwal, booking."""
import secrets
import string
from datetime import timedelta

from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

ALPHABET = string.ascii_uppercase + string.digits  # tanpa simbol
AMBIGUOUS = set('O0I1')  # dihilangkan dari kode booking agar tidak tertukar


def generate_code(prefix: str, length: int = 8) -> str:
    chars = [c for c in ALPHABET if c not in AMBIGUOUS]
    body = ''.join(secrets.choice(chars) for _ in range(length))
    return f'{prefix}-{body}'


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_('dibuat'), auto_now_add=True)
    updated_at = models.DateTimeField(_('diperbarui'), auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------
class City(models.Model):
    name = models.CharField(_('nama kota'), max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    province = models.CharField(_('provinsi'), max_length=100)
    is_popular = models.BooleanField(_('kota populer'), default=False)

    class Meta:
        verbose_name = _('kota')
        verbose_name_plural = _('kota-kota')
        ordering = ['name']

    def __str__(self):
        return self.name


class Route(TimeStampedModel):
    origin = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name='departures', verbose_name=_('kota asal'))
    destination = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name='arrivals', verbose_name=_('kota tujuan'))
    distance_km = models.PositiveIntegerField(_('jarak (km)'))
    duration_minutes = models.PositiveIntegerField(_('durasi (menit)'))
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        verbose_name = _('rute')
        verbose_name_plural = ('rute-rute')
        unique_together = [('origin', 'destination')]
        ordering = ['origin__name', 'destination__name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = f'{self.origin.slug}-{self.destination.slug}'
            slug, i = base, 2
            while Route.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        # URL hierarkis: /bus/rute/dari/<asal>/<tujuan>/ — kategori di depan
        from django.urls import reverse
        return reverse('booking:route_detail', kwargs={
            'city_slug': self.origin.slug, 'dest_slug': self.destination.slug})

    @property
    def duration_display(self):
        h, m = divmod(self.duration_minutes, 60)
        return f'{h}h {m}m'

    def __str__(self):
        return f'{self.origin.name} → {self.destination.name}'


class Bus(TimeStampedModel):
    """Armada bus. Layout kursi mengikuti kelas layanan."""

    class BusClass(models.TextChoices):
        ECONOMY = 'EKONOMI', _('Ekonomi')
        AC = 'AC', _('AC')
        EXECUTIVE = 'EKSEKUTIF', _('Eksekutif')
        SLEEPER = 'SLEEPER', _('Sleeper')

    # jumlah kolom kursi per baris (di luar lorong): 2-2, 2-1, 1-1
    CLASS_COLUMNS = {
        BusClass.ECONOMY: 4,
        BusClass.AC: 4,
        BusClass.EXECUTIVE: 3,
        BusClass.SLEEPER: 2,
    }
    CLASS_ICONS = {
        BusClass.ECONOMY: 'fa-chair',
        BusClass.AC: 'fa-snowflake',
        BusClass.EXECUTIVE: 'fa-crown',
        BusClass.SLEEPER: 'fa-bed',
    }

    code = models.CharField(_('kode armada'), max_length=20, unique=True)
    name = models.CharField(_('nama armada'), max_length=100)
    plate_number = models.CharField(_('nomor polisi'), max_length=15, unique=True)
    bus_class = models.CharField(_('kelas'), max_length=12, choices=BusClass.choices)
    rows = models.PositiveIntegerField(_('jumlah baris'), default=10)
    amenities = models.CharField(
        _('fasilitas'), max_length=255, blank=True,
        help_text=_('Pisahkan dengan koma, mis. "AC, WiFi, Toilet, Snack"'))
    is_active = models.BooleanField(_('aktif'), default=True)

    class Meta:
        verbose_name = _('bus')
        verbose_name_plural = ('bus-bus')
        ordering = ['code']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.seats.exists():
            self.generate_seats()

    @property
    def columns(self):
        return self.CLASS_COLUMNS.get(self.bus_class, 4)

    @property
    def aisle_after(self):
        """Kolom terakhir sebelum lorong (untuk gambar denah kursi)."""
        return (self.columns + 1) // 2

    @property
    def total_seats(self):
        return self.seats.count()

    def generate_seats(self):
        cols = self.columns
        labels = 'ABCDEFGH'
        seats = [
            Seat(bus=self, row=row, col=col, label=f'{row}{labels[col - 1]}')
            for row in range(1, self.rows + 1)
            for col in range(1, cols + 1)
        ]
        Seat.objects.bulk_create(seats)

    def amenity_list(self):
        return [a.strip() for a in self.amenities.split(',') if a.strip()]

    def __str__(self):
        return f'{self.name} ({self.plate_number})'


class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seats')
    label = models.CharField(_('label kursi'), max_length=4)
    row = models.PositiveSmallIntegerField(_('baris'))
    col = models.PositiveSmallIntegerField(_('kolom'))

    class Meta:
        verbose_name = _('kursi')
        verbose_name_plural = ('kursi-kursi')
        unique_together = [('bus', 'label')]
        ordering = ['row', 'col']

    def __str__(self):
        return f'{self.bus.code}-{self.label}'


class Schedule(TimeStampedModel):
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name='schedules', verbose_name=_('rute'))
    bus = models.ForeignKey(
        Bus, on_delete=models.PROTECT, related_name='schedules', verbose_name=_('bus'))
    departure_time = models.TimeField(_('jam berangkat'), db_index=True)
    arrival_time = models.TimeField(_('jam tiba'))
    price = models.DecimalField(_('harga'), max_digits=12, decimal_places=0)
    is_active = models.BooleanField(_('aktif'), default=True, db_index=True)

    class Meta:
        verbose_name = _('jadwal')
        verbose_name_plural = ('jadwal-jadwal')
        ordering = ['departure_time']

    @property
    def arrives_next_day(self):
        return self.arrival_time <= self.departure_time

    @property
    def bus_total_seats(self):
        """Jumlah kursi bus — dari annotate(Count) bila ada (anti N+1)."""
        n = getattr(self, 'bus_seat_count', None)
        return self.bus.total_seats if n is None else n

    @property
    def duration_minutes(self):
        dep = self.departure_time.hour * 60 + self.departure_time.minute
        arr = self.arrival_time.hour * 60 + self.arrival_time.minute
        return (arr - dep) % (24 * 60) or 24 * 60

    @property
    def duration_display(self):
        h, m = divmod(self.duration_minutes, 60)
        return f'{h}j {m}m' if m else f'{h}j'

    def __str__(self):
        return f'{self.route} · {self.departure_time:%H:%M} · {self.bus.code}'


# ---------------------------------------------------------------------------
# Pemesanan
# ---------------------------------------------------------------------------
class Booking(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Menunggu pembayaran')
        CONFIRMED = 'CONFIRMED', _('Terkonfirmasi')
        CANCELLED = 'CANCELLED', _('Dibatalkan')
        EXPIRED = 'EXPIRED', _('Kedaluwarsa')

    # Status yang masih "mengunci" kursi
    LOCKING_STATUSES = [Status.PENDING, Status.CONFIRMED]

    code = models.CharField(_('kode booking'), max_length=16, unique=True, db_index=True)
    schedule = models.ForeignKey(
        Schedule, on_delete=models.PROTECT, related_name='bookings', verbose_name=_('jadwal'))
    travel_date = models.DateField(_('tanggal perjalanan'))
    contact_name = models.CharField(_('nama pemesan'), max_length=100)
    contact_phone = models.CharField(_('no. WhatsApp'), max_length=20)
    contact_email = models.EmailField(_('email'), blank=True)
    seats_qty = models.PositiveSmallIntegerField(_('jumlah kursi'), default=1)
    total_price = models.DecimalField(_('total harga'), max_digits=12, decimal_places=0)
    status = models.CharField(
        _('status'), max_length=12, choices=Status.choices, default=Status.PENDING,
        db_index=True)
    payment_method = models.CharField(_('metode pembayaran'), max_length=20, blank=True)
    payment_proof = models.ImageField(
        _('bukti pembayaran'), upload_to='payment_proofs/%Y/%m/', blank=True, null=True)
    paid_at = models.DateTimeField(_('dibayar pada'), null=True, blank=True)
    admin_note = models.TextField(_('catatan admin'), blank=True)

    class Meta:
        verbose_name = _('booking tiket')
        verbose_name_plural = ('booking tiket')
        ordering = ['-created_at']
        indexes = [
            # Cek ketersediaan kursi: filter(schedule=, travel_date=, status__in=)
            models.Index(fields=['schedule', 'travel_date'], name='booking_sched_date_ix'),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            for _ in range(10):
                candidate = generate_code('NT')
                if not Booking.objects.filter(code=candidate).exists():
                    self.code = candidate
                    break
        super().save(*args, **kwargs)

    @property
    def payment_deadline(self):
        from django.conf import settings
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


class BookingSeat(models.Model):
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='seat_items')
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT)

    class Meta:
        verbose_name = _('kursi booking')
        verbose_name_plural = ('kursi booking')
        unique_together = [('booking', 'seat')]

    def __str__(self):
        return f'{self.booking.code} · {self.seat.label}'


# ---------------------------------------------------------------------------
# Helper ketersediaan kursi
# ---------------------------------------------------------------------------
def taken_seat_ids(schedule: Schedule, travel_date) -> set:
    """Kumpulan id Seat yang sudah terkunci utk jadwal+tanggal (PENDING/CONFIRMED)."""
    return set(
        BookingSeat.objects
        .filter(
            booking__schedule=schedule,
            booking__travel_date=travel_date,
            booking__status__in=Booking.LOCKING_STATUSES,
        )
        .values_list('seat_id', flat=True)
    )


def available_seat_count(schedule: Schedule, travel_date) -> int:
    taken = taken_seat_ids(schedule, travel_date)
    # bus_total_seats memakai hasil annotate(bus_seat_count=Count(...))
    # bila tersedia; bus.total_seats selalu menembak COUNT kursi baru.
    return max(schedule.bus_total_seats - len(taken), 0)


def taken_seat_counts(schedule_ids, travel_date) -> dict:
    """Peta ``{schedule_id: jumlah kursi terkunci}`` dalam SATU query agregat.

    Pasangan untuk daftar jadwal (hasil pencarian): menggantikan pola
    memanggil available_seat_count()/taken_seat_ids() per jadwal (N+1).
    DISTINCT menjaga semantik taken_seat_ids (kursi yang sama, walau
    tercatat di lebih dari satu booking, tetap dihitung sekali).
    """
    ids = [getattr(s, 'pk', s) for s in schedule_ids]
    if not ids:
        return {}
    rows = (
        BookingSeat.objects
        .filter(
            booking__schedule_id__in=ids,
            booking__travel_date=travel_date,
            booking__status__in=Booking.LOCKING_STATUSES,
        )
        .values('booking__schedule_id')
        .annotate(n=Count('seat', distinct=True))
    )
    return {row['booking__schedule_id']: row['n'] for row in rows}


def expire_stale_bookings() -> int:
    """Tandai EXPIRED untuk booking PENDING yang lewat batas bayar (kursi otomatis lepas).

    Dipanggil dari management command ``expire_stale_bookings`` yang
    dijadwalkan cron/periodic task — BUKAN dari request handler, agar
    GET halaman publik tidak menulis (UPDATE) ke database.
    """
    from django.conf import settings
    deadline = timezone.now() - timedelta(hours=settings.PAYMENT_TIMEOUT_HOURS)
    return Booking.objects.filter(
        status=Booking.Status.PENDING, created_at__lt=deadline
    ).update(status=Booking.Status.EXPIRED)


def seats_taken_q(schedule, travel_date):
    """Q object utk meng-join booking aktif (dipakai di query kompleks bila perlu)."""
    return Q(
        booking__schedule=schedule,
        booking__travel_date=travel_date,
        booking__status__in=Booking.LOCKING_STATUSES,
    )
