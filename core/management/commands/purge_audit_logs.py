"""Hapus AuditLog yang melewati masa retensi (dijalankan cron)."""
from django.core.management.base import BaseCommand

from core.audit import purge_old_events


class Command(BaseCommand):
    help = 'Hapus jejak audit lebih lama dari AUDIT_RETENTION_DAYS (default 180).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=None,
            help='Timpa retensi (hari). Minimal 1.')

    def handle(self, *args, **options):
        deleted = purge_old_events(options.get('days'))
        self.stdout.write(self.style.SUCCESS(
            f'✔ {deleted} baris audit lama dihapus.'))
