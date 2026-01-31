#!/bin/bash
set -e

# =========================
# CONFIGURATION
# =========================
PROJECT_DIR="/root/FinAI-v1.2/backend"
VENV_DIR="/root/FinAI-v1.2/backend/venv"
DOMAIN_OR_IP="72.62.239.220"
GUNICORN_SOCKET="/run/finai.sock"

echo "🚀 Starting FinAI Deployment..."

# =========================
# SYSTEM PACKAGES
# =========================
apt update -y
apt install -y python3.12 python3.12-venv python3.12-dev \
nginx git build-essential

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
# SYSTEMD SERVICE
# =========================
cat > /etc/systemd/system/finai.service <<EOF
[Unit]
Description=FinAI Django Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
ExecStartPre=/bin/rm -f /run/finai.sock
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
# NGINX
# =========================
cat > /etc/nginx/sites-available/finai <<EOF
server {
    listen 80;
    server_name $DOMAIN_OR_IP;

    client_max_body_size 50M;

    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
    }

    location /media/ {
        alias $PROJECT_DIR/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$GUNICORN_SOCKET;
    }
}
EOF

ln -sf /etc/nginx/sites-available/finai /etc/nginx/sites-enabled/finai
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl restart nginx

echo "✅ FinAI Deployment Completed Successfully"
echo "🌍 Open: http://$DOMAIN_OR_IP"
