# COE Kernel — REST/FastAPI Social Contract

## 🎯 Purpose

This document defines the **social contract** between the COE Kernel and external systems via a REST API. It establishes protocols for:
- **Agents**: Registration, lifecycle, task execution
- **Data Management**: Database connections, queries, migrations
- **Tools**: Discovery, invocation, versioning
- **Metrics**: Observability, health, performance
- **Modules**: Hot-swap, loading, unloading

---

## 🛑 Zero Tolerance Contract Terms

### 1. Explicit Authorization
Every API call MUST include:
- `X-Identity-ID`: UUID of the calling identity
- `X-Request-Signature`: HMAC-SHA256 of request
- `X-Timestamp`: ISO 8601 timestamp (±30s clock skew allowed)

### 2. Audit Trail Guarantee
Every API call results in exactly one audit entry:
```json
{
  "actor_id": "<identity_id>",
  "action": "api.<endpoint>.<method>",
  "status": "SUCCESS|DENIED|FAILED",
  "metadata": {
    "endpoint": "/v1/agents/register",
    "request_id": "<uuid>",
    "duration_ms": 42
  }
}
```

### 3. Hot-Swap Guarantee
Any component (module, agent, DB, tool) can be hot-swapped with:
- Zero downtime
- Automatic rollback on failure
- Audit trail of swap operation
- Health verification before cutover

### 4. Deterministic Responses
Identical requests produce identical responses (given same kernel state).

---

## 🌐 API Contract Specification

### Base URL
```
https://kernel.coe.local/v1
```

### Authentication
```http
GET /v1/health
X-Identity-ID: <uuid>
X-Timestamp: 2026-03-26T13:30:00Z
X-Request-Signature: <hmac-sha256>
```

Signature computation:
```python
signature = hmac_sha256(
    key=identity_signing_key,
    message=f"{method}:{path}:{timestamp}:{body_hash}"
)
```

---

## 📡 Endpoints

### 1. AGENTS

#### POST /v1/agents/register
Register a new agent with the kernel.

**Request:**
```json
{
  "agent_id": "prospector-alpha",
  "role": "revenue_agent",
  "capabilities": ["SIGNAL_HARVESTING", "EMAIL_OUTREACH"],
  "token_budget": 100000,
  "constraints": {
    "max_steps": 10,
    "timeout_seconds": 300
  }
}
```

**Response:**
```json
{
  "identity_id": "<uuid>",
  "status": "registered",
  "allocated_budget": 100000,
  "event_stream": "/v1/events/stream?agent_id=<uuid>"
}
```

**Audit Action**: `api.agents.register`

---

#### POST /v1/agents/{id}/tasks
Submit a task to an agent.

**Request:**
```json
{
  "instruction": "Analyze Q1 leads for high-intent signals",
  "context": {
    "time_range": "2026-01-01/2026-03-31",
    "min_confidence": 0.7
  },
  "correlation_id": "<uuid>"
}
```

**Response:**
```json
{
  "task_id": "<uuid>",
  "status": "accepted",
  "estimated_completion": "2026-03-26T13:35:00Z"
}
```

---

#### GET /v1/agents/{id}/tasks/{task_id}
Get task status and results.

**Response:**
```json
{
  "task_id": "<uuid>",
  "status": "completed",
  "steps_taken": 5,
  "result": {
    "signals_found": 42,
    "high_intent_leads": ["lead-001", "lead-002"]
  },
  "audit_trail": ["<entry_id_1>", "<entry_id_2>"]
}
```

---

#### DELETE /v1/agents/{id}
Unregister an agent.

**Response:**
```json
{
  "status": "unregistered",
  "final_budget_remaining": 5234,
  "audit_summary": "/v1/audit?actor_id=<uuid>"
}
```

---

### 2. DATA MANAGEMENT

#### GET /v1/data/connections
List configured database connections.

**Response:**
```json
{
  "connections": [
    {
      "id": "primary-postgres",
      "type": "postgresql",
      "status": "healthy",
      "pool_size": 20,
      "active_connections": 5,
      "last_health_check": "2026-03-26T13:29:55Z"
    }
  ]
}
```

---

#### POST /v1/data/connections
Add a new database connection (hot-swap capable).

**Request:**
```json
{
  "id": "analytics-replica",
  "type": "postgresql",
  "host": "analytics.db.internal",
  "port": 5432,
  "database": "analytics",
  "credentials_ref": "vault://secrets/analytics-db",
  "pool_config": {
    "min_size": 5,
    "max_size": 20,
    "max_overflow": 10
  }
}
```

**Response:**
```json
{
  "status": "connected",
  "connection_id": "analytics-replica",
  "health_check_passed": true,
  "failover_ready": true
}
```

---

#### POST /v1/data/connections/{id}/rotate-credentials
Rotate database credentials without downtime.

**Response:**
```json
{
  "status": "rotated",
  "old_credential_revoked": true,
  "new_credential_active": true,
  "connections_drained": 5,
  "zero_downtime": true
}
```

---

#### POST /v1/data/query
Execute a read-only query (audited).

**Request:**
```json
{
  "connection_id": "primary-postgres",
  "query": "SELECT * FROM signals WHERE confidence > :min_conf",
  "parameters": {"min_conf": 0.7},
  "read_only": true
}
```

**Response:**
```json
{
  "rows": [...],
  "row_count": 42,
  "execution_time_ms": 15,
  "audit_entry_id": "<uuid>"
}
```

---

### 3. TOOLS

#### GET /v1/tools
List available tools.

**Response:**
```json
{
  "tools": [
    {
      "id": "email_sender",
      "version": "2.1.0",
      "capabilities": ["SEND_EMAIL", "TRACK_OPENS"],
      "schema": {
        "input": {...},
        "output": {...}
      },
      "health": "healthy"
    }
  ]
}
```

---

#### POST /v1/tools/{id}/invoke
Invoke a tool.

**Request:**
```json
{
  "parameters": {
    "to": "user@example.com",
    "subject": "Welcome",
    "body": "..."
  },
  "correlation_id": "<uuid>"
}
```

**Response:**
```json
{
  "invocation_id": "<uuid>",
  "status": "success",
  "result": {
    "message_id": "msg-123",
    "delivered": true
  },
  "metering": {
    "tokens_consumed": 150,
    "compute_ms": 245
  }
}
```

---

#### POST /v1/tools/register
Register a new tool (hot-swap capable).

**Request:**
```json
{
  "id": "slack_notifier",
  "version": "1.0.0",
  "entrypoint": "tools.slack:Notifier",
  "schema": {...},
  "permissions": ["bus_publish"]
}
```

---

### 4. METRICS

#### GET /v1/metrics
Prometheus-compatible metrics.

**Response:**
```
# HELP coe_events_published_total Total events published
# TYPE coe_events_published_total counter
coe_events_published_total 15234

# HELP coe_policy_evaluations_duration_seconds Policy evaluation latency
# TYPE coe_policy_evaluations_duration_seconds histogram
coe_policy_evaluations_duration_seconds_bucket{le="0.01"} 1024
...
```

---

#### GET /v1/metrics/health
Detailed health status.

**Response:**
```json
{
  "kernel": "healthy",
  "subsystems": {
    "event_bus": "healthy",
    "policy_engine": "healthy",
    "audit_ledger": "healthy",
    "module_loader": "healthy"
  },
  "modules": {
    "crm": "healthy",
    "social_media": "not_loaded"
  },
  "checks": {
    "audit_chain_integrity": "pass",
    "event_store_writable": "pass",
    "policy_rules_loaded": "pass"
  }
}
```

---

### 5. MODULES

#### GET /v1/modules
List loaded modules.

**Response:**
```json
{
  "modules": [
    {
      "id": "crm",
      "version": "1.0.0",
      "status": "active",
      "capabilities": ["REVENUE_GRAPH_UPDATE"],
      "events_subscribed": ["revenue.signal.detected"],
      "health": "healthy",
      "loaded_at": "2026-03-26T12:00:00Z"
    }
  ]
}
```

---

#### POST /v1/modules/load
Load a new module.

**Request:**
```json
{
  "module_id": "social-media",
  "path": "/opt/coe/modules/social-media",
  "activation": "immediate"
}
```

**Response:**
```json
{
  "status": "loaded",
  "module_id": "social-media",
  "version": "1.0.0",
  "health_check": "passed",
  "events_registered": ["social.post.requested"]
}
```

---

#### POST /v1/modules/{id}/hot-swap
Hot-swap a module.

**Request:**
```json
{
  "new_version_path": "/opt/coe/modules/social-media-v2",
  "verification": {
    "run_tests": true,
    "shadow_traffic": true
  }
}
```

**Response:**
```json
{
  "status": "swapped",
  "module_id": "social-media",
  "old_version": "1.0.0",
  "new_version": "2.0.0",
  "shadow_verification": "passed",
  "rollback_available": true
}
```

---

#### POST /v1/modules/{id}/rollback
Rollback to previous version.

**Response:**
```json
{
  "status": "rolled_back",
  "module_id": "social-media",
  "current_version": "1.0.0",
  "previous_version": "2.0.0",
  "rollback_time_ms": 523
}
```

---

#### DELETE /v1/modules/{id}
Unload a module.

**Response:**
```json
{
  "status": "unloaded",
  "module_id": "social-media",
  "cleanup": {
    "event_handlers_removed": 5,
    "memory_freed_mb": 12
  }
}
```

---

## 🔌 WebSocket Events

### /v1/events/stream
Real-time event stream for agents.

**Connection:**
```
wss://kernel.coe.local/v1/events/stream?identity_id=<uuid>&token=<jwt>
```

**Events:**
```json
{
  "event_id": "<uuid>",
  "type": "agent.task_assigned",
  "timestamp": "2026-03-26T13:30:00Z",
  "payload": {
    "task_id": "<uuid>",
    "instruction": "..."
  }
}
```

---

## 🛡️ Error Responses

### 401 Unauthorized
```json
{
  "error": "UNAUTHORIZED",
  "message": "Invalid or expired signature",
  "audit_entry_id": "<uuid>"
}
```

### 403 Forbidden
```json
{
  "error": "POLICY_DENIED",
  "message": "Capability AGENT_REGISTER not allowed for role 'guest'",
  "policy_decision": {...}
}
```

### 429 Rate Limited
```json
{
  "error": "RATE_LIMITED",
  "message": "Budget exceeded: 100000/100000 tokens consumed",
  "retry_after": 3600
}
```

### 503 Backpressure
```json
{
  "error": "BACKPRESSURE_ACTIVE",
  "message": "Event queue at capacity, retry after 5s",
  "queue_depth": 10000
}
```

---

## 📊 OpenAPI Schema

Available at:
```
GET /v1/openapi.json
GET /v1/docs (Swagger UI)
```

---

## 🔐 Security Contract

1. **TLS 1.3** required for all connections
2. **mTLS** optional for service-to-service
3. **Request signing** required for all mutations
4. **Audit logging** guaranteed for all requests
5. **Rate limiting** per identity per endpoint
6. **Payload size limits**: 1MB default, configurable per endpoint

---

## 🔄 Versioning

- URL versioning: `/v1/`, `/v2/`
- Backward compatibility: 2 major versions supported
- Deprecation warnings: 6 months advance notice

---

*Contract Version: 1.0*
*Kernel Version: 1.0.0*
*Baseline: Zero Tolerance*
