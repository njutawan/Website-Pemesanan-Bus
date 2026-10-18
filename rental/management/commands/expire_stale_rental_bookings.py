"""
Kedaluwarsakan pesanan sewa PENDING yang melewati batas waktu pembayaran.

Jalankan berkala (cron/periodic task) bersama perintah kedaluwarsa
booking bus, mis. tiap 5 menit:

    */5 * * * * cd /var/www/website-pemesanan-bus && \
        .venv/bin/python manage.py expire_stale_bookings && \
        .venv/bin/python manage.py expire_stale_rental_bookings

Sengaja BUKAN bagian dari request handler: halaman publik (GET) tidak
boleh menulis ke database di setiap kunjungan.
"""
from django.core.management.base import BaseCommand

from rental.models import expire_stale_rental_bookings


class Command(BaseCommand):
    help = ('Tandai EXPIRED untuk pesanan sewa PENDING yang melewati '
            'batas waktu pembayaran (PAYMENT_TIMEOUT_HOURS).')

    def handle(self, *args, **options):
        count = expire_stale_rental_bookings()
        self.stdout.write(self.style.SUCCESS(
            f'{count} pesanan sewa kedaluwarsa ditandai EXPIRED.'))
