# COE Kernel - Production Monitoring & SSL Setup

## Overview

This document describes the production monitoring and SSL setup for COE Kernel.

## Components

### 1. Health Check Endpoints

The following health endpoints are available:

| Endpoint | Purpose | Status Code |
|----------|---------|-------------|
| `/healthz` | Load balancer health check | 200 OK |
| `/ready` | Kubernetes readiness probe | 200/503 |
| `/live` | Kubernetes liveness probe | 200 OK |
| `/v1/health` | Detailed health with all dependencies | 200/503 |

#### Health Check Details

**`/v1/health` checks:**
- **Database**: SQLite connectivity (migratable to PostgreSQL)
- **Redis**: Cache connectivity
- **OpenAI API**: API availability
- **Disk Space**: Free space monitoring
- **Memory**: Usage statistics
- **System**: CPU, load average

### 2. Prometheus Metrics

Metrics exposed at `/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `request_duration_seconds` | Histogram | Request latency by method/endpoint/status |
| `request_total` | Counter | Total requests |
| `task_total` | Counter | Tasks created/completed/failed |
| `memory_usage_bytes` | Gauge | Memory usage (used/available/total) |
| `db_connection_pool_size` | Gauge | Database connection pool |
| `tool_execution_duration_seconds` | Histogram | Tool execution latency |
| `active_tasks` | Gauge | Currently active tasks |
| `error_total` | Counter | Error count by type |

### 3. Grafana Dashboard

Dashboard file: `monitoring/grafana-dashboard.json`

**Panels:**
- Service Status
- Request Rate (by method)
- Active Tasks
- P95 Latency
- Error Rate %
- Request Latency Distribution (p50/p95/p99)
- Response Status Distribution
- Task Throughput
- Memory Usage
- DB Pool Size
- Errors by Type

**Alerts Configured:**
- High Error Rate (>5%)
- High Latency (p95 > 1s)
- Low Memory (>90% usage)
- Service Down
- High CPU (>80%)
- Low Disk Space (<10%)

### 4. SSL/TLS Setup

**Certificate Location:** `certs/`
- `server.crt` - Certificate (644 permissions)
- `server.key` - Private key (600 permissions)

**Configuration:**
- TLS 1.3 enabled
- TLS 1.2 for compatibility
- 4096-bit RSA key
- Strong cipher suites
- Auto-renewal support via scripts

**Scripts:**
- `scripts/setup-ssl.sh` - Generate self-signed certificates
- `scripts/renew-ssl.sh` - Let's Encrypt integration

### 5. Structured Logging

JSON-formatted logs with:
- Timestamp (ISO 8601)
- Log level
- Correlation ID
- Request ID
- Source location (file/line/function)
- Request details (method, path, status, duration)

**Log Files:**
- Console (stdout)
- File: `logs/coe-kernel.log` (rotated, 10MB max, 10 backups)

## Quick Start

### Run with HTTPS

```bash
# Set environment variables
export USE_SSL=true
export SSL_CERT_PATH=/home/coe/.openclaw/workspace/colony-os-app/certs/server.crt
export SSL_KEY_PATH=/home/coe/.openclaw/workspace/colony-os-app/certs/server.key

# Run the production app
cd /home/coe/.openclaw/workspace/colony-os-app
python3 src/app_production.py
```

### Run with Docker Compose

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# Access services:
# - App: https://localhost:8443
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

### Test Endpoints

```bash
# Health check
curl -k https://localhost:8443/healthz

# Readiness probe
curl -k https://localhost:8443/ready

# Detailed health
curl -k https://localhost:8443/v1/health

# Prometheus metrics
curl -k https://localhost:8443/metrics
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_PORT` | 8080 | HTTP port |
| `APP_HOST` | 0.0.0.0 | Bind address |
| `USE_SSL` | false | Enable HTTPS |
| `SSL_CERT_PATH` | certs/server.crt | Certificate path |
| `SSL_KEY_PATH` | certs/server.key | Private key path |
| `DATABASE_PATH` | data/colony_os_tasks.db | SQLite database |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `LOG_LEVEL` | INFO | Logging level |
| `ENVIRONMENT` | production | Environment name |

## Files Created

```
colony-os-app/
├── src/
│   └── app_production.py      # Production Flask app with monitoring
├── monitoring/
│   ├── grafana-dashboard.json # Grafana dashboard definition
│   ├── prometheus.yml         # Prometheus configuration
│   ├── alerts.yml             # Prometheus alerting rules
│   ├── grafana-datasource.yml # Grafana data source config
│   └── grafana-dashboard-provider.yml
├── scripts/
│   ├── setup-ssl.sh           # SSL certificate generation
│   └── renew-ssl.sh           # Let's Encrypt renewal
├── certs/
│   ├── server.crt             # SSL certificate
│   └── server.key             # SSL private key
├── logs/
│   └── coe-kernel.log         # Application logs
├── requirements-production.txt # Python dependencies
├── Dockerfile.production       # Production Docker image
└── docker-compose.production.yml # Full stack deployment
```

## Verification Results

### Health Endpoints
- ✅ `/healthz` - Returns 200 OK
- ✅ `/ready` - Returns 200 with database and memory checks
- ✅ `/live` - Returns 200 OK
- ✅ `/v1/health` - Returns detailed health with all dependencies

### Prometheus Metrics
- ✅ `/metrics` - Exposes all metrics in Prometheus format
- ✅ request_duration_seconds histogram
- ✅ request_total counter
- ✅ task_total counter
- ✅ memory_usage_bytes gauge
- ✅ active_tasks gauge

### SSL/TLS
- ✅ TLS 1.3 enabled
- ✅ Certificate valid for 365 days
- ✅ 4096-bit RSA key
- ✅ HTTPS working on port 8443

### Logging
- ✅ JSON structured logging
- ✅ Correlation IDs in requests/responses
- ✅ Log rotation configured
- ✅ File and console output

## Notes

- Redis is optional; health checks will show "unhealthy" if not running but app still works
- OpenAI API key is optional; shows "unknown" status if not configured
- For production, replace self-signed certificates with Let's Encrypt or proper CA certificates
- Grafana default credentials: admin/admin (change in production)
