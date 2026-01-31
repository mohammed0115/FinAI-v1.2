#!/bin/bash
set -e

# =========================
# CONFIGURATION
# =========================
PROJECT_NAME="FinAI"
PROJECT_DIR="/root/FinAI-v1.2/backend"
VENV_DIR="FinAI-v1.2/venv"
DJANGO_SETTINGS_MODULE="config.settings"
DOMAIN_OR_IP="72.62.239.220"
USER_NAME="root"
GUNICORN_SOCKET="/run/finai.sock"

echo "🚀 Starting FinAI Deployment..."

# =========================
# SYSTEM UPDATE
# =========================
sudo apt update -y
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
git nginx ufw build-essential

# =========================
# VIRTUAL ENV
# =========================
if [ ! -d "$VENV_DIR" ]; then
  echo "🐍 Creating virtual environment..."
  python3.12 -m venv $VENV_DIR
fi

source $VENV_DIR/bin/activate

pip install --upgrade pip setuptools wheel
pip install django gunicorn

# =========================
# INSTALL REQUIREMENTS
# =========================
cd $PROJECT_DIR
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

# =========================
# DJANGO COMMANDS
# =========================
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE

python manage.py migrate
python manage.py collectstatic --noinput

# =========================
# SYSTEMD SERVICE
# =========================
echo "⚙️ Creating systemd service..."

sudo tee /etc/systemd/system/finai.service > /dev/null <<EOF
[Unit]
Description=FinAI Django Application
After=network.target

[Service]
User=$USER_NAME
Group=www-data
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn \
          --workers 3 \
          --bind unix:$GUNICORN_SOCKET \
          FinAI.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable finai
sudo systemctl restart finai

# =========================
# NGINX CONFIG
# =========================
echo "🌐 Configuring Nginx..."

sudo tee /etc/nginx/sites-available/finai > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN_OR_IP;

    location /static/ {
        root $PROJECT_DIR;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$GUNICORN_SOCKET;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/finai /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

# =========================
# FIREWALL
# =========================
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "✅ FinAI Deployment Completed Successfully!"
echo "🌍 Open: http://$DOMAIN_OR_IP"
