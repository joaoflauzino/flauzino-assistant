#!/usr/bin/env bash
# ==============================================================================
# Flauzino Assistant - Automated Backup & Retention with Rclone (OneDrive)
# ==============================================================================
set -euo pipefail

# Ensure standard binaries are in PATH (crucial for cron / systemd)
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# Resolve absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"

# Load environment variables if .env exists
if [ -f "$ENV_FILE" ]; then
  # Export non-comment lines
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# Configurable variables with defaults
POSTGRES_USER="${POSTGRES_USER:-flauzino}"
POSTGRES_DB="${POSTGRES_DB:-assistant}"
CONTAINER_DB="${CONTAINER_DB:-infra-db-1}"
RCLONE_REMOTE="${RCLONE_REMOTE:-onedrive:flauzino-backups}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
DISK_ALERT_THRESHOLD="${DISK_ALERT_THRESHOLD:-85}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_DAY=$(date +"%Y%m%d")

# Local directories
DIR_PG="$BACKUP_DIR/postgres"
DIR_LOGS="$BACKUP_DIR/logs"
mkdir -p "$DIR_PG" "$DIR_LOGS"

# ------------------------------------------------------------------------------
# Helper: Send Telegram Notification
# ------------------------------------------------------------------------------
send_telegram() {
  local message="$1"
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      -d "parse_mode=Markdown" \
      -d "text=${message}" > /dev/null 2>&1 || true
  fi
}

# Trap unexpected errors
on_error() {
  local exit_code=$?
  local line_no=$1
  echo "[ERROR] Backup failed at line $line_no with status $exit_code"
  send_telegram "❌ *Flauzino Backup: FALHA!*%0AErro na linha $line_no (status: $exit_code). Verifique os logs no Raspberry Pi."
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Iniciando Rotina de Backup ==="

# ------------------------------------------------------------------------------
# 1. Health check de Espaço em Disco
# ------------------------------------------------------------------------------
echo "1. Verificando espaço em disco no host..."
DISK_USAGE=$(df -P "$BACKUP_DIR" | awk 'NR==2 {gsub("%","",$5); print $5}')
echo "Uso atual do disco: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -ge "$DISK_ALERT_THRESHOLD" ]; then
  echo "[ALERTA] Uso de disco crítico: ${DISK_USAGE}%!"
  send_telegram "⚠️ *Flauzino Alerta de Armazenamento!*%0AO disco do Raspberry Pi atingiu *${DISK_USAGE}%* de capacidade (limite: ${DISK_ALERT_THRESHOLD}%). Verifique o MicroSD!"
fi

# ------------------------------------------------------------------------------
# 2. Backup do PostgreSQL (Snapshot Custom Compactado)
# ------------------------------------------------------------------------------
echo "2. Gerando dump do banco PostgreSQL ($POSTGRES_DB)..."
DUMP_FILE="$DIR_PG/db_backup_${TIMESTAMP}.dump"

# Check if db container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_DB}$"; then
  echo "[ERRO] Container de banco '$CONTAINER_DB' não está em execução!"
  exit 1
fi

docker exec "$CONTAINER_DB" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c > "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "Dump gerado com sucesso: $DUMP_FILE ($DUMP_SIZE)"

# ------------------------------------------------------------------------------
# 3. Coleta e Compressão de Logs dos Containers (últimas 24h)
# ------------------------------------------------------------------------------
echo "3. Coletando logs das aplicações..."
LOG_ARCHIVE="$DIR_LOGS/apps_logs_${DATE_DAY}.tar.gz"
TEMP_LOG_DIR=$(mktemp -d)

CONTAINERS=("infra-agent_api-1" "infra-finance_api-1" "infra-telegram_bot-1" "infra-graph_api-1" "infra-frontend-1" "infra-db-1")
COLLECTED_COUNT=0

for c_name in "${CONTAINERS[@]}"; do
  if docker ps -a --format '{{.Names}}' | grep -q "^${c_name}$"; then
    docker logs --since 24h "$c_name" > "$TEMP_LOG_DIR/${c_name}.log" 2>&1 || true
    COLLECTED_COUNT=$((COLLECTED_COUNT + 1))
  fi
done

if [ "$COLLECTED_COUNT" -gt 0 ]; then
  tar -czf "$LOG_ARCHIVE" -C "$TEMP_LOG_DIR" .
  echo "Logs compactados em: $LOG_ARCHIVE ($(du -h "$LOG_ARCHIVE" | cut -f1))"
fi
rm -rf "$TEMP_LOG_DIR"

# ------------------------------------------------------------------------------
# 4. Sincronização com o Microsoft OneDrive via Rclone
# ------------------------------------------------------------------------------
echo "4. Sincronizando com o OneDrive ($RCLONE_REMOTE)..."

if command -v rclone &>/dev/null; then
  echo "Enviando dumps do PostgreSQL..."
  rclone copy "$DIR_PG/" "${RCLONE_REMOTE}/postgres/"

  echo "Enviando arquivos de logs..."
  rclone copy "$DIR_LOGS/" "${RCLONE_REMOTE}/logs/"

  # ----------------------------------------------------------------------------
  # 5. Políticas de Retenção Remota (OneDrive)
  # ----------------------------------------------------------------------------
  echo "5. Aplicando políticas de expiração no OneDrive..."
  # PostgreSQL: retenção de 6 meses (180 dias)
  rclone delete "${RCLONE_REMOTE}/postgres/" --min-age 180d --rmdirs || true

  # Logs: retenção de 1 mês (30 dias)
  rclone delete "${RCLONE_REMOTE}/logs/" --min-age 30d --rmdirs || true
else
  echo "[AVISO] Binário 'rclone' não encontrado no PATH. Pulando sincronização remota."
fi

# ------------------------------------------------------------------------------
# 6. Políticas de Retenção Local (Raspberry Pi)
# ------------------------------------------------------------------------------
echo "6. Aplicando políticas de expiração local no Raspberry Pi..."
# Manter 6 meses (180 dias) de dumps do banco localmente
find "$DIR_PG" -name "db_backup_*.dump" -type f -mtime +180 -delete

# Manter 7 dias de logs compactados localmente
find "$DIR_LOGS" -name "apps_logs_*.tar.gz" -type f -mtime +7 -delete

echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Backup concluído com sucesso! ==="

# Enviar notificação de sucesso resumida
send_telegram "✅ *Flauzino Backup: Sucesso!*%0A• Banco: \`${POSTGRES_DB}\` (${DUMP_SIZE})%0A• Retenção DB: 180 dias%0A• Retenção Logs: 30 dias%0A• Disco RPi: ${DISK_USAGE}% usado"
