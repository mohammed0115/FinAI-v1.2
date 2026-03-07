#!/bin/bash
set -e

# =========================
# CONFIGURATION
# =========================
PROJECT_DIR="/root/FinAI-v1.2/backend"
VENV_DIR="$PROJECT_DIR/venv"
DOMAIN="tadgeeg.com"
WWW_DOMAIN="www.tadgeeg.com"
GUNICORN_SOCKET="/run/finai.sock"
EMAIL="admin@tadgeeg.com"

echo "🚀 Starting FinAI Full Deployment with SSL..."

# =========================
# SYSTEM PACKAGES
# =========================
apt update -y
apt install -y python3.12 python3.12-venv python3.12-dev \
nginx git build-essential certbot python3-certbot-nginx

# =========================
# VIRTUAL ENV
# =========================
cd $PROJECT_DIR

if [ ! -d "$VENV_DIR" ]; then
  echo "🐍 Creating virtual environment..."
  python3.12 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# =========================
# DJANGO
# =========================
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# =========================
# SYSTEMD - GUNICORN
# =========================
cat > /etc/systemd/system/finai.service <<EOF
[Unit]
Description=FinAI Django Application
After=network.target

[Service]
User=root
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/rm -f $GUNICORN_SOCKET
ExecStart=$VENV_DIR/bin/gunicorn FinAI.wsgi:application \
    --workers 3 \
    --bind unix:$GUNICORN_SOCKET \
    --umask 007
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable finai
systemctl restart finai

# =========================
# NGINX (HTTP only first)
# =========================
cat > /etc/nginx/sites-available/finai <<EOF
server {
    listen 80;
    server_name $DOMAIN $WWW_DOMAIN;

    client_max_body_size 50M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
    }

    location / {
        proxy_pass http://unix:$GUNICORN_SOCKET;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }
}
EOF

ln -sf /etc/nginx/sites-available/finai /etc/nginx/sites-enabled/finai
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

# =========================
# SSL - CERTBOT
# =========================
echo "🔐 Issuing SSL certificate..."
certbot --nginx \
  -d $DOMAIN \
  -d $WWW_DOMAIN \
  --non-interactive \
  --agree-tos \
  -m $EMAIL \
  --redirect

# =========================
# FINAL RELOAD
# =========================
nginx -t
systemctl reload nginx

echo "✅ Deployment completed successfully!"
echo "🌍 https://$DOMAIN"
