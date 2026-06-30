#!/bin/bash
# scripts/restore_postgres.sh - Restore Postgres database from backup

set -e

BACKUP_FILE="${1:?Please provide backup file path}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "WARNING: This will restore the database from ${BACKUP_FILE}"
echo "All current data will be overwritten."
read -p "Continue? (yes/no): " confirmation

if [ "${confirmation}" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Starting restore..."

# Handle both .gz and .sql files
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    gunzip -c "${BACKUP_FILE}" | docker-compose exec -T postgres psql -U dieter dieter
else
    cat "${BACKUP_FILE}" | docker-compose exec -T postgres psql -U dieter dieter
fi

echo "Restore completed!"
