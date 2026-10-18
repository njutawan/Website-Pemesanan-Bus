"""
Kedaluwarsakan booking PENDING yang melewati batas waktu pembayaran.

Jalankan berkala (cron/periodic task), mis. tiap 5 menit:

    */5 * * * * cd /var/www/website-pemesanan-bus && \
        .venv/bin/python manage.py expire_stale_bookings

atau di Docker Compose: jadwalkan di host

    */5 * * * * docker compose -f /path/docker-compose.yml \
        exec -T web python manage.py expire_stale_bookings

Sengaja BUKAN bagian dari request handler: halaman publik (GET) tidak
boleh menulis ke database di setiap kunjungan.
"""
from django.core.management.base import BaseCommand

from booking.models import expire_stale_bookings


class Command(BaseCommand):
    help = ('Tandai EXPIRED untuk booking PENDING yang melewati batas '
            'waktu pembayaran (PAYMENT_TIMEOUT_HOURS).')

    def handle(self, *args, **options):
        count = expire_stale_bookings()
        self.stdout.write(self.style.SUCCESS(
            f'{count} booking kedaluwarsa ditandai EXPIRED.'))
