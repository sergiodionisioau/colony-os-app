#!/bin/bash
# Docker Installation & Deployment Script for Colony OS
# Run this on your VM

echo "=== Colony OS Docker Setup ==="

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
echo "Verifying installation..."
docker --version
docker-compose --version

# Navigate to app
cd /home/coe/.openclaw/workspace/colony-os-app

# Build and run
echo "Building Colony OS container..."
docker-compose build

echo "Starting Colony OS..."
docker-compose up -d

# Show status
echo ""
echo "=== Status ==="
docker ps | grep colony-os
echo ""
echo "App should be running at:"
echo "  - Local: http://localhost:8080"
echo "  - Cloudflare: https://colonyos.ai"
