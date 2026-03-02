#!/bin/bash
# Install nginx and system dependencies for Shanghan-TCM deployment

set -e

echo "=== Installing nginx and dependencies ==="

# Detect package manager
if command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    UPDATE_CMD="sudo apt update"
    INSTALL_CMD="sudo apt install -y"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    UPDATE_CMD="sudo yum check-update"
    INSTALL_CMD="sudo yum install -y"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    UPDATE_CMD="sudo dnf check-update"
    INSTALL_CMD="sudo dnf install -y"
else
    echo "Error: Unsupported package manager. Please install nginx manually."
    exit 1
fi

# Update package list
echo "Updating package lists..."
$UPDATE_CMD || true

# Install nginx
echo "Installing nginx..."
$INSTALL_CMD nginx

# Install Python and pip if not present
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    $INSTALL_CMD python3 python3-pip python3-venv
fi

# Install other system dependencies (optional)
echo "Installing additional system dependencies..."
$INSTALL_CMD openssl

# Enable and start nginx service
if systemctl is-active --quiet nginx; then
    echo "nginx is already running."
else
    echo "Starting nginx service..."
    sudo systemctl enable nginx
    sudo systemctl start nginx
fi

# Verify nginx installation
if sudo nginx -t &> /dev/null; then
    echo "nginx configuration test passed."
else
    echo "Warning: nginx configuration test failed."
fi

echo "=== nginx installation complete ==="