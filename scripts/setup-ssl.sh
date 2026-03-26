#!/bin/bash
# SSL Certificate Setup Script for COE Kernel
# Generates self-signed certificates for development/testing
# For production, use Let's Encrypt or a proper CA

set -e

CERT_DIR="/app/certs"
CERT_FILE="$CERT_DIR/server.crt"
KEY_FILE="$CERT_DIR/server.key"
DAYS_VALID=365

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "COE Kernel SSL Certificate Setup"
echo "=========================================="
echo ""

# Create certificate directory
mkdir -p "$CERT_DIR"

# Check if certificates already exist
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo -e "${YELLOW}Certificates already exist at:${NC}"
    echo "  Certificate: $CERT_FILE"
    echo "  Key: $KEY_FILE"
    echo ""
    read -p "Do you want to regenerate them? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Keeping existing certificates.${NC}"
        exit 0
    fi
fi

echo "Generating new SSL certificates..."
echo ""

# Generate private key and certificate
openssl req -x509 -nodes -days $DAYS_VALID -newkey rsa:4096 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/C=US/ST=State/L=City/O=COE Kernel/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:::1"

# Set proper permissions
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo -e "${GREEN}SSL certificates generated successfully!${NC}"
echo ""
echo "Certificate details:"
echo "------------------------------------------"
openssl x509 -in "$CERT_FILE" -text -noout | grep -E "Subject:|Issuer:|Not Before|Not After|Subject Alternative Name" || true
echo ""
echo "Files created:"
echo "  Certificate: $CERT_FILE"
echo "  Private Key: $KEY_FILE"
echo ""
echo "Valid for: $DAYS_VALID days"
echo ""

# Verify certificate
echo "Verifying certificate..."
openssl x509 -in "$CERT_FILE" -noout -verify
echo ""

# Display TLS version support
echo "Testing TLS 1.3 support..."
openssl s_client -tls1_3 -connect localhost:8443 </dev/null 2>/dev/null | grep -E "Protocol|Cipher" || echo "Server not running yet, TLS 1.3 will be enabled when started."
echo ""

echo -e "${GREEN}SSL setup complete!${NC}"
echo ""
echo "To enable HTTPS, set the following environment variables:"
echo "  export USE_SSL=true"
echo "  export SSL_CERT_PATH=$CERT_FILE"
echo "  export SSL_KEY_PATH=$KEY_FILE"
echo ""
echo "Or in your .env file:"
echo "  USE_SSL=true"
echo "  SSL_CERT_PATH=$CERT_FILE"
echo "  SSL_KEY_PATH=$KEY_FILE"
