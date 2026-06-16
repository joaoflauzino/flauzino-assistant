#!/bin/bash
# Database backup script for Flauzino Assistant
# This script should be run periodically via cron on the Raspberry Pi.

# Resolve absolute path to the backups directory based on script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.dump"

# Execute pg_dump inside the db container
echo "Starting backup of database 'assistant' to $BACKUP_FILE..."

# container name is based on your folder name (infra-db-1)
docker exec -t infra-db-1 pg_dump -U flauzino -d assistant -F c > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    
    # Optional: If you want to automatically clean up old backups (older than 7 days)
    find "$BACKUP_DIR" -name "db_backup_*.dump" -type f -mtime +7 -delete
    
else
    echo "Backup failed!"
    exit 1
fi
