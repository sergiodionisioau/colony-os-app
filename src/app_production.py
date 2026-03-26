"""
COE Kernel - Production Monitoring & Health Checks
Enhanced Flask app with Prometheus metrics, health checks, and structured logging.
"""

import os
import sys
import json
import time
import uuid
import logging
import psutil
import ssl
from pathlib import Path
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional

# Flask and extensions
from flask import Flask, jsonify, request, g, Response
from flask.logging import default_handler

# Prometheus client
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry

# Database and cache imports (for health checks)
import sqlite3
import redis
import openai

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from task_manager import TaskManager, TaskStatus

# ============================================================================
# Configuration
# ============================================================================

APP_NAME = "COE Kernel"
APP_VERSION = "1.0.0"
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
DATABASE_PATH = os.getenv('DATABASE_PATH', '/home/coe/.openclaw/workspace/colony-os-app/data/colony_os_tasks.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# SSL Configuration
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH', '/home/coe/.openclaw/workspace/colony-os-app/certs/server.crt')
SSL_KEY_PATH = os.getenv('SSL_KEY_PATH', '/home/coe/.openclaw/workspace/colony-os-app/certs/server.key')
USE_SSL = os.getenv('USE_SSL', 'false').lower() == 'true'

# ============================================================================
# Structured Logging Setup
# ============================================================================

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": {
                "file": record.filename,
                "line": record.lineno,
                "function": record.funcName
            }
        }
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_obj['correlation_id'] = record.correlation_id
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)
        
        # Add exception info
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

# Configure root logger
def setup_logging():
    """Configure structured JSON logging"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Remove default handler
    root_logger.removeHandler(default_handler)
    
    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_dir = Path('/home/coe/.openclaw/workspace/colony-os-app/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        log_dir / 'coe-kernel.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)
    
    return root_logger

logger = setup_logging()

# ============================================================================
# Prometheus Metrics
# ============================================================================

# Create a custom registry
registry = CollectorRegistry()

# Request metrics
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint', 'status'],
    registry=registry
)

request_total = Counter(
    'request_total',
    'Total number of requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

# Task metrics
task_total = Counter(
    'task_total',
    'Total number of tasks',
    ['status'],
    registry=registry
)

# System metrics
memory_usage = Gauge(
    'memory_usage_bytes',
    'Current memory usage in bytes',
    ['type'],
    registry=registry
)

db_pool_size = Gauge(
    'db_connection_pool_size',
    'Database connection pool size',
    registry=registry
)

# Tool execution metrics
tool_execution_duration = Histogram(
    'tool_execution_duration_seconds',
    'Tool execution duration in seconds',
    ['tool_name'],
    registry=registry
)

# Custom application metrics
active_tasks = Gauge(
    'active_tasks',
    'Number of currently active tasks',
    registry=registry
)

error_rate = Counter(
    'error_total',
    'Total number of errors',
    ['type'],
    registry=registry
)

# ============================================================================
# Flask App Setup
# ============================================================================

app = Flask(__name__)
task_manager = TaskManager(db_path=DATABASE_PATH)

# ============================================================================
# Middleware
# ============================================================================

@app.before_request
def before_request():
    """Set up request context"""
    g.start_time = time.time()
    g.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
    g.request_id = str(uuid.uuid4())
    
    # Log request
    logger.info(
        f"Request started: {request.method} {request.path}",
        extra={
            'correlation_id': g.correlation_id,
            'extra': {
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.user_agent.string if request.user_agent else None
            }
        }
    )

@app.after_request
def after_request(response):
    """Record metrics and log response"""
    duration = time.time() - g.start_time
    
    # Record Prometheus metrics
    endpoint = request.endpoint or 'unknown'
    status = str(response.status_code)
    
    request_duration.labels(
        method=request.method,
        endpoint=endpoint,
        status=status
    ).observe(duration)
    
    request_total.labels(
        method=request.method,
        endpoint=endpoint,
        status=status
    ).inc()
    
    # Add correlation ID to response
    response.headers['X-Correlation-ID'] = g.correlation_id
    response.headers['X-Request-ID'] = g.request_id
    
    # Log response
    logger.info(
        f"Request completed: {request.method} {request.path} - {response.status_code}",
        extra={
            'correlation_id': g.correlation_id,
            'extra': {
                'request_id': g.request_id,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_seconds': duration
            }
        }
    )
    
    return response

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    error_rate.labels(type=type(error).__name__).inc()
    
    logger.error(
        f"Unhandled error: {str(error)}",
        extra={
            'correlation_id': getattr(g, 'correlation_id', 'unknown'),
            'extra': {
                'error_type': type(error).__name__,
                'error_message': str(error)
            }
        },
        exc_info=True
    )
    
    return jsonify({
        "error": "Internal server error",
        "correlation_id": getattr(g, 'correlation_id', 'unknown')
    }), 500

# ============================================================================
# Health Check Endpoints
# ============================================================================

def check_postgresql() -> Dict[str, Any]:
    """Check PostgreSQL connectivity"""
    try:
        # Currently using SQLite, but structure supports PostgreSQL migration
        conn = sqlite3.connect(DATABASE_PATH, timeout=5)
        cursor = conn.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        return {"status": "healthy", "type": "sqlite", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity"""
    try:
        r = redis.from_url(REDIS_URL, socket_connect_timeout=5)
        r.ping()
        info = r.info()
        return {
            "status": "healthy",
            "version": info.get('redis_version'),
            "used_memory": info.get('used_memory_human'),
            "connected_clients": info.get('connected_clients')
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def check_openai() -> Dict[str, Any]:
    """Check OpenAI API availability"""
    try:
        if not OPENAI_API_KEY:
            return {"status": "unknown", "message": "API key not configured"}
        
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        # Lightweight models list call
        models = client.models.list(limit=1)
        return {"status": "healthy", "message": "API accessible"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def check_disk_space() -> Dict[str, Any]:
    """Check disk space"""
    try:
        disk = psutil.disk_usage('/')
        total_gb = disk.total / (1024**3)
        used_gb = disk.used / (1024**3)
        free_gb = disk.free / (1024**3)
        percent_used = disk.percent
        
        status = "healthy" if percent_used < 90 else "warning" if percent_used < 95 else "critical"
        
        return {
            "status": status,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent_used": percent_used
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

def check_memory() -> Dict[str, Any]:
    """Check memory usage"""
    try:
        mem = psutil.virtual_memory()
        
        # Update Prometheus gauge
        memory_usage.labels(type='used').set(mem.used)
        memory_usage.labels(type='available').set(mem.available)
        memory_usage.labels(type='total').set(mem.total)
        
        status = "healthy" if mem.percent < 80 else "warning" if mem.percent < 90 else "critical"
        
        return {
            "status": status,
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_percent": mem.percent,
            "cached_gb": round(getattr(mem, 'cached', 0) / (1024**3), 2)
        }
    except Exception as e:
        return {"error": str(e)}

def get_system_stats() -> Dict[str, Any]:
    """Get comprehensive system statistics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else None
        
        return {
            "cpu_percent": cpu_percent,
            "cpu_count": cpu_count,
            "load_average": load_avg,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.route('/v1/health', methods=['GET'])
def health_detailed():
    """Detailed health check endpoint"""
    checks = {
        "database": check_postgresql(),
        "redis": check_redis(),
        "openai": check_openai(),
        "disk": check_disk_space(),
        "memory": check_memory(),
        "system": get_system_stats()
    }
    
    # Determine overall status
    statuses = [c.get('status') for c in checks.values() if isinstance(c, dict)]
    if any(s == 'critical' for s in statuses):
        overall_status = "critical"
        status_code = 503
    elif any(s == 'unhealthy' for s in statuses):
        overall_status = "unhealthy"
        status_code = 503
    elif any(s == 'warning' for s in statuses):
        overall_status = "degraded"
        status_code = 200
    else:
        overall_status = "healthy"
        status_code = 200
    
    response = {
        "status": overall_status,
        "app": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks
    }
    
    return jsonify(response), status_code

@app.route('/healthz', methods=['GET'])
def healthz():
    """Simple health check for load balancers"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200

@app.route('/ready', methods=['GET'])
def ready():
    """Kubernetes readiness probe"""
    checks = {
        "database": check_postgresql(),
        "memory": check_memory()
    }
    
    is_ready = all(
        c.get('status') in ['healthy', 'warning', 'unknown']
        for c in checks.values()
    )
    
    if is_ready:
        return jsonify({
            "status": "ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 200
    else:
        return jsonify({
            "status": "not_ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 503

@app.route('/live', methods=['GET'])
def liveness():
    """Kubernetes liveness probe"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200

# ============================================================================
# Prometheus Metrics Endpoint
# ============================================================================

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    # Update dynamic gauges
    try:
        # Update task counts
        stats = task_manager.get_stats()
        for status, data in stats.get('by_status', {}).items():
            active_tasks.set(data.get('count', 0))
    except Exception as e:
        logger.error(f"Failed to update task metrics: {e}")
    
    return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)

# ============================================================================
# Original API Endpoints (Enhanced)
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "app": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "endpoints": [
            "/v1/health",
            "/healthz",
            "/ready",
            "/live",
            "/metrics",
            "/tasks",
            "/tasks/<id>",
            "/tasks/<id>/complete"
        ]
    })

@app.route('/tasks', methods=['GET'])
def list_tasks():
    """List all tasks"""
    tasks = task_manager.list_tasks()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    data = request.json
    task = task_manager.create_task(
        title=data.get('title'),
        description=data.get('description'),
        task_type=data.get('type', 'general'),
        priority=data.get('priority', 3),
        complexity=data.get('complexity', 2),
        created_by=data.get('created_by', 'system'),
        tags=data.get('tags', [])
    )
    
    # Increment task counter
    task_total.labels(status='created').inc()
    
    logger.info(
        f"Task created: {task.id}",
        extra={
            'correlation_id': g.correlation_id,
            'extra': {
                'task_id': task.id,
                'task_title': task.title
            }
        }
    )
    
    return jsonify(task.to_dict()), 201

@app.route('/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    task = task_manager.get_task(task_id)
    if task:
        return jsonify(task.to_dict())
    return jsonify({"error": "Task not found"}), 404

@app.route('/tasks/<task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as complete"""
    success = task_manager.complete_task(task_id)
    if success:
        task_total.labels(status='completed').inc()
        
        logger.info(
            f"Task completed: {task_id}",
            extra={
                'correlation_id': g.correlation_id,
                'extra': {'task_id': task_id}
            }
        )
        
        return jsonify({"status": "completed"})
    return jsonify({"error": "Task not found"}), 404

# ============================================================================
# SSL/TLS Setup
# ============================================================================

def create_ssl_context() -> ssl.SSLContext:
    """Create SSL context with TLS 1.3"""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Enable TLS 1.3 (and 1.2 for compatibility)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED
    
    # Load certificate and key
    if os.path.exists(SSL_CERT_PATH) and os.path.exists(SSL_KEY_PATH):
        context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
        logger.info("SSL certificates loaded successfully")
    else:
        logger.warning("SSL certificates not found, HTTPS will not be available")
    
    # Security settings
    context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    
    return context

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('APP_PORT', 8080))
    host = os.getenv('APP_HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting {APP_NAME} v{APP_VERSION} on {host}:{port}")
    
    if USE_SSL and os.path.exists(SSL_CERT_PATH):
        ssl_context = create_ssl_context()
        logger.info("HTTPS enabled with TLS 1.3")
        app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)
    else:
        logger.info("Running in HTTP mode (set USE_SSL=true for HTTPS)")
        app.run(host=host, port=port, debug=debug)
