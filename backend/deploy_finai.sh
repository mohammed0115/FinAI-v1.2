#!/bin/bash
set -e

# ======================================================
# CONFIG
# ======================================================
PROJECT_ROOT="/root/FinAI-v1.2"
PROJECT_BACKEND="$PROJECT_ROOT/backend"
VENV_DIR="$PROJECT_BACKEND/venv"
SOCKET="/run/finai.sock"

GIT_BRANCH="main"
AUTO_UPDATE_SCRIPT="$PROJECT_ROOT/auto_update.sh"
BACKUP_DIR="/root/backups"
LOG_FILE="/var/log/finai_deploy.log"

DOMAIN="tadgeeg.com"
WWW="www.tadgeeg.com"
EMAIL="admin@tadgeeg.com"

TESSDATA="/usr/share/tesseract-ocr/4.00/tessdata"

export DJANGO_SETTINGS_MODULE="FinAI.settings.prod"
export TESSDATA_PREFIX="$TESSDATA"

mkdir -p "$BACKUP_DIR"
touch "$LOG_FILE"

exec >> "$LOG_FILE" 2>&1

echo "========== DEPLOY START $(date) =========="

# ======================================================
# SYSTEM PACKAGES (SAFE)
# ======================================================
apt update -y
apt install -y \
python3.12 python3.12-venv python3.12-dev \
nginx git build-essential \
certbot python3-certbot-nginx \
tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng \
poppler-utils

# ======================================================
# OCR ENV (SAFE)
# ======================================================
grep -q TESSDATA_PREFIX /etc/environment || echo "TESSDATA_PREFIX=$TESSDATA" >> /etc/environment

# ======================================================
# PYTHON ENV
# ======================================================
cd "$PROJECT_BACKEND"

[ -d "$VENV_DIR" ] || python3.12 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install -U pip setuptools wheel
pip install -r requirements.txt

# ======================================================
# DJANGO
# ======================================================
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# ======================================================
# SYSTEMD (GUNICORN) – SAFE
# ======================================================
if [ ! -f /etc/systemd/system/finai.service ]; then
cat > /etc/systemd/system/finai.service <<EOF
[Unit]
Description=FinAI Gunicorn
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$PROJECT_BACKEND
Environment="DJANGO_SETTINGS_MODULE=FinAI.settings.prod"
Environment="TESSDATA_PREFIX=$TESSDATA"
ExecStartPre=/bin/rm -f $SOCKET
ExecStart=$VENV_DIR/bin/gunicorn FinAI.wsgi:application \
  --workers 3 \
  --bind unix:$SOCKET \
  --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable finai
fi

systemctl restart finai

# ======================================================
# NGINX CONFIG (SAFE)
# ======================================================
if [ ! -f /etc/nginx/sites-available/finai ]; then
cat > /etc/nginx/sites-available/finai <<EOF
server {
    listen 80;
    server_name $DOMAIN $WWW;
    return 301 https://$DOMAIN\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN $WWW;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;

    client_max_body_size 50M;

    location /static/ {
        alias $PROJECT_BACKEND/staticfiles/;
        expires 30d;
        access_log off;
    }

    location /media/ {
        alias $PROJECT_BACKEND/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$SOCKET;
    }
}
EOF

ln -sf /etc/nginx/sites-available/finai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
fi

# ======================================================
# SSL (SAFE)
# ======================================================
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
certbot --nginx \
  -d "$DOMAIN" -d "$WWW" \
  --non-interactive \
  --agree-tos \
  -m "$EMAIL"
fi

# ======================================================
# AUTO UPDATE + ROLLBACK SCRIPT (CREATE ONCE)
# ======================================================
if [ ! -f "$AUTO_UPDATE_SCRIPT" ]; then
cat > "$AUTO_UPDATE_SCRIPT" <<'EOF'
#!/bin/bash
set -e

PROJECT_ROOT="/root/FinAI-v1.2"
BACKUP_DIR="/root/backups"
BRANCH="main"
DEPLOY="./deploy.sh"
LOG="/var/log/finai_auto_update.log"

exec >> "$LOG" 2>&1

cd "$PROJECT_ROOT"

git fetch origin "$BRANCH"

LOCAL=$(git rev-parse "$BRANCH")
REMOTE=$(git rev-parse "origin/$BRANCH")

[ "$LOCAL" = "$REMOTE" ] && exit 0

STAMP=$(date +%F_%H-%M-%S)
BACKUP="$BACKUP_DIR/finai_$STAMP.tar.gz"

# =========================
# BACKUP
# =========================
tar -czf "$BACKUP" --exclude=.git .

# =========================
# STASH BEFORE PULL
# =========================
git stash push -u -m "auto-stash-before-pull-$STAMP"

# =========================
# PULL
# =========================
if ! git pull origin "$BRANCH"; then
  git stash pop || true
  tar -xzf "$BACKUP" -C "$PROJECT_ROOT"
  exit 1
fi

chmod +x "$DEPLOY"

# =========================
# DEPLOY
# =========================
if ! "$DEPLOY"; then
  git stash pop || true
  tar -xzf "$BACKUP" -C "$PROJECT_ROOT"
  systemctl restart finai
  systemctl restart nginx
  exit 1
fi

# =========================
# CLEAN STASH (SUCCESS)
# =========================
git stash drop || true

EOF

chmod +x "$AUTO_UPDATE_SCRIPT"
fi

# ======================================================
# CRON JOB (SAFE)
# ======================================================
CRON="*/5 * * * * $AUTO_UPDATE_SCRIPT"
(crontab -l 2>/dev/null | grep -v auto_update.sh; echo "$CRON") | crontab -

echo "========== DEPLOY END $(date) =========="
