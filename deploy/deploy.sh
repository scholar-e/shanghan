#!/bin/bash
# Main deployment script for Shanghan-TCM
# Run with: ./deploy.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="shanghan-tcm"
INSTALL_DIR="/opt/$APP_NAME"
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default flags
SKIP_NGINX_INSTALL=false
SKIP_SSL=false
SKIP_APP_SETUP=false
SKIP_NGINX_CONFIG=false
DOMAIN="localhost"

usage() {
    cat << EOF
Usage: $0 [options]

Deploy Shanghan-TCM application with nginx reverse proxy.

Options:
    --skip-nginx-install    Skip nginx installation
    --skip-ssl              Skip SSL certificate generation
    --skip-app-setup        Skip application setup (virtualenv, systemd)
    --skip-nginx-config     Skip nginx configuration
    --domain <domain>       Domain name for SSL certificate (default: localhost)
    --install-dir <dir>     Installation directory (default: /opt/shanghan-tcm)
    -h, --help              Show this help message

Example:
    $0 --domain shanghan.example.com
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-nginx-install)
            SKIP_NGINX_INSTALL=true
            shift
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --skip-app-setup)
            SKIP_APP_SETUP=true
            shift
            ;;
        --skip-nginx-config)
            SKIP_NGINX_CONFIG=true
            shift
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Shanghan-TCM Deployment ===${NC}"
echo "Install directory: $INSTALL_DIR"
echo "Domain: $DOMAIN"
echo "Deploy scripts directory: $DEPLOY_DIR"

# Function to run a script with error checking
run_script() {
    local script="$1"
    local description="$2"
    
    if [[ ! -x "$script" ]]; then
        echo -e "${YELLOW}Making script executable: $script${NC}"
        chmod +x "$script"
    fi
    
    echo -e "${GREEN}Running: $description${NC}"
    if ! "$script"; then
        echo -e "${RED}Error: $description failed${NC}"
        exit 1
    fi
}

# Export environment variables for child scripts
export DOMAIN
export INSTALL_DIR

# Step 1: Install nginx and dependencies
if [[ "$SKIP_NGINX_INSTALL" = false ]]; then
    run_script "$DEPLOY_DIR/install-nginx.sh" "nginx installation"
else
    echo -e "${YELLOW}Skipping nginx installation${NC}"
fi

# Step 2: Generate SSL certificates
if [[ "$SKIP_SSL" = false ]]; then
    run_script "$DEPLOY_DIR/generate-ssl.sh" "SSL certificate generation"
else
    echo -e "${YELLOW}Skipping SSL certificate generation${NC}"
fi

# Step 3: Set up application with systemd service
if [[ "$SKIP_APP_SETUP" = false ]]; then
    run_script "$DEPLOY_DIR/setup-app.sh" "application setup"
else
    echo -e "${YELLOW}Skipping application setup${NC}"
fi

# Step 4: Configure nginx
if [[ "$SKIP_NGINX_CONFIG" = false ]]; then
    run_script "$DEPLOY_DIR/configure-nginx.sh" "nginx configuration"
else
    echo -e "${YELLOW}Skipping nginx configuration${NC}"
fi

# Final summary
echo -e "${GREEN}=== Deployment completed successfully ===${NC}"
cat << EOF

Next steps:
1. Update the SSL certificates for production (use Let's Encrypt):
   sudo certbot --nginx -d $DOMAIN

2. Start the application service:
   sudo systemctl start $APP_NAME

3. Verify nginx is running:
   sudo systemctl status nginx

4. Access the application:
   https://$DOMAIN

5. Monitor logs:
   sudo journalctl -u $APP_NAME -f
   sudo tail -f /var/log/nginx/access.log

For troubleshooting, check:
  - Application logs: sudo journalctl -u $APP_NAME
  - Nginx error logs: sudo tail -f /var/log/nginx/error.log
  - Firewall: sudo ufw status

EOF