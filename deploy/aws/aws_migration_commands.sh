#!/usr/bin/env bash
set -euo pipefail

# AWS Migration Commands (Beginner Safe)
#
# Usage:
# 1) Read this file fully once.
# 2) Verify the variables below match your desired cutover domains.
# 3) Run sections one by one (do NOT run everything blindly).
#
# This script is intentionally verbose and defensive.

############################################
# PROJECT VALUES (prefilled for UI_CryptoCEN)
############################################
APP_USER="mantraj"
APP_DIR="/home/mantraj/mantraj"
PYTHON_BIN="python3"
VENV_DIR="$APP_DIR/venv"
REPO_URL="https://github.com/bitdev23/UI_CryptoCEN.git"
BRANCH="main"

# Phase 1 testing domain (recommended)
TEST_DOMAIN="aws-test.app.velank.io"

# Final production domain
PROD_DOMAIN="app.velank.io"

# Gunicorn bind and workers (matching your current setup)
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

echo "[A3] Creating app user if not exists"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
  sudo adduser --disabled-password --gecos "" "$APP_USER"
fi

echo "[A4] Creating app directory"
sudo mkdir -p "$APP_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "/home/$APP_USER"

############################################
# SECTION B - APP CODE + VENV (run on EC2)
############################################

echo "[B1] Cloning or updating repo"
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

echo "[B2] Creating/updating virtualenv"
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

echo "[B3] Creating .env from template if missing"
if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "IMPORTANT: Edit $APP_DIR/.env now with production values."
fi

############################################
# SECTION C - SYSTEMD SERVICES (run on EC2)
############################################

echo "[C1] Writing API service"
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

echo "[C2] Writing Worker service"
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

echo "[C3] Reloading systemd + starting services"
sudo systemctl daemon-reload
sudo systemctl enable mantraj-api mantraj-worker
sudo systemctl restart mantraj-api mantraj-worker

echo "[C4] Service status checks"
sudo systemctl --no-pager --full status mantraj-api || true
sudo systemctl --no-pager --full status mantraj-worker || true

############################################
# SECTION D - NGINX (TEST DOMAIN)
############################################

echo "[D1] Writing Nginx test-domain config"
sudo tee /etc/nginx/sites-available/mantraj >/dev/null <<EOF
server {
    listen 80;
    server_name $TEST_DOMAIN;

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

echo "[D2] Enabling Nginx site"
sudo ln -sf /etc/nginx/sites-available/mantraj /etc/nginx/sites-enabled/mantraj
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "[D3] Getting TLS cert for test domain"
sudo certbot --nginx -d "$TEST_DOMAIN" --non-interactive --agree-tos -m admin@"$PROD_DOMAIN" --redirect || true

############################################
# SECTION E - OBSERVABILITY QUICK CHECKS
############################################

echo "[E1] API health via localhost"
curl -I http://127.0.0.1:5050 || true

echo "[E2] API logs tail"
sudo journalctl -u mantraj-api -n 100 --no-pager || true

echo "[E3] Worker logs tail"
sudo journalctl -u mantraj-worker -n 100 --no-pager || true

############################################
# SECTION F - PRODUCTION CUTOVER COMMANDS
# Run ONLY after testing on test domain passes.
############################################

echo "[F1] Update APP_BASE_URL in .env to production domain"
echo "Edit: $APP_DIR/.env"
echo "Set: APP_BASE_URL=https://$PROD_DOMAIN"

echo "[F2] Rewrite Nginx server_name for production"
sudo sed -i "s/$TEST_DOMAIN/$PROD_DOMAIN/g" /etc/nginx/sites-available/mantraj
sudo nginx -t
sudo systemctl reload nginx

echo "[F3] Issue production cert"
sudo certbot --nginx -d "$PROD_DOMAIN" --non-interactive --agree-tos -m admin@"$PROD_DOMAIN" --redirect || true

echo "[F4] Restart app services"
sudo systemctl restart mantraj-api mantraj-worker

echo "[F5] Final status"
sudo systemctl --no-pager --full status mantraj-api || true
sudo systemctl --no-pager --full status mantraj-worker || true

echo "Done. Now perform DNS switch to point $PROD_DOMAIN to this EC2 Elastic IP."
