#!/usr/bin/env bash
# One-time EC2 setup script.
# Run as: bash scripts/ec2_setup.sh
# Assumes Ubuntu 22.04, running as a user with sudo.
set -euo pipefail

APP_DIR="$HOME/SME_indicators"
REPO_URL="https://github.com/sachin245/SME_indicators.git"
DOMAIN_OR_IP="98.81.94.194"

# ── System packages ──────────────────────────────────────────────────────────
echo "[1/7] Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm nginx git curl

# Install Node 20 LTS (Ubuntu default may be old)
if ! node --version | grep -q "^v2"; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

# ── Clone repo ───────────────────────────────────────────────────────────────
echo "[2/7] Cloning repository"
if [ -d "$APP_DIR" ]; then
  echo "  Directory exists, pulling latest"
  git -C "$APP_DIR" pull origin main
else
  git clone "$REPO_URL" "$APP_DIR"
fi

# ── Python virtualenv ─────────────────────────────────────────────────────────
echo "[3/7] Creating Python virtualenv"
cd "$APP_DIR"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# ── Build frontend ────────────────────────────────────────────────────────────
echo "[4/7] Building React frontend"
cd "$APP_DIR/frontend"
npm ci --silent
npm run build
cd "$APP_DIR"

# ── Systemd service for FastAPI ───────────────────────────────────────────────
echo "[5/7] Installing systemd service"
sudo tee /etc/systemd/system/sme-api.service > /dev/null <<EOF
[Unit]
Description=SME Indicators FastAPI
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sme-api
sudo systemctl restart sme-api

# ── Nginx config ───────────────────────────────────────────────────────────────
echo "[6/7] Configuring nginx"
sudo cp "$APP_DIR/nginx/sme-indicators.conf" /etc/nginx/sites-available/sme-indicators
sudo ln -sf /etc/nginx/sites-available/sme-indicators /etc/nginx/sites-enabled/sme-indicators
sudo rm -f /etc/nginx/sites-enabled/default

# Substitute APP_DIR placeholder
sudo sed -i "s|APP_DIR_PLACEHOLDER|$APP_DIR|g" /etc/nginx/sites-available/sme-indicators

sudo nginx -t
sudo systemctl restart nginx

# ── Firewall ───────────────────────────────────────────────────────────────────
echo "[7/7] Configuring firewall"
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo ""
echo "Setup complete. App is live at http://$DOMAIN_OR_IP"
