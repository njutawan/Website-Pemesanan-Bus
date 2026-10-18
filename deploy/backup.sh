#!/usr/bin/env bash
# Backup PostgreSQL + media Nusantara Trans.
#
# WAJIB via env (jangan taruh password di argumen/command line):
#   PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
#   MEDIA_ROOT=/var/www/website-pemesanan-bus/media
#   BACKUP_DIR=/var/backups/nusantartrans (opsional)
#   BACKUP_RETENTION_DAYS=14 (opsional)
#   BACKUP_GPG_RECIPIENT=... (opsional, enkripsi GPG)
#
# Hasil: $BACKUP_DIR/<UTC timestamp>/{db.dump,media.tar.gz,SHA256SUMS}
set -euo pipefail
umask 077

: "${PGDATABASE:?PGDATABASE wajib diisi}"
: "${PGUSER:?PGUSER wajib diisi}"
MEDIA_ROOT="${MEDIA_ROOT:-/var/www/website-pemesanan-bus/media}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/nusantartrans}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${BACKUP_DIR}/${STAMP}"

command -v pg_dump >/dev/null || { echo "pg_dump tidak ditemukan" >&2; exit 1; }
[ -d "$MEDIA_ROOT" ] || { echo "MEDIA_ROOT tidak ada: $MEDIA_ROOT" >&2; exit 1; }
mkdir -p "$BACKUP_DIR"
[ ! -e "$DEST" ] || { echo "Direktori backup sudah ada: $DEST" >&2; exit 1; }
mkdir -p "$DEST"

cleanup() {
  # Jangan tinggalkan backup setengah jadi.
  if [ "${SUCCESS:-0}" != "1" ]; then rm -rf "$DEST"; fi
}
trap cleanup EXIT

echo "→ pg_dump $PGDATABASE"
pg_dump --format=custom --no-owner --no-privileges --file="$DEST/db.dump"

echo "→ tar media"
tar -czf "$DEST/media.tar.gz" -C "$MEDIA_ROOT" .

if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
  command -v gpg >/dev/null || { echo "gpg tidak ditemukan" >&2; exit 1; }
  echo "→ enkripsi GPG"
  for f in "$DEST/db.dump" "$DEST/media.tar.gz"; do
    gpg --batch --yes --encrypt --recipient "$BACKUP_GPG_RECIPIENT" "$f"
    rm -f "$f"
  done
fi

( cd "$DEST" && sha256sum ./* > SHA256SUMS )

# Salin metadata skema untuk audit restore.
psql -Atc "select version();" > "$DEST/postgres-version.txt" 2>/dev/null || true
psql -Atc "select count(*) from django_migrations;" > "$DEST/migrations-count.txt" 2>/dev/null || true

ln -sfn "$STAMP" "$BACKUP_DIR/latest"
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d \
     -not -name "$STAMP" -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

SUCCESS=1
echo "✔ Backup selesai: $DEST"
( cd "$DEST" && sha256sum -c SHA256SUMS )
