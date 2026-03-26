#!/bin/bash
# Let's Encrypt Certificate Auto-Renewal Script for COE Kernel
# This script handles automatic certificate renewal using certbot

set -e

DOMAIN="${DOMAIN:-localhost}"
EMAIL="${EMAIL:-admin@example.com}"
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
APP_CERT_DIR="/app/certs"
WEBROOT="/var/www/certbot"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Check if running as root for certbot
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root for Let's Encrypt"
        exit 1
    fi
}

# Install certbot if not present
install_certbot() {
    if ! command -v certbot &> /dev/null; then
        log "Installing certbot..."
        apt-get update
        apt-get install -y certbot
    fi
}

# Obtain initial certificate
obtain_certificate() {
    log "Obtaining certificate for $DOMAIN..."
    
    mkdir -p "$WEBROOT"
    
    certbot certonly \
        --webroot \
        --webroot-path "$WEBROOT" \
        --domain "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive \
        --rsa-key-size 4096 \
        --must-staple
    
    if [ $? -eq 0 ]; then
        log "Certificate obtained successfully!"
        copy_certificates
    else
        error "Failed to obtain certificate"
        exit 1
    fi
}

# Copy certificates to app directory
copy_certificates() {
    log "Copying certificates to app directory..."
    
    mkdir -p "$APP_CERT_DIR"
    
    cp "$CERT_DIR/fullchain.pem" "$APP_CERT_DIR/server.crt"
    cp "$CERT_DIR/privkey.pem" "$APP_CERT_DIR/server.key"
    
    chmod 600 "$APP_CERT_DIR/server.key"
    chmod 644 "$APP_CERT_DIR/server.crt"
    
    log "Certificates copied to $APP_CERT_DIR"
}

# Renew certificates
renew_certificates() {
    log "Checking for certificate renewal..."
    
    certbot renew --quiet --deploy-hook "/app/scripts/copy-certs.sh"
    
    if [ $? -eq 0 ]; then
        log "Certificate renewal check completed"
    else
        warn "Certificate renewal may have issues"
    fi
}

# Setup auto-renewal cron job
setup_cron() {
    log "Setting up auto-renewal cron job..."
    
    # Renew twice daily (recommended by Let's Encrypt)
    CRON_JOB="0 0,12 * * * /app/scripts/renew-ssl.sh renew >> /var/log/letsencrypt-renewal.log 2>&1"
    
    # Remove existing cron job if present
    crontab -l 2>/dev/null | grep -v "renew-ssl.sh" | crontab - || true
    
    # Add new cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    
    log "Cron job installed. Certificates will be renewed automatically."
}

# Test SSL configuration
test_ssl() {
    log "Testing SSL configuration..."
    
    if [ -f "$APP_CERT_DIR/server.crt" ]; then
        echo "Certificate info:"
        openssl x509 -in "$APP_CERT_DIR/server.crt" -noout -subject -dates
        
        echo ""
        echo "Testing TLS versions..."
        for version in tls1_2 tls1_3; do
            result=$(openssl s_client -$version -connect localhost:8443 </dev/null 2>/dev/null | grep "Protocol" | head -1)
            if [ -n "$result" ]; then
                log "✓ $version supported"
            else
                warn "✗ $version not available"
            fi
        done
    else
        error "Certificate not found at $APP_CERT_DIR/server.crt"
    fi
}

# Main
case "${1:-setup}" in
    setup)
        check_root
        install_certbot
        obtain_certificate
        setup_cron
        test_ssl
        log "SSL setup complete!"
        ;;
    renew)
        renew_certificates
        ;;
    test)
        test_ssl
        ;;
    copy)
        copy_certificates
        ;;
    *)
        echo "Usage: $0 {setup|renew|test|copy}"
        exit 1
        ;;
esac
