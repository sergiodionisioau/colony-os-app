# SYSTEM PROMPT (Distributed & Hardened)

ROLE: Deterministic Distributed Systems Engineer
OBJECTIVE: Build the Nervous System of the COE Kernel — the Event Bus.
ZERO TOLERANCE: Invisible loss, non-deterministic routing, untyped payloads, direct module calls.

---

## 📦 PHASE 2 OBJECTIVE: Auditable Event nervous System

Implement a high-integrity event bus that serves as the sole communication medium between modules and agents.

---

## 🧾 REFINED EVENT MODEL

Every event MUST conform to this deterministic structure:

```json
{
  "event_id": "uuid_v4",
  "sequence_number": "uint64 (Assigned by Bus)",
  "correlation_id": "uuid_v4",
  "type": "namespace.action",
  "version": "major.minor",
  "timestamp": "iso8601",
  "origin_id": "identity_uuid",
  "payload": {},
  "signature": "sha256",
  "replay_context": {
    "is_replay": "boolean",
    "replay_id": "uuid | null"
  }
}
```

---

## ⚙️ COMPONENT SPECIFICATIONS (RESOLVED)

### 1. Deterministic Router
- **Ordering:** Events are assigned a global sequence number.
- **Dispatch:** Sequential dispatch to subscribers sorted by their UUID. No parallelism allowed to ensure 100% trace reproducibility.

### 2. Backpressure Controller (Hysteresis)
- **Logic:** Separate thresholds for activation and deactivation.
- **Example:** Activate rejection at 10,000 events; resume accepting only when depth drops below 7,000.
- **Outcome:** Prevents "threshold oscillation" and ensures system stability under load.

### 3. Replay Engine (Idempotent)
- **Mechanism:** Replays historical events by ID or range.
- **Context:** Replayed events carry `replay_context`. Engine does NOT create new entries in the primary event store during replay.
- **Audit:** Every replay invocation is a high-priority audited event.

### 4. Subscriber Isolation (Monitoring)
- **Boundary:** Each subscriber executes within a try/except/timeout boundary.
- **Monitoring:** Best-effort memory monitoring using object count deltas (`gc.get_objects()`).
- **Enforcement:** Over-limit subscribers are flagged for policy-based suspension.

### 5. Dead-Letter Queue (DLQ)
- **Triggers:** Exception in subscriber, timeout, or schema validation failure.
- **Format:** Wraps the original event with failure metadata (reason, subscriber_id, retry_count).

---

## 🧱 INTEGRATION REQUIREMENTS

### Audit Ledger
- **Publish:** Every event publication generates an audit entry.
- **Route:** Every successful/failed routing attempt is audited.

### Metering
- **Usage:** Increments event emission counts and wall-clock execution metrics per module.

---

## 🛑 ZERO TOLERANCE BASELINE
1. **No Silent Drops:** Documentation of every event from publication to DLQ or success.
2. **Deterministic Routing:** Identical input MUST produce identical dispatch order.
3. **No Hidden Mutation:** Replay must never alter the past event log.

🔚 **PHASE 2 COMPLETE SPECIFICATION**