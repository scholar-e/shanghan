#!/bin/bash
# Generate self-signed SSL certificates for Shanghan-TCM development

set -e

# Configuration
DOMAIN="localhost"
COUNTRY="US"
STATE="California"
LOCALITY="San Francisco"
ORGANIZATION="Shanghan-TCM"
ORG_UNIT="Development"
EMAIL="admin@shanghan-tcm.local"
DAYS=365

# Directories
SSL_CERT_DIR="/etc/ssl/certs"
SSL_KEY_DIR="/etc/ssl/private"

echo "Generating SSL certificates for ${DOMAIN}..."

# Check if openssl is available
if ! command -v openssl &> /dev/null; then
    echo "Error: openssl is not installed. Please install openssl."
    exit 1
fi

# Create directories if they don't exist
sudo mkdir -p "${SSL_CERT_DIR}"
sudo mkdir -p "${SSL_KEY_DIR}"

# Generate private key
echo "Generating private key..."
sudo openssl genrsa -out "${SSL_KEY_DIR}/shanghan-tcm.key" 2048

# Generate certificate signing request
echo "Generating CSR..."
sudo openssl req -new -key "${SSL_KEY_DIR}/shanghan-tcm.key" \
    -out /tmp/shanghan-tcm.csr \
    -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${ORGANIZATION}/OU=${ORG_UNIT}/CN=${DOMAIN}/emailAddress=${EMAIL}"

# Generate self-signed certificate
echo "Generating self-signed certificate..."
sudo openssl x509 -req -days ${DAYS} \
    -in /tmp/shanghan-tcm.csr \
    -signkey "${SSL_KEY_DIR}/shanghan-tcm.key" \
    -out "${SSL_CERT_DIR}/shanghan-tcm.crt"

# Clean up CSR
sudo rm -f /tmp/shanghan-tcm.csr

# Set permissions
echo "Setting permissions..."
sudo chmod 644 "${SSL_CERT_DIR}/shanghan-tcm.crt"
sudo chmod 640 "${SSL_KEY_DIR}/shanghan-tcm.key"

# Make key readable by nginx (adjust group based on your system)
if getent group www-data > /dev/null; then
    sudo chown root:www-data "${SSL_KEY_DIR}/shanghan-tcm.key"
elif getent group nginx > /dev/null; then
    sudo chown root:nginx "${SSL_KEY_DIR}/shanghan-tcm.key"
else
    echo "Warning: Could not determine web server group. Key ownership not changed."
fi

# Create a combined PEM file (optional, for some applications)
echo "Creating combined PEM file..."
sudo cat "${SSL_KEY_DIR}/shanghan-tcm.key" "${SSL_CERT_DIR}/shanghan-tcm.crt" \
    | sudo tee "${SSL_CERT_DIR}/shanghan-tcm.pem" > /dev/null
sudo chmod 644 "${SSL_CERT_DIR}/shanghan-tcm.pem"

# Verify the certificate
echo "Verifying certificate..."
sudo openssl x509 -in "${SSL_CERT_DIR}/shanghan-tcm.crt" -text -noout | head -20

echo ""
echo "SSL certificates generated successfully!"
echo ""
echo "Certificate: ${SSL_CERT_DIR}/shanghan-tcm.crt"
echo "Private Key: ${SSL_KEY_DIR}/shanghan-tcm.key"
echo "PEM File:    ${SSL_CERT_DIR}/shanghan-tcm.pem"
echo ""
echo "You can now start nginx with the configuration."
echo "Note: For development only. Use Let's Encrypt for production."

# Create symbolic links in local directory for easy reference
mkdir -p ../certs
sudo cp "${SSL_CERT_DIR}/shanghan-tcm.crt" ../certs/
sudo cp "${SSL_KEY_DIR}/shanghan-tcm.key" ../certs/
sudo chmod 644 ../certs/shanghan-tcm.crt
sudo chmod 600 ../certs/shanghan-tcm.key
echo ""
echo "Copied certificates to ../certs/ for local reference."