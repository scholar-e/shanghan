#!/bin/bash
# Self-contained deployment script for Shanghan-TCM Evidence v1
# Run: ./deploy.sh [--domain example.com] [--install-dir /opt/shanghan]
#      ./deploy.sh --help for full options

set -e

APP_NAME="shanghan-tcm"
DOMAIN="${DOMAIN:-localhost}"
INSTALL_DIR="${INSTALL_DIR:-/opt/$APP_NAME}"
SKIP_SSL=false
SKIP_APP_SETUP=false
GEN_SSL=false

usage() {
    cat << EOF
Usage: $0 [options]

Deploy Shanghan-TCM with systemd service (gunicorn).

Options:
    --domain <domain>       Domain for SSL cert (default: localhost)
    --install-dir <dir>     Install directory (default: /opt/shanghan-tcm)
    --ssl                   Generate self-signed SSL certs for the app
    --skip-app-setup        Skip venv/systemd setup (just copy files)
    -h, --help              Show this help
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --domain) DOMAIN="$2"; shift 2 ;;
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --ssl) GEN_SSL=true; shift ;;
        --skip-app-setup) SKIP_APP_SETUP=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown: $1"; usage ;;
    esac
done

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== Deploying $APP_NAME ==="
echo "Source: $SRC_DIR"
echo "Target: $INSTALL_DIR"
echo "Domain: $DOMAIN"

if [[ $EUID -eq 0 ]]; then
    echo "Do not run as root. A regular user with sudo is expected."
    exit 1
fi

# --- Copy files ---
echo "Copying application to $INSTALL_DIR ..."
sudo mkdir -p "$INSTALL_DIR"
sudo chown "$USER:$USER" "$INSTALL_DIR"
rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' "$SRC_DIR/" "$INSTALL_DIR/"

# --- .env ---
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    if [[ -f "$SRC_DIR/.env" ]]; then
        cp "$SRC_DIR/.env" "$INSTALL_DIR/.env"
        echo ".env copied from source"
    else
        SECRET=$(openssl rand -hex 32 2>/dev/null || echo "change-me")
        cat > "$INSTALL_DIR/.env" << EOF
SECRET_KEY=$SECRET
DEEPSEEK_API_KEY=
FLASK_DEBUG=false
PORT=5000
FLASK_HOST=127.0.0.1
EOF
        echo ".env created with random SECRET_KEY (edit DEEPSEEK_API_KEY)"
    fi
fi

# --- Logs ---
mkdir -p "$INSTALL_DIR/src/logs"

# --- Optional SSL certs ---
if [[ "$GEN_SSL" == true ]]; then
    CERT="/etc/ssl/certs/$APP_NAME.crt"
    KEY="/etc/ssl/private/$APP_NAME.key"
    if [[ ! -f "$CERT" ]]; then
        echo "Generating self-signed SSL cert for $DOMAIN ..."
        sudo mkdir -p /etc/ssl/certs /etc/ssl/private
        sudo openssl req -x509 -newkey rsa:2048 -keyout "$KEY" -out "$CERT" -days 365 -nodes \
            -subj "/CN=$DOMAIN" 2>/dev/null
        sudo chmod 640 "$KEY"
        echo "  Cert: $CERT"
        echo "  Key:  $KEY"
    else
        echo "SSL certs already exist, skipping"
    fi
    # Write SSL paths into .env
    echo "SSL_CERT_PATH=$CERT" >> "$INSTALL_DIR/.env"
    echo "SSL_KEY_PATH=$KEY" >> "$INSTALL_DIR/.env"
fi

# --- App setup: venv + systemd ---
if [[ "$SKIP_APP_SETUP" == false ]]; then
    echo "Setting up Python virtual environment ..."
    if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
        python3 -m venv "$INSTALL_DIR/.venv"
    fi
    "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
    "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/src/requirements.txt" -q
    "$INSTALL_DIR/.venv/bin/pip" install gunicorn -q

    echo "Creating systemd service ..."
    sudo tee "/etc/systemd/system/$APP_NAME.service" > /dev/null << EOF
[Unit]
Description=Shanghan-TCM Evidence
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR/src
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 120 server:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$APP_NAME.service"
    echo "Service enabled: $APP_NAME.service"
fi

echo ""
echo "=== Done ==="
echo "Edit $INSTALL_DIR/.env with your DEEPSEEK_API_KEY, then:"
echo "  sudo systemctl start $APP_NAME"
echo "  sudo systemctl status $APP_NAME"
echo "  sudo journalctl -u $APP_NAME -f"
if [[ "$GEN_SSL" == true ]]; then
    echo ""
    echo "App will serve HTTPS at https://$DOMAIN"
fi
