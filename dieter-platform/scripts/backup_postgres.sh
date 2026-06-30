#!/bin/bash
# scripts/backup_postgres.sh - Backup Postgres database

set -e

BACKUP_DIR="${1:-.}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/dieter_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Starting Postgres backup..."
docker-compose exec -T postgres pg_dump -U dieter dieter | gzip > "${BACKUP_FILE}"

echo "Backup completed: ${BACKUP_FILE}"
echo "Size: $(du -h ${BACKUP_FILE} | cut -f1)"

# Keep only last 30 days of backups
find "${BACKUP_DIR}" -name "dieter_*.sql.gz" -mtime +30 -delete

echo "Old backups cleaned up."
