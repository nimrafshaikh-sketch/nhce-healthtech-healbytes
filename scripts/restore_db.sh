#!/usr/bin/env bash
# Safe PostgreSQL restore script for HealBytes.
# Requires explicit --confirm-restore to prevent accidental overwrite.
# Usage:
#   ./scripts/restore_db.sh ./backups/healbytes_20261118_120000.dump --confirm-restore

set -euo pipefail

if [ "$#" -lt 2 ] || [ "$2" != "--confirm-restore" ]; then
  echo "Usage: $0 <backup.dump> --confirm-restore" >&2
  echo "Refusing to overwrite database without explicit --confirm-restore confirmation." >&2
  exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="${POSTGRES_CONTAINER:-healbytes_db}"
DB_NAME="${POSTGRES_DB:-healbytes}"
DB_USER="${POSTGRES_USER:-healbytes}"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "[restore_db] ERROR: Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

echo "[restore_db] Restoring '${BACKUP_FILE}' into '${DB_NAME}'..."

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  docker exec -i "${CONTAINER_NAME}" pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner < "${BACKUP_FILE}"
else
  pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner "${BACKUP_FILE}"
fi

echo "[restore_db] Restore completed cleanly."

