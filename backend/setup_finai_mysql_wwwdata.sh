#!/bin/bash

set -e

# ============================
# FinAI MySQL + www-data Setup
# ============================

DB_NAME="finai_db"
DB_USER="finai_user"
DB_PASS="FinAI_Strong_Pass123!"
PROJECT_PATH="/root/FinAI-v1.2/backend"
PROJECT_ROOT="/root/FinAI-v1.2"
SERVICE_NAME="finai"

echo "================================="
echo " FinAI MySQL + Permission Setup"
echo "================================="

echo "[1/9] Installing MySQL packages..."
sudo apt update
sudo apt install -y mysql-server libmysqlclient-dev pkg-config

echo "[2/9] Creating MySQL database and user..."
sudo mysql <<EOF
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "[3/9] Setting ownership to www-data..."
sudo chown -R www-data:www-data "${PROJECT_ROOT}"

echo "[4/9] Setting safe permissions..."
sudo find "${PROJECT_ROOT}" -type d -exec chmod 755 {} \;
sudo find "${PROJECT_ROOT}" -type f -exec chmod 644 {} \;

# keep executables executable if they exist
[ -f "${PROJECT_PATH}/manage.py" ] && sudo chmod 755 "${PROJECT_PATH}/manage.py"
[ -f "${PROJECT_PATH}/startup.sh" ] && sudo chmod 755 "${PROJECT_PATH}/startup.sh"

# venv binaries usually need execute bit
if [ -d "${PROJECT_PATH}/venv/bin" ]; then
  sudo find "${PROJECT_PATH}/venv/bin" -type f -exec chmod 755 {} \;
fi

# media/static writable
sudo mkdir -p "${PROJECT_PATH}/media"
sudo mkdir -p "${PROJECT_PATH}/staticfiles"
sudo chown -R www-data:www-data "${PROJECT_PATH}/media" "${PROJECT_PATH}/staticfiles"
sudo chmod -R 775 "${PROJECT_PATH}/media" "${PROJECT_PATH}/staticfiles"

echo "[5/9] Backing up old SQLite database if found..."
if [ -f "${PROJECT_PATH}/db.sqlite3" ]; then
    sudo mv "${PROJECT_PATH}/db.sqlite3" "${PROJECT_PATH}/db.sqlite3.backup.$(date +%F_%H%M%S)"
fi

echo "[6/9] Installing mysqlclient inside virtualenv..."
cd "${PROJECT_PATH}"
sudo -u www-data bash -c "source venv/bin/activate && pip install mysqlclient"

echo "[7/9] Running Django migrations..."
sudo -u www-data bash -c "cd '${PROJECT_PATH}' && source venv/bin/activate && python manage.py migrate"

echo "[8/9] Collecting static files..."
sudo -u www-data bash -c "cd '${PROJECT_PATH}' && source venv/bin/activate && python manage.py collectstatic --noinput"

echo "[9/9] Restarting services..."
sudo systemctl restart "${SERVICE_NAME}"
sudo systemctl reload nginx

echo "================================="
echo " Setup completed successfully"
echo "================================="
echo "Database : ${DB_NAME}"
echo "User     : ${DB_USER}"
echo "Project  : ${PROJECT_ROOT}"