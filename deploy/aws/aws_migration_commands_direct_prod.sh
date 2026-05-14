#!/usr/bin/env bash
set -euo pipefail

# Direct-to-Production AWS Migration Commands (No Test Domain)
#
# WARNING:
# - This is faster but higher risk than the test-domain method.
# - Keep GCP running as rollback fallback.
# - Execute section by section.

############################################
# PROJECT VALUES (prefilled for UI_CryptoCEN)
############################################
APP_USER="mantraj"
APP_DIR="/home/mantraj/mantraj"
PYTHON_BIN="python3"
VENV_DIR="$APP_DIR/venv"
REPO_URL="https://github.com/bitdev23/UI_CryptoCEN.git"
BRANCH="main"
PROD_DOMAIN="app.velank.io"
GUNICORN_BIND="0.0.0.0:5050"
GUNICORN_WORKERS="16"

############################################
# SECTION A - SERVER PREP (run on EC2)
############################################

echo "[A1] Updating OS packages"
sudo apt update && sudo apt -y upgrade

echo "[A2] Installing base dependencies"
sudo apt -y install \
  git curl unzip build-essential \
  nginx certbot python3-certbot-nginx \
  python3 python3-venv python3-pip

echo "[A3] Creating app user if missing"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  sudo adduser --disabled-password --gecos "" "$APP_USER"
fi

echo "[A4] Creating app directory"
sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "/home/$APP_USER"

############################################
# SECTION B - APP CODE + VENV
############################################

echo "[B1] Clone or update repository"
sudo -u "$APP_USER" -H bash -lc '
  set -euo pipefail
  if [ ! -d "'$APP_DIR'/.git" ]; then
    git clone "'$REPO_URL'" "'$APP_DIR'"
  fi
  cd "'$APP_DIR'"
  git fetch --all
  git checkout "'$BRANCH'"
  git pull --ff-only origin "'$BRANCH'"
'

echo "[B2] Install Python dependencies"
sudo -u "$APP_USER" -H bash -lc '
  set -euo pipefail
  cd "'$APP_DIR'"
  if [ ! -d "'$VENV_DIR'" ]; then
    '$PYTHON_BIN' -m venv "'$VENV_DIR'"
  fi
  source "'$VENV_DIR'/bin/activate"
  pip install --upgrade pip
  pip install -r requirements.txt
'

echo "[B3] Create .env if missing"
if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi

echo "IMPORTANT: Edit $APP_DIR/.env now."
echo "Set APP_BASE_URL=https://$PROD_DOMAIN"

############################################
# SECTION C - SYSTEMD SERVICES
############################################

echo "[C1] Install API service"
sudo tee /etc/systemd/system/mantraj-api.service >/dev/null <<EOF
[Unit]
Description=Mantraj API Server
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/gunicorn app:app -w $GUNICORN_WORKERS -b $GUNICORN_BIND
Restart=always
RestartSec=3
EnvironmentFile=$APP_DIR/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "[C2] Install worker service"
sudo tee /etc/systemd/system/mantraj-worker.service >/dev/null <<EOF
[Unit]
Description=Mantraj RQ Worker
After=network.target

[Service]
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$VENV_DIR/bin/python worker.py
Restart=always
RestartSec=3
EnvironmentFile=$APP_DIR/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "[C3] Enable and restart services"
sudo systemctl daemon-reload
sudo systemctl enable mantraj-api mantraj-worker
sudo systemctl restart mantraj-api mantraj-worker

############################################
# SECTION D - NGINX + TLS (PRODUCTION DOMAIN)
############################################

echo "[D1] Write production nginx config"
sudo tee /etc/nginx/sites-available/mantraj >/dev/null <<EOF
server {
    listen 80;
    server_name $PROD_DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 55M;
        proxy_read_timeout 120;
        proxy_connect_timeout 120;
    }
}
EOF

echo "[D2] Enable nginx site"
sudo ln -sf /etc/nginx/sites-available/mantraj /etc/nginx/sites-enabled/mantraj
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "[D3] Get TLS cert (run after DNS points to this EC2 IP)"
echo "Command: sudo certbot --nginx -d $PROD_DOMAIN --non-interactive --agree-tos -m admin@$PROD_DOMAIN --redirect"

############################################
# SECTION E - HEALTH + LOG CHECKS
############################################

echo "[E1] API health (localhost)"
curl -I http://127.0.0.1:5050 || true

echo "[E2] API service status"
sudo systemctl --no-pager --full status mantraj-api || true

echo "[E3] Worker service status"
sudo systemctl --no-pager --full status mantraj-worker || true

echo "[E4] API logs"
sudo journalctl -u mantraj-api -n 100 --no-pager || true

echo "[E5] Worker logs"
sudo journalctl -u mantraj-worker -n 100 --no-pager || true

echo "Next: perform provider callback updates, DNS cutover, cert issue, and smoke tests."
