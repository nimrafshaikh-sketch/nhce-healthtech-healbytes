#!/usr/bin/env bash
# Automated PostgreSQL backup script for HealBytes (Docker or direct host).
# Usage:
#   ./scripts/backup_db.sh
#   RETENTION_DAYS=30 BACKUP_DIR=/var/backups/healbytes ./scripts/backup_db.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
CONTAINER_NAME="${POSTGRES_CONTAINER:-healbytes_db}"
DB_NAME="${POSTGRES_DB:-healbytes}"
DB_USER="${POSTGRES_USER:-healbytes}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "[backup_db] Starting PostgreSQL backup of '${DB_NAME}' -> ${OUT_FILE}"

if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -qx "${CONTAINER_NAME}"; then
  docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --format=custom --compress=9 > "${OUT_FILE}"
  # Verify archive integrity via pg_restore --list inside container
  docker exec -i "${CONTAINER_NAME}" pg_restore --list < "${OUT_FILE}" > /dev/null
else
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" --format=custom --compress=9 -f "${OUT_FILE}"
  pg_restore --list "${OUT_FILE}" > /dev/null
fi

if [ ! -s "${OUT_FILE}" ]; then
  echo "[backup_db] ERROR: Backup file is empty: ${OUT_FILE}" >&2
  rm -f "${OUT_FILE}"
  exit 1
fi

SIZE_BYTES="$(wc -c < "${OUT_FILE}")"
echo "[backup_db] Verified backup archive (${SIZE_BYTES} bytes): ${OUT_FILE}"

# Prune backups older than RETENTION_DAYS
find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${DB_NAME}_*.dump" -mtime "+${RETENTION_DAYS}" -delete
echo "[backup_db] Retention cleanup complete (kept last ${RETENTION_DAYS} days)."

