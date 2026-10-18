#!/usr/bin/env bash
# Pemindai rahasia: berkas ter-track + riwayat git.
# Dipakai lokal (pre-commit) dan CI. Exit 1 bila ada temuan.
#
#   ./deploy/scan_secrets.sh
#
# Sengaja TANPA dependensi (grep/git saja) agar bisa jalan di server mana pun.
set -euo pipefail
cd "$(dirname "$0")/.."

FAIL=0
note() { printf '  %s\n' "$*"; }

echo "→ 1) Berkas sensitif yang ter-track"
SENSITIVE=$(git ls-files | grep -E '(^|/)(\.env($|\.)|id_rsa|id_ed25519|\.netrc|\.pgpass|.*\.(pem|key|p12|pfx))$' \
  | grep -v -E '(^|/)\.env\.example$' || true)
if [ -n "$SENSITIVE" ]; then
  note "DITEMUKAN:"; printf '%s\n' "$SENSITIVE" | sed 's/^/    /'
  FAIL=1
else
  note "OK — tidak ada .env / kunci privat / sertifikat ter-track."
fi

echo "→ 2) Pola rahasia pada berkas ter-track (HEAD)"
# Dikecualikan: modul pemindai & dokumen keamanan yang memang memuat pola.
EXCLUDES=(
  ':!core/logging.py' ':!core/checks.py'
  ':!core/management/commands/security_review.py'
  ':!deploy/scan_secrets.sh' ':!SECURITY.md'
  ':!core/tests_security.py' ':!core/tests_hardening.py'
  ':!*.po' ':!*.mo'
)
PATTERNS=(
  'AKIA[0-9A-Z]{16}'
  'sk_live_[0-9A-Za-z]{16,}'
  'ghp_[0-9A-Za-z]{36}'
  'xox[baprs]-[0-9A-Za-z-]{10,}'
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  '(?i)api[_-]?key["'\'']?\s*[:=]\s*["'\''][A-Za-z0-9_-]{16,}'
)
for pat in "${PATTERNS[@]}"; do
  HITS=$(git grep -I -n -E -e "$pat" -- . "${EXCLUDES[@]}" 2>/dev/null || true)
  if [ -n "$HITS" ]; then
    note "DITEMUKAN pola: $pat"; printf '%s\n' "$HITS" | head -5 | sed 's/^/    /'
    FAIL=1
  fi
done
[ "$FAIL" -eq 0 ] && note "OK — tidak ada token/kunci privat di HEAD."

echo "→ 3) Riwayat git (commit lama)"
for pat in 'AKIA[0-9A-Z]{16}' 'sk_live_[0-9A-Za-z]{16,}' \
           '-----BEGIN [A-Z ]*PRIVATE KEY-----' 'ghp_[0-9A-Za-z]{36}'; do
  HITS=$(git grep -I -l -E -e "$pat" $(git rev-list --all 2>/dev/null) \
           -- ':!*.po' ':!*.mo' 2>/dev/null | head -5 || true)
  if [ -n "$HITS" ]; then
    note "DITEMUKAN di riwayat: $pat"; printf '%s\n' "$HITS" | sed 's/^/    /'
    FAIL=1
  fi
done
[ "$FAIL" -eq 0 ] && note "OK — riwayat bersih dari kunci nyata."

echo
if [ "$FAIL" -eq 0 ]; then
  echo "✔ Tidak ada rahasia terdeteksi."
else
  echo "✖ Ada rahasia/berkas sensitif — hapus dari commit dan rotasi kuncinya." >&2
fi
exit "$FAIL"
