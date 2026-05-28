#!/bin/bash
set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="quant_db_${TIMESTAMP}.sql.gz"
mkdir -p "$BACKUP_DIR"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-quant}" "${POSTGRES_DB:-quant}" | gzip > "${BACKUP_DIR}/${FILENAME}"

find "$BACKUP_DIR" -name "quant_db_*.sql.gz" -mtime +${RETAIN_DAYS} -delete

echo "Backup completed: ${BACKUP_DIR}/${FILENAME}"
