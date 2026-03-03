#!/bin/bash
# Configure nginx for Shanghan-TCM

set -e

# Configuration
APP_NAME="shanghan-tcm"
INSTALL_DIR="${INSTALL_DIR:-/opt/$APP_NAME}"
DOMAIN="${DOMAIN:-localhost}"
NGINX_CONF_SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../nginx/nginx.conf" && pwd)"
NGINX_CONF_DEST="/etc/nginx/nginx.conf"
BACKUP_DIR="/etc/nginx/backup"

echo "=== Configuring nginx ==="
echo "Source config: $NGINX_CONF_SOURCE"
echo "Destination: $NGINX_CONF_DEST"
echo "Install directory: $INSTALL_DIR"
echo "Domain: $DOMAIN"

# Check if source config exists
if [[ ! -f "$NGINX_CONF_SOURCE" ]]; then
    echo "Error: nginx config source not found at $NGINX_CONF_SOURCE"
    exit 1
fi

# Backup existing nginx config
echo "Backing up existing nginx config..."
sudo mkdir -p "$BACKUP_DIR"
if [[ -f "$NGINX_CONF_DEST" ]]; then
    BACKUP_FILE="$BACKUP_DIR/nginx.conf.backup.$(date +%Y%m%d_%H%M%S)"
    sudo cp "$NGINX_CONF_DEST" "$BACKUP_FILE"
    echo "Backup created at $BACKUP_FILE"
fi

# Create a temporary config with replaced paths
TEMP_CONF=$(mktemp)
echo "Generating nginx configuration..."
sed -e "s|/home/elinzi/Coding/shanghan|$INSTALL_DIR|g" \
    -e "s|server_name .*;|server_name $DOMAIN;|g" \
    "$NGINX_CONF_SOURCE" > "$TEMP_CONF"

# Validate the generated config
echo "Validating nginx configuration..."
if sudo nginx -t -c "$TEMP_CONF" 2>/dev/null; then
    echo "Configuration test passed."
    # Install the new config
    sudo cp "$TEMP_CONF" "$NGINX_CONF_DEST"
    sudo chmod 644 "$NGINX_CONF_DEST"
    echo "Configuration installed to $NGINX_CONF_DEST"
else
    echo "Error: Generated nginx configuration test failed."
    echo "Please check the configuration. The original config remains unchanged."
    rm -f "$TEMP_CONF"
    exit 1
fi

# Clean up temp file
rm -f "$TEMP_CONF"

# Reload nginx
echo "Reloading nginx..."
if sudo systemctl reload nginx 2>/dev/null; then
    echo "nginx reloaded successfully."
else
    echo "Warning: Failed to reload nginx via systemctl. Attempting nginx -s reload..."
    sudo nginx -s reload || echo "Error: nginx reload failed. Please check nginx status."
fi

echo "=== nginx configuration complete ==="