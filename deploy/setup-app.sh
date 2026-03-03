#!/bin/bash
# Setup Flask application with gunicorn and systemd service

set -e

# Configuration
APP_NAME="shanghan-tcm"
APP_USER="${APP_USER:-$USER}"
APP_GROUP="${APP_GROUP:-$APP_USER}"
INSTALL_DIR="${INSTALL_DIR:-/opt/$APP_NAME}"
VENV_DIR="${INSTALL_DIR}/.venv"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Setting up $APP_NAME ==="
echo "Install directory: $INSTALL_DIR"
echo "Repository directory: $REPO_DIR"
echo "Application user: $APP_USER"

# Check if running as root or with sudo
if [[ $EUID -eq 0 ]]; then
    echo "Error: This script should not be run as root. Run as a regular user with sudo privileges."
    exit 1
fi

# Create installation directory
echo "Creating installation directory..."
sudo mkdir -p "$INSTALL_DIR"
sudo chown "$APP_USER:$APP_GROUP" "$INSTALL_DIR"

# Copy application files (excluding git, venv, etc.)
echo "Copying application files..."
rsync -av --progress \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='*.pyc' \
    --exclude='__pycache__/' \
    --exclude='*.log' \
    --exclude='logs/' \
    --exclude='deploy/' \
    --exclude='*.zip' \
    "$REPO_DIR/" "$INSTALL_DIR/"

# Ensure logs directory exists
sudo mkdir -p "$INSTALL_DIR/logs"
sudo chown "$APP_USER:$APP_GROUP" "$INSTALL_DIR/logs"

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
cd "$INSTALL_DIR"
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment and install dependencies
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/src/requirements.txt"
pip install gunicorn

# Create systemd service file
echo "Creating systemd service..."
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Shanghan-TCM Flask Application
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$INSTALL_DIR/src
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
Environment="SECRET_KEY=$(openssl rand -hex 32)"
Environment="PORT=5000"
Environment="FLASK_HOST=127.0.0.1"
Environment="FLASK_DEBUG=false"
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 120 server:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME.service"

echo "=== Application setup complete ==="
echo "To start the service: sudo systemctl start $APP_NAME"
echo "To check status: sudo systemctl status $APP_NAME"
echo "To view logs: sudo journalctl -u $APP_NAME -f"