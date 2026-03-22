#!/bin/bash
# Colony OS - Docker Deployment Script

set -e

APP_NAME="colony-os-app"
REGISTRY="ghcr.io"
USER="sergiodionisioau"

echo "=== Colony OS Docker Deployment ==="

# Build
echo "Building Docker image..."
docker build -t ${APP_NAME}:latest .

# Tag for GitHub Container Registry
echo "Tagging for GitHub Container Registry..."
docker tag ${APP_NAME}:latest ${REGISTRY}/${USER}/${APP_NAME}:latest
docker tag ${APP_NAME}:latest ${REGISTRY}/${USER}/${APP_NAME}:$(date +%Y%m%d-%H%M%S)

# Run locally with docker-compose
echo "Starting with docker-compose..."
docker-compose up -d

echo ""
echo "=== Deployment Complete ==="
echo "App running at: http://localhost:8080"
echo "Health check: http://localhost:8080/health"
echo ""
echo "To push to GitHub Container Registry:"
echo "  echo $GITHUB_TOKEN | docker login ghcr.io -u ${USER} --password-stdin"
echo "  docker push ${REGISTRY}/${USER}/${APP_NAME}:latest"
echo ""
echo "To deploy with Cloudflare Tunnel:"
echo "  1. Create tunnel: cloudflared tunnel create colony-os"
echo "  2. Add token to .env as CF_TUNNEL_TOKEN"
echo "  3. docker-compose --profile tunnel up -d"
