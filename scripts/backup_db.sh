#!/bin/bash
# ============================================================
# Hawassa Dispatch System — Automatic Database Backup Script
# ============================================================
# Backs up SQLite database using online atomic backup API.
# Retains last 7 days of daily backups.
# ============================================================

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${APP_DIR}/backups"
DB_PATH="${APP_DIR}/hawassa_places.db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/hawassa_places_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found at $DB_PATH" >&2
    exit 1
fi

# Execute non-blocking online atomic SQLite backup
sqlite3 "$DB_PATH" ".backup '${BACKUP_FILE}'"

# Ensure proper permissions
chmod 600 "$BACKUP_FILE"

# Rotate: remove backups older than 7 days
find "$BACKUP_DIR" -name "hawassa_places_*.db" -type f -mtime +7 -delete

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database backup succeeded: ${BACKUP_FILE}"
