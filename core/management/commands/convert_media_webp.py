"""Backfill: konversi gambar media lama (jpg/png) -> WebP.

python manage.py convert_media_webp

Dipakai sekali setelah pemasangan pipeline; unggahan BARU otomatis
terkonversi lewat hook di model (core.img_tools.convert_to_webp).
Bukti pembayaran tidak disentuh (dokumen legal, disimpan apa adanya).
"""
from django.core.management.base import BaseCommand

from core.img_tools import convert_to_webp
from core.models import PageMeta
from rental.models import Vehicle


class Command(BaseCommand):
    help = 'Konversi semua foto mobil & og:image lama ke WebP.'

    def handle(self, *args, **options):
        total_asli = total_baru = 0
        for model, field in ((Vehicle, 'image'), (PageMeta, 'og_image')):
            n = 0
            qs = model.objects.all()
            for obj in qs:
                f = getattr(obj, field)
                name = f.name or ''
                if not name or name.lower().endswith('.webp'):
                    continue
                try:
                    old_size = f.storage.size(name)
                except Exception:
                    continue  # berkas tidak ada di storage
                new_name = convert_to_webp(f)
                if new_name:
                    setattr(obj, field, new_name)
                    obj.save(update_fields=[field])
                    try:
                        new_size = f.storage.size(new_name)
                    except Exception:
                        new_size = 0
                    total_asli += old_size
                    total_baru += new_size
                    n += 1
            label = model.__name__
            self.stdout.write(f'  {label}.{field}: {n} berkas dikonversi')
        hemat = total_asli - total_baru
        self.stdout.write(self.style.SUCCESS(
            f'✔ Selesai. {total_asli // 1024}KB -> {total_baru // 1024}KB '
            f'(hemat {hemat // 1024}KB)'))
