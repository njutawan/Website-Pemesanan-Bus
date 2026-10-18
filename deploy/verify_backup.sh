#!/usr/bin/env bash
# Drill restore: pulihkan backup ke database SEMENTARA lalu cek integritas.
# Database asli tidak disentuh.
#
#   PGHOST=... PGUSER=... PGPASSWORD=... ./deploy/verify_backup.sh [BACKUP_DIR]
set -euo pipefail
umask 077

BACKUP_SRC="${1:-${BACKUP_DIR:-/var/backups/nusantartrans}/latest}"
: "${PGUSER:?PGUSER wajib diisi}"
[ -d "$BACKUP_SRC" ] || { echo "Backup tidak ditemukan: $BACKUP_SRC" >&2; exit 1; }
cd "$BACKUP_SRC"
[ -f SHA256SUMS ] || { echo "SHA256SUMS tidak ada — menolak drill." >&2; exit 1; }
sha256sum -c SHA256SUMS

TMPDIR="$(mktemp -d)"
DB_DUMP="$TMPDIR/db.dump"
MEDIA_TAR="$TMPDIR/media.tar.gz"
if [ -f db.dump.gpg ]; then
  command -v gpg >/dev/null || { echo "gpg tidak ditemukan" >&2; exit 1; }
  gpg --batch --quiet --yes --decrypt --output "$DB_DUMP" db.dump.gpg
elif [ -f db.dump ]; then
  cp db.dump "$DB_DUMP"
else
  echo "db.dump tidak ada" >&2; exit 1
fi
if [ -f media.tar.gz.gpg ]; then
  gpg --batch --quiet --yes --decrypt --output "$MEDIA_TAR" media.tar.gz.gpg
elif [ -f media.tar.gz ]; then
  cp media.tar.gz "$MEDIA_TAR"
fi

TMP_DB="nusantartrans_restore_verify_$$"
trap 'dropdb --if-exists --force "$TMP_DB" >/dev/null 2>&1 || true; rm -rf "$TMPDIR"' EXIT

echo "→ restore ke database sementara $TMP_DB"
createdb "$TMP_DB"
pg_restore --no-owner --no-privileges --exit-on-error -d "$TMP_DB" "$DB_DUMP"

MIGRATIONS="$(psql -d "$TMP_DB" -Atc 'select count(*) from django_migrations;')"
BOOKINGS="$(psql -d "$TMP_DB" -Atc 'select count(*) from booking_booking;')"
RENTALS="$(psql -d "$TMP_DB" -Atc 'select count(*) from rental_rentalbooking;')"
AUDIT="$(psql -d "$TMP_DB" -Atc 'select count(*) from core_auditlog;')"

echo "  migrasi=$MIGRATIONS booking=$BOOKINGS rental=$RENTALS audit=$AUDIT"
[ "$MIGRATIONS" -gt 0 ] || { echo "Tabel migrasi kosong!" >&2; exit 1; }
[ "$BOOKINGS" -ge 0 ] && [ "$RENTALS" -ge 0 ] && [ "$AUDIT" -ge 0 ] || {
  echo "Query integritas gagal!" >&2; exit 1; }

# Cek arsip media bisa dibaca tanpa error.
if [ -f "$MEDIA_TAR" ]; then
  tar -tzf "$MEDIA_TAR" >/dev/null || { echo "media.tar.gz korup!" >&2; exit 1; }
fi

echo "✔ Drill restore BERHASIL (database asli tidak disentuh)."
