# Backup & Restore — Nusantara Trans

RPO yang disarankan: **≤ 24 jam** (backup harian) dan **≤ 15 menit** bila
memakai WAL archiving. RTO target: **≤ 2 jam**.

## 1. Backup harian (cron)

```cron
15 2 * * * cd /var/www/website-pemesanan-bus && \
  set -a; . /etc/nusantartrans/backup.env; set +a; \
  ./deploy/backup.sh >> /var/log/nusantartrans-backup.log 2>&1
```

`/etc/nusantartrans/backup.env` (root, mode 600) berisi `PGHOST`,
`PGUSER`, `PGPASSWORD`, `PGDATABASE`, `MEDIA_ROOT`, `BACKUP_DIR`.
Enkripsi opsional: `BACKUP_GPG_RECIPIENT=ops@example.com`.

Simpan salinan **di luar server** (S3/B2/rsync) — backup di host yang sama
tidak melindungi dari kehilangan disk/ransomware.

## 2. Drill restore (WAJIB berkala, mis. bulanan)

```bash
set -a; . /etc/nusantartrans/backup.env; set +a
./deploy/verify_backup.sh /var/backups/nusantartrans/latest
```

Skrip membuat database sementara, `pg_restore`, menghitung tabel penting,
menguji arsip media, lalu menghapus database sementara. Output `✔ Drill
restore BERHASIL` adalah bukti restore teruji — bukan sekadar "backup ada".

## 3. Restore ke produksi (insiden)

```bash
set -a; . /etc/nusantartrans/backup.env; set +a
sudo systemctl stop nusantartrans
RESTORE_CONFIRM=YES ./deploy/restore.sh /var/backups/nusantartrans/latest
sudo systemctl start nusantartrans
python manage.py migrate --check
python manage.py security_audit --no-fail
```

`restore.sh` memverifikasi SHA256, menolak tar dengan path `../`/absolut,
menyimpan media lama sebagai `media.pre-restore-<stamp>`, dan memakai
`--exit-on-error` agar restore gagal keras, bukan setengah jalan.

## 4. Checklist bukti audit

- [ ] Backup harian sukses 7 hari terakhir
- [ ] Checksum `SHA256SUMS` valid
- [ ] Drill `verify_backup.sh` sukses ≤ 30 hari terakhir
- [ ] Salinan off-site terbaru < 24 jam
- [ ] Password backup/GPG disimpan di secret manager
- [ ] Restore tahunan diuji di lingkungan staging
