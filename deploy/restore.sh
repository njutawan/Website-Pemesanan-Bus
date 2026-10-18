#!/usr/bin/env bash
# Restore PostgreSQL + media dari backup yang dibuat deploy/backup.sh.
#
#   RESTORE_CONFIRM=YES PGHOST=... PGUSER=... PGPASSWORD=... \
#   PGDATABASE=nusantartrans MEDIA_ROOT=/var/www/.../media \
#   ./deploy/restore.sh /var/backups/nusantartrans/20261018T010203Z
#
# PERINGATAN: database tujuan akan DIHAPUS & dibuat ulang.
set -euo pipefail
umask 077

BACKUP_SRC="${1:-${BACKUP_DIR:-/var/backups/nusantartrans}/latest}"
MEDIA_ROOT="${MEDIA_ROOT:-/var/www/website-pemesanan-bus/media}"
: "${PGDATABASE:?PGDATABASE wajib diisi}"
: "${PGUSER:?PGUSER wajib diisi}"
[ "${RESTORE_CONFIRM:-}" = "YES" ] || {
  echo "Set RESTORE_CONFIRM=YES untuk benar-benar menimpa database $PGDATABASE." >&2
  exit 2
}
[ -d "$BACKUP_SRC" ] || { echo "Backup tidak ditemukan: $BACKUP_SRC" >&2; exit 1; }
cd "$BACKUP_SRC"

# 1) Integritas berkas
if [ -f SHA256SUMS ]; then sha256sum -c SHA256SUMS; else
  echo "SHA256SUMS tidak ada — menolak restore." >&2; exit 1
fi

# 2) Dekripsi bila backup terenkripsi (tetap di TMPDIR, jangan menulis
#    plaintext ke direktori backup)
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
DB_DUMP="$TMPDIR/db.dump"
MEDIA_TAR="$TMPDIR/media.tar.gz"
for f in db.dump media.tar.gz; do
  if [ -f "$f.gpg" ]; then
    command -v gpg >/dev/null || { echo "gpg tidak ditemukan" >&2; exit 1; }
    gpg --batch --quiet --yes --decrypt --output "$TMPDIR/$f" "$f.gpg"
  else
    cp "$f" "$TMPDIR/$f"
  fi
done

# 3) Validasi tar media (anti zip-slip)
if tar -tzf "$MEDIA_TAR" | grep -Eq '(^/|(^|/)\.\.(/|$))'; then
  echo "media.tar.gz berisi path tidak aman — dibatalkan." >&2; exit 1
fi

# 4) Restore database
echo "→ drop/create $PGDATABASE"
dropdb --if-exists --force "$PGDATABASE"
createdb "$PGDATABASE"
pg_restore --no-owner --no-privileges --exit-on-error -d "$PGDATABASE" "$DB_DUMP"

# 5) Restore media (simpan yang lama sebagai .pre-restore-<stamp>)
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [ -d "$MEDIA_ROOT" ] && [ "$(ls -A "$MEDIA_ROOT" 2>/dev/null || true)" ]; then
  mv "$MEDIA_ROOT" "${MEDIA_ROOT}.pre-restore-${STAMP}"
fi
mkdir -p "$MEDIA_ROOT"
tar -xzf "$MEDIA_TAR" -C "$MEDIA_ROOT" --no-same-owner --no-same-permissions

echo "✔ Restore selesai. Jalankan: python manage.py migrate --check &&"
echo "  python manage.py security_audit --no-fail"
