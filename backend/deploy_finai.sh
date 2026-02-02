#!/bin/bash
set -e

# =========================
# CONFIG
# =========================
PROJECT_DIR="/root/FinAI-v1.2/backend"
VENV_DIR="$PROJECT_DIR/venv"
DOMAIN="tadgeeg.com"
WWW_DOMAIN="www.tadgeeg.com"
SOCKET="/run/finai.sock"
EMAIL="admin@tadgeeg.com"

echo "🚀 Starting FULL Production Deployment..."

# =========================
# SYSTEM PACKAGES
# =========================
apt update -y
apt install -y python3.12 python3.12-venv python3.12-dev \
nginx git build-essential certbot python3-certbot-nginx

# =========================
# PYTHON ENV
# =========================
cd $PROJECT_DIR

if [ ! -d "$VENV_DIR" ]; then
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
# SYSTEMD – GUNICORN
# =========================
cat > /etc/systemd/system/finai.service <<EOF
[Unit]
Description=FinAI Django App
After=network.target

[Service]
User=root
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/rm -f $SOCKET
ExecStart=$VENV_DIR/bin/gunicorn FinAI.wsgi:application \
  --workers 3 \
  --bind unix:$SOCKET
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable finai
systemctl restart finai

# =========================
# NGINX (HTTP FIRST)
# =========================
cat > /etc/nginx/sites-available/finai <<EOF
server {
    listen 80;
    server_name $DOMAIN $WWW_DOMAIN;
}
EOF

ln -sf /etc/nginx/sites-available/finai /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

# =========================
# SSL (CERTBOT)
# =========================
certbot --nginx -d $DOMAIN -d $WWW_DOMAIN \
  --non-interactive --agree-tos -m $EMAIL

# =========================
# FINAL NGINX CONFIG (HTTPS)
# =========================
cat > /etc/nginx/sites-available/finai <<EOF
server {
    listen 80;
    server_name $DOMAIN $WWW_DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN $WWW_DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;

    client_max_body_size 50M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
        expires 30d;
        access_log off;
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
        expires 30d;
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_pass http://unix:$SOCKET;
    }
}
EOF

nginx -t
systemctl reload nginx
systemctl restart finai

echo "✅ DEPLOYMENT COMPLETE"
echo "🌍 https://$DOMAIN"
