# COE Kernel — Deterministic Gap Resolution Engineering

> **Scope:** All gaps, questions, and architectural issues across Phase 1 (Kernel), Phase 2 (Event Bus), Phase 3 (Agent Orchestration)
> **Resolution posture:** Temperature 0. Every gap gets a concrete, implementable, deterministic solution. No ambiguity remains.
> **Target:** AGI/ASI-ready agent kernel — the trust boundary between uncontrolled intelligence and controlled execution

---

## Table of Contents

1. [Kernel Bootstrap & Root of Trust](#1-kernel-bootstrap--root-of-trust)
2. [Identity Service: Revocation, Delegation, Signing Authority](#2-identity-service)
3. [Policy Engine: Format, Versioning, Conflict Resolution](#3-policy-engine)
4. [Event Bus: Ordering, TTL, Correlation](#4-event-bus)
5. [Audit Ledger: Genesis, Scope, Rotation](#5-audit-ledger)
6. [Module Loader: Sandboxing, Versioning, Health](#6-module-loader)
7. [Secrets Vault: Key Management, Rotation, Expiry](#7-secrets-vault)
8. [Metering: Enforcement Loop, Platform Limits](#8-metering-layer)
9. [State Engine: Declaration Format, Persistence, Concurrency](#9-state-engine)
10. [Cross-Cutting: Concurrency, Error Model, Config, Persistence, Interfaces](#10-cross-cutting-architecture)
11. [Phase 2 Event Bus Gaps](#11-phase-2-event-bus-gaps)
12. [Phase 3 Agent Layer Gaps](#12-phase-3-agent-layer-gaps)

---

## 1. Kernel Bootstrap & Root of Trust

### Gap
The happy path says "Kernel starts → Admin user created" but never defines how the first identity is created without an existing authorized identity. This is the chicken-and-egg problem.

### Resolution

**Bootstrap is a distinct, audited kernel lifecycle phase — not a bypass of RBAC.**

```yaml
# config.yaml — bootstrap section
bootstrap:
  mode: "genesis"                    # "genesis" on first boot, "normal" thereafter
  root_keypair_path: "./keys/kernel_root.pem"
  admin_identity:
    name: "kernel_admin"
    role: "kernel_root"
    type: "user"
```

**Deterministic bootstrap sequence:**

```
1. Kernel reads config.yaml
2. IF mode == "genesis":
   a. Generate Ed25519 keypair → store at root_keypair_path
   b. Create GENESIS audit entry (previous_hash = SHA256("COE_KERNEL_GENESIS_v1"))
   c. Create kernel_root identity, signed by the new keypair
   d. Log identity creation to audit ledger
   e. Set config.yaml bootstrap.mode = "normal" (one-time mutation)
   f. Kernel is now live with exactly 1 identity
3. IF mode == "normal":
   a. Load keypair from root_keypair_path
   b. Verify audit chain integrity from genesis
   c. Reconstruct identity registry from persisted state
   d. Resume normal RBAC-enforced operation
```

**Trust chain:**

```mermaid
graph TD
    A["Ed25519 Root Keypair<br/>(generated at genesis)"] --> B["kernel_root identity<br/>(self-signed by root key)"]
    B --> C["admin identities<br/>(signed by kernel_root)"]
    C --> D["user identities<br/>(signed by admin)"]
    C --> E["agent identities<br/>(signed by admin)"]
    C --> F["module identities<br/>(signed by admin)"]
```

**Why Ed25519:** Deterministic signatures (no random nonce like ECDSA), fast, 32-byte keys, standard library support via `hashlib` + minimal pure-Python implementation, or `cryptography` package if the zero-external-deps rule relaxes to "standard + crypto."

**Constraint reconciliation:** The spec says "zero external dependencies except standard libraries." Ed25519 is not in Python stdlib. Two options:
1. Use HMAC-SHA256 for signatures (stdlib-only, symmetric — weaker but deterministic)
2. Allow `cryptography` as the **single** permitted external dependency (recommended)

> [!IMPORTANT]
> **Decision required:** HMAC-SHA256 (stdlib-only, symmetric keys) or Ed25519 (requires `cryptography` package, asymmetric, production-grade)?

---

## 2. Identity Service

### Gap 2a: No Identity Revocation

**Resolution: Add `revoke_identity()`, `suspend_identity()`, `reinstate_identity()`**

```python
class IdentityStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"       # Temporarily disabled, can be reinstated
    REVOKED = "revoked"           # Permanently disabled, cannot be reinstated

class Identity:
    id: UUID
    name: str
    type: Literal["user", "agent", "module"]
    role: str
    status: IdentityStatus        # NEW — defaults to ACTIVE
    created_at: str               # ISO8601
    updated_at: str               # ISO8601, NEW
    signature: str                # Signed by parent identity's key
    parent_id: Optional[UUID]     # NEW — who created this identity
```

**Enforcement rule:** Every kernel operation checks `identity.status == ACTIVE` before proceeding. Suspended/revoked identities receive a `KernelError(code="IDENTITY_INACTIVE")`. This check happens in the Policy Engine, not in each component — single enforcement point.

**Audit:** Every status change creates an audit entry with `action: "identity.status_changed"`, `old_status`, `new_status`, `actor_id`.

### Gap 2b: Signature Hash — Signed by Whom?

**Resolution:** Defined in §1 above. Every identity is signed by its parent identity's key. The root identity is self-signed by the kernel keypair. Signature is computed as:

```python
signature = HMAC_SHA256(
    key=parent_key,
    message=canonicalize(identity_fields_without_signature)
)
```

`canonicalize()` = JSON with sorted keys, no whitespace — deterministic byte sequence.

### Gap 2c: No Identity Delegation

**Resolution: Delegation Token Model**

```python
@dataclass(frozen=True)
class DelegationToken:
    token_id: UUID
    delegator_id: UUID          # The identity granting authority
    delegate_id: UUID           # The identity receiving authority (typically an agent)
    scope: list[str]            # Subset of delegator's capabilities
    expires_at: str             # ISO8601 — mandatory expiry
    created_at: str
    signature: str              # Signed by delegator's key

class IdentityService:
    def create_delegation(self, delegator_id, delegate_id, scope, ttl_seconds) -> DelegationToken
    def verify_delegation(self, token: DelegationToken) -> bool
    def revoke_delegation(self, token_id: UUID) -> None
```

**Policy integration:** When an agent invokes a capability, the Policy Engine checks:
1. Agent's own role permits the capability? → **No delegation needed**
2. Agent presents a delegation token? → Validate token signature, expiry, scope subset → allow if valid
3. Neither? → Reject

**Phase 3 alignment:** The agent manifest can reference `delegation_from: <user_id>` to auto-create a scoped delegation on load.

### Gap 2d: No Rate Limiting

**Resolution: Rate limit as a policy rule (see §3 below)**

Rate limits are not a property of identity — they are a policy constraint enforced per-identity by the Policy Engine. The Metering Layer provides the data; the Policy Engine evaluates the rule.

```json
{
  "rule_id": "rate_limit_agent_events",
  "type": "rate_limit",
  "target": { "identity_type": "agent" },
  "constraint": {
    "metric": "event_emissions",
    "window_seconds": 60,
    "max_count": 100
  },
  "action": "deny",
  "priority": 100
}
```

---

## 3. Policy Engine

### Gap 3a: No Policy Definition Format

**Resolution: JSON Rule Format with Deterministic Evaluation**

This is the most critical gap. The policy engine uses a **typed JSON rule set** — no DSL, no interpreted language, no Turing-complete evaluation.

#### Policy Rule Schema

```json
{
  "rule_id": "string (UUID)",
  "version": "integer (monotonically increasing)",
  "type": "enum: capability_check | budget_check | rate_limit | event_auth | scope_check",
  "description": "string",
  "priority": "integer (lower = evaluated first)",
  "conditions": {
    "identity_id": "UUID | null (null = applies to all)",
    "identity_type": "enum: user | agent | module | null",
    "role": "string | null",
    "capability": "string | null",
    "event_type": "string | null"
  },
  "constraint": {
    // Type-specific constraint payload — see below
  },
  "action": "enum: allow | deny",
  "enabled": "boolean"
}
```

#### Constraint Types

| Rule Type | Constraint Fields |
|---|---|
| `capability_check` | `{ "capabilities": ["list", "of", "allowed"] }` |
| `budget_check` | `{ "metric": "cost_usd", "max_value": 100.0, "period": "monthly" }` |
| `rate_limit` | `{ "metric": "event_emissions", "window_seconds": 60, "max_count": 100 }` |
| `event_auth` | `{ "allowed_event_types": ["invoice.*", "payment.created"] }` |
| `scope_check` | `{ "allowed_scopes": ["business_operator", "verifier"] }` |

#### Evaluation Algorithm (Deterministic)

```python
def evaluate(identity, capability, context) -> PolicyDecision:
    """
    1. Collect all enabled rules where conditions match
    2. Sort by priority (ascending = highest priority first)
    3. Evaluate in order:
       - First DENY wins → return DENY with rule_id
       - If no DENY and at least one ALLOW → return ALLOW
       - If no matching rules → return DENY (default-deny)
    """
```

**This is deny-by-default, first-deny-wins.** No ambiguity. No conflict resolution needed beyond priority ordering. Deterministic for identical input.

#### Policy Storage

Policies are loaded from `schemas/policies.json` at kernel boot. They are immutable at runtime. To update policies, the kernel must be restarted with updated files. This satisfies "zero runtime mutation."

### Gap 3b: Policy Versioning

**Resolution:** Each policy rule has an integer `version` field. When the kernel boots, it records the policy set hash in the audit ledger. Events are validated against the **current loaded policy set** — not historical versions. For audit replay, the audit entry records the `policy_version_hash` that was active at evaluation time, enabling forensic reconstruction.

```python
@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    rule_id: str
    policy_set_hash: str          # SHA256 of the entire loaded policy file
    timestamp: str
    identity_id: UUID
    capability: str
```

### Gap 3c: Policy Conflict Resolution

**Resolution:** Already resolved above — **first-deny-wins with priority ordering**. No conflict is possible because:
1. Rules are sorted by priority (ascending)
2. First `DENY` match terminates evaluation → deny
3. No `DENY` + at least one `ALLOW` → allow
4. No matches → default deny

### Gap 3d: Policy Dry-Run / Simulation

**Resolution:**

```python
class PolicyEngine:
    def evaluate(self, identity, capability, context, dry_run=False) -> PolicyDecision:
        decision = self._evaluate_rules(identity, capability, context)
        if not dry_run:
            self._audit_log(decision)
            if not decision.allowed:
                raise PolicyDeniedError(decision)
        return decision
```

Dry-run returns the `PolicyDecision` without logging to audit or raising exceptions. Operators can test policy changes by loading a candidate policy file and running dry-run evaluations against historical event data.

---

## 4. Event Bus

### Gap 4a: No Event Ordering Guarantee

**Resolution:** Phase 1 establishes the contract that Phase 2 implements:

**Total ordering within a single kernel instance.** Events are assigned a monotonically increasing `sequence_number` (64-bit integer) at publish time. Subscriber dispatch order is deterministic: sorted by subscriber UUID (lexicographic). This is single-threaded sequential — no parallelism in v1.

Add to the Phase 1 event format:

```json
{
  "event_id": "uuid",
  "sequence_number": 12345,
  "correlation_id": "uuid",
  "type": "invoice.created",
  "version": "1.0",
  "timestamp": "...",
  "origin": "module_id",
  "payload": {},
  "signature": "hash"
}
```

### Gap 4b: No Event TTL / Retention

**Resolution:**

```yaml
# config.yaml
event_store:
  max_events: 1000000                 # Hard cap
  retention_policy: "segment"          # "unlimited" | "segment" | "count"
  segment_size: 100000                 # Events per segment file
  archive_segments: true               # Move old segments to archive/
  archive_path: "./data/event_archive"
```

The event store operates in **segments**. Each segment is an append-only file of up to `segment_size` events. When a segment fills, it is sealed (hash-finalized) and a new segment opens. Sealed segments can be archived (moved to cold storage) without breaking the active event chain — the new segment's first entry references the sealed segment's final hash.

**For Phase 1 (in-memory):** Enforce `max_events` as a circular buffer with the oldest events evicted and their hashes preserved in a compaction record. Event store exposes `is_compacted(event_id) -> bool`.

### Gap 4c: Missing `correlation_id`

**Resolution:** Add `correlation_id: UUID` to the Phase 1 event format immediately (shown in §4a above). Default to `event_id` if no correlation chain exists. This prevents a Phase 2 migration.

---

## 5. Audit Ledger

### Gap 5a: No Genesis Entry

**Resolution:**

```python
GENESIS_HASH = hashlib.sha256(b"COE_KERNEL_GENESIS_v1").hexdigest()

class AuditLedger:
    def _create_genesis_entry(self) -> AuditEntry:
        return AuditEntry(
            entry_id=uuid4(),
            previous_hash=GENESIS_HASH,
            current_hash=None,     # Computed below
            event_id=None,
            actor_id="KERNEL",
            action="kernel.genesis",
            timestamp=now_iso8601(),
            metadata={"kernel_version": "1.0.0", "policy_set_hash": "..."}
        )
        # current_hash = SHA256(canonical(entry_without_current_hash))
```

The genesis constant is defined in the codebase, documented, and never changes. Every audit chain starts with this entry. Verification walks from genesis forward.

### Gap 5b: What Gets Audited

**Resolution: Every state-mutating kernel operation.** Define exhaustive audit scope:

| Component | Audited Operations |
|---|---|
| **Identity** | `register_user`, `register_agent`, `register_module`, `assign_role`, `revoke_identity`, `suspend_identity`, `reinstate_identity`, `create_delegation`, `revoke_delegation` |
| **Policy** | `policy_set_loaded` (at boot), `policy_evaluation` (every check, with decision) |
| **Event Bus** | `event_published`, `event_routed`, `event_dead_lettered`, `event_replayed` |
| **Module Loader** | `module_loaded`, `module_unloaded`, `module_rollback`, `capability_registered` |
| **Secrets** | `secret_stored`, `secret_retrieved`, `secret_revoked`, `secret_rotated` |
| **Metering** | `budget_exceeded` (enforcement events only — not every metric tick) |
| **State Engine** | `state_transition`, `state_machine_registered` |
| **Kernel** | `kernel_boot`, `kernel_shutdown`, `config_loaded` |

Non-mutating reads (e.g., `get_permissions()`) are NOT audited — they would flood the ledger.

### Gap 5c: Audit Log Rotation

**Resolution: Segmented append-only logs with cross-segment hash continuity.**

```python
class AuditLedger:
    SEGMENT_MAX_ENTRIES = 100_000

    def _seal_segment(self, segment: AuditSegment) -> str:
        """Returns the final hash of the sealed segment."""
        segment.sealed = True
        segment.seal_hash = SHA256(segment.entries[-1].current_hash + b"SEALED")
        return segment.seal_hash

    def _open_new_segment(self, previous_seal_hash: str) -> AuditSegment:
        """New segment's first entry references the sealed segment."""
        segment = AuditSegment(segment_id=next_id())
        bridge_entry = AuditEntry(
            previous_hash=previous_seal_hash,
            action="audit.segment_bridge",
            ...
        )
        segment.append(bridge_entry)
        return segment
```

Verification walks segments in order. Each segment's first entry proves continuity from the previous segment's seal hash. Tamper detection works across segment boundaries.

---

## 6. Module Loader

### Gap 6a: Module Sandboxing

**Resolution: Capability-restricted execution with import whitelisting.**

Full OS-level sandboxing (seccomp, namespaces) is not feasible in pure Python without external deps. Instead:

**Layer 1 — Static Analysis at Load Time:**

```python
FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "shutil", "socket", "http", 
                     "urllib", "ctypes", "importlib", "multiprocessing", "signal"}

class ModuleLoader:
    def _validate_module_source(self, module_path: Path) -> list[str]:
        """AST-scan all .py files for forbidden imports."""
        violations = []
        for py_file in module_path.glob("**/*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module_name = node.module or node.names[0].name
                    root_module = module_name.split(".")[0]
                    if root_module in FORBIDDEN_IMPORTS:
                        violations.append(f"{py_file}:{node.lineno}: imports {module_name}")
        return violations  # Non-empty → reject module
```

**Layer 2 — Runtime `__builtins__` Restriction:**

```python
SAFE_BUILTINS = {
    "len", "range", "enumerate", "zip", "map", "filter", "sorted",
    "min", "max", "sum", "abs", "round", "isinstance", "issubclass",
    "str", "int", "float", "bool", "list", "dict", "tuple", "set",
    "frozenset", "None", "True", "False", "print", "ValueError",
    "TypeError", "KeyError", "Exception"
}

def create_restricted_globals():
    restricted_builtins = {k: __builtins__[k] for k in SAFE_BUILTINS 
                           if k in __builtins__}
    restricted_builtins["__import__"] = _guarded_import  # Only allows pre-approved modules
    return {"__builtins__": restricted_builtins}
```

**Layer 3 — Audit-only enforcement:** Every module function call is logged to metering. If a module exhibits anomalous behavior (excessive CPU, unexpected file access), the metering → policy enforcement loop (§8) suspends it.

**This is defense-in-depth, not perfect isolation.** The spec should acknowledge: "Python modules operate in a shared process. Sandboxing is best-effort via static analysis + restricted builtins + audit monitoring. Full isolation requires subprocess/container boundaries in a future phase."

### Gap 6b: Module Versioning

**Resolution:**

```yaml
# module.yaml — version field is mandatory
name: "invoice_module"
version: "1.2.0"                     # semver
kernel_compatibility: ">=1.0.0"
```

**Rules:**
- Only **one version of a module may be loaded at a time.** No parallel version coexistence in Phase 1.
- Loading a new version requires `unload(old)` → `load(new)`. If load fails → `rollback()` restores old version.
- The module registry tracks `{module_name: {version, loaded_at, capabilities}}`.
- Subscribers registered by a module are **bound to the module identity**, not the version. When a module is reloaded, its subscriber registrations are re-validated against the new capabilities.

### Gap 6c: Module Health Checks

**Resolution:**

```python
from abc import ABC, abstractmethod

class ModuleInterface(ABC):
    @abstractmethod
    def initialize(self, kernel_context: "KernelContext") -> None: ...

    @abstractmethod
    def healthcheck(self) -> "HealthStatus": ...

    @abstractmethod
    def shutdown(self) -> None: ...

@dataclass(frozen=True)
class HealthStatus:
    healthy: bool
    message: str
    timestamp: str
    metrics: dict          # Module-specific metrics (e.g., queue depth)
```

The kernel runs periodic health checks (configurable interval). Unhealthy modules emit `module.unhealthy` events and are suspended after `max_unhealthy_checks` consecutive failures.

---

## 7. Secrets Vault

### Gap 7a: Encryption Key Management

**Resolution: PBKDF2-derived encryption key from a boot-time passphrase.**

```python
import hashlib
import os

class SecretsVault:
    def __init__(self, passphrase: str, salt_path: str = "./data/vault.salt"):
        # Salt is generated once at genesis, stored on disk
        if not os.path.exists(salt_path):
            self._salt = os.urandom(32)
            with open(salt_path, "wb") as f:
                f.write(self._salt)
        else:
            with open(salt_path, "rb") as f:
                self._salt = f.read()

        # Derive 256-bit encryption key
        self._key = hashlib.pbkdf2_hmac(
            "sha256",
            passphrase.encode("utf-8"),
            self._salt,
            iterations=600_000          # OWASP 2023 recommendation
        )
```

**Encryption:** AES-256-GCM using the derived key. Each secret gets a unique 12-byte nonce (stored alongside the ciphertext). Nonce reuse with the same key must be prevented — use a counter.

**Config:**
```yaml
# config.yaml
secrets:
  passphrase_env_var: "COE_KERNEL_VAULT_PASSPHRASE"  # Read from env, never from file
  salt_path: "./data/vault.salt"
  kdf_iterations: 600000
```

**The passphrase is provided at runtime via environment variable — never stored on disk.**

**Stdlib constraint:** AES-GCM is not in Python stdlib. Options:
1. Use `Fernet` from `cryptography` package (recommended — authenticated encryption)
2. Use XOR with HMAC for integrity (stdlib-only, weak but functional for Phase 1)

### Gap 7b: Secret Rotation

**Resolution:**

```python
class SecretsVault:
    def rotate_secret(self, module_id: UUID, key: str, new_value: bytes) -> None:
        """Atomically replace a secret value. Old value is wiped."""
        old_entry = self._store.get((module_id, key))
        if old_entry is None:
            raise KernelError("SECRET_NOT_FOUND", 
                              f"No secret '{key}' for module {module_id}")

        new_entry = SecretEntry(
            key=key,
            module_id=module_id,
            ciphertext=self._encrypt(new_value),
            version=old_entry.version + 1,      # Monotonic version
            created_at=now_iso8601(),
            expires_at=None
        )
        self._store[(module_id, key)] = new_entry
        self._audit("secret_rotated", module_id=module_id, 
                     key=key, version=new_entry.version)
```

### Gap 7c: Secret Expiry / TTL

**Resolution:**

```python
@dataclass
class SecretEntry:
    key: str
    module_id: UUID
    ciphertext: bytes
    version: int
    created_at: str
    expires_at: Optional[str]         # ISO8601 or None (no expiry)

class SecretsVault:
    def retrieve_secret(self, module_id: UUID, key: str) -> bytes:
        entry = self._store.get((module_id, key))
        if entry is None:
            raise KernelError("SECRET_NOT_FOUND")
        if entry.expires_at and parse_iso(entry.expires_at) < now():
            self._audit("secret_expired_access_denied", 
                         module_id=module_id, key=key)
            raise KernelError("SECRET_EXPIRED", 
                              f"Secret '{key}' expired at {entry.expires_at}")
        self._audit("secret_retrieved", module_id=module_id, key=key)
        return self._decrypt(entry.ciphertext)
```

Expired secrets are **not** auto-deleted — they remain in the store but are inaccessible. An explicit `revoke_secret()` removes them.

---

## 8. Metering Layer

### Gap 8a: Metering → Policy Enforcement Loop

**Resolution: Metering emits threshold-breach events that the Policy Engine subscribes to.**

```python
class MeteringLayer:
    def record(self, identity_id: UUID, metric: str, value: float) -> None:
        self._ledger[identity_id][metric] += value
        self._check_thresholds(identity_id, metric)

    def _check_thresholds(self, identity_id: UUID, metric: str) -> None:
        current = self._ledger[identity_id][metric]
        decision = self._policy_engine.evaluate(
            identity_id=identity_id,
            capability=f"metering.{metric}",
            context={"current_value": current}
        )
        if not decision.allowed:
            self._event_bus.publish(Event(
                type="system.budget_exceeded",
                payload={"identity_id": str(identity_id), 
                         "metric": metric, "value": current},
                origin="kernel.metering"
            ))
```

**The loop:** Metering records → Policy evaluates → Event emitted → subscriber (e.g., identity suspension handler) acts → deterministic enforcement.

### Gap 8b: CPU/Memory Measurement Platform Limitations

**Resolution: Use `time.monotonic()` for wall-clock execution time, `gc.get_objects()` for object count.**

```python
import time
import gc

class ExecutionMeter:
    def measure(self, callable, *args, **kwargs):
        start_time = time.monotonic()
        start_objects = len(gc.get_objects())

        result = callable(*args, **kwargs)

        elapsed = time.monotonic() - start_time
        object_delta = len(gc.get_objects()) - start_objects

        return MeteringRecord(
            wall_time_seconds=elapsed,
            object_count_delta=object_delta,
            result=result
        )
```

**Spec amendment:** Replace "CPU time (approx)" with "Wall-clock execution time." Replace "Memory allocation estimate" with "Tracked object count delta (best-effort)." Document explicitly that these are proxies.

---

## 9. State Engine

### Gap 9a: No FSM Declaration Format

**Resolution: YAML-defined state machines, loaded at module registration time.**

```yaml
# schemas/state_machines/invoice.yaml
name: "invoice"
version: "1.0"
initial_state: "draft"
states:
  - "draft"
  - "submitted"
  - "approved"
  - "paid"
  - "cancelled"
  - "void"
transitions:
  - from: "draft"
    to: "submitted"
    event: "invoice.submitted"
    required_capability: "submit_invoice"
  - from: "submitted"
    to: "approved"
    event: "invoice.approved"
    required_capability: "approve_invoice"
  - from: "submitted"
    to: "cancelled"
    event: "invoice.cancelled"
    required_capability: "cancel_invoice"
  - from: "approved"
    to: "paid"
    event: "invoice.paid"
    required_capability: "process_payment"
  - from: ["draft", "submitted"]
    to: "void"
    event: "invoice.voided"
    required_capability: "void_invoice"
```

**Validation at load:**
- All states in transitions must exist in the states list
- No orphan states (unreachable from initial)
- `required_capability` must exist in the capability registry
- `event` must exist in the event schema registry

### Gap 9b: State Persistence

**Resolution: Event-sourced state reconstruction.**

Current state is derived from the audit ledger. The State Engine maintains an **in-memory projection** of current states, but can reconstruct them from the audit trail on restart.

```python
class StateEngine:
    def __init__(self, audit_ledger: AuditLedger):
        self._current_states: dict[tuple[str, str], str] = {}
        # Key = (fsm_name, entity_id), Value = current_state

    def rebuild_from_audit(self) -> None:
        """Replay all state_transition audit entries to reconstruct."""
        for entry in self._audit_ledger.iterate(action="state_transition"):
            key = (entry.metadata["fsm_name"], entry.metadata["entity_id"])
            self._current_states[key] = entry.metadata["to_state"]

    def transition(self, fsm_name, entity_id, event_type, identity_id) -> str:
        current = self._current_states.get(
            (fsm_name, entity_id), 
            self._fsm_definitions[fsm_name].initial_state
        )
        # Validate transition exists
        # Validate identity has required_capability via Policy Engine
        # Apply transition
        # Log to audit
        # Return new state
```

**State survives kernel restart** because the audit ledger is persistent.

### Gap 9c: Concurrent State Machines (Multiple Instances)

**Resolution:** The state key is `(fsm_name, entity_id)` — not just `fsm_name`.

```python
# Two invoices, same FSM, different states — no conflict
engine.transition("invoice", "INV-001", "invoice.submitted", admin_id)
engine.transition("invoice", "INV-002", "invoice.approved", admin_id)

assert engine.get_state("invoice", "INV-001") == "submitted"
assert engine.get_state("invoice", "INV-002") == "approved"
```

---

## 10. Cross-Cutting Architecture

### Gap 10a: Concurrency Model

**Resolution: Explicitly single-threaded, synchronous, no parallelism in Phase 1.**

```
COE Kernel Concurrency Model — Phase 1

- All event dispatch is sequential
- All subscriber execution is sequential
- No threading, no asyncio, no multiprocessing
- The kernel processes one event at a time, start to finish

Phase 2+ roadmap:
- Cooperative async (asyncio) for I/O-bound subscribers
- Worker processes for isolation (subprocess with IPC)
- Event ordering must remain deterministic regardless
```

### Gap 10b: Unified Error Model

**Resolution:**

```python
class ErrorCode(Enum):
    # Identity errors (1xxx)
    IDENTITY_NOT_FOUND = 1001
    IDENTITY_DUPLICATE = 1002
    IDENTITY_INACTIVE = 1003
    IDENTITY_ROLE_UNDEFINED = 1004
    IDENTITY_ROLE_ESCALATION = 1005
    IDENTITY_DELEGATION_EXPIRED = 1006

    # Policy errors (2xxx)
    POLICY_DENIED = 2001
    POLICY_BUDGET_EXCEEDED = 2002
    POLICY_RATE_LIMITED = 2003

    # Event errors (3xxx)
    EVENT_SCHEMA_INVALID = 3001
    EVENT_SIGNATURE_INVALID = 3002
    EVENT_TYPE_UNKNOWN = 3003
    EVENT_VERSION_MISMATCH = 3004

    # Module errors (4xxx)
    MODULE_MANIFEST_INVALID = 4001
    MODULE_SIGNATURE_INVALID = 4002
    MODULE_DEPENDENCY_CIRCULAR = 4003
    MODULE_CAPABILITY_UNDECLARED = 4004

    # Secrets errors (5xxx)
    SECRET_NOT_FOUND = 5001
    SECRET_ACCESS_DENIED = 5002
    SECRET_EXPIRED = 5003

    # State errors (6xxx)
    STATE_TRANSITION_INVALID = 6001
    STATE_VERSION_MISMATCH = 6002
    STATE_FSM_NOT_FOUND = 6003

    # Audit errors (7xxx)
    AUDIT_INTEGRITY_VIOLATION = 7001
    AUDIT_CHAIN_BROKEN = 7002

    # System errors (9xxx)
    KERNEL_BOOTSTRAP_FAILED = 9001
    CONFIG_INVALID = 9002
    BACKPRESSURE_ACTIVE = 9003

@dataclass(frozen=True)
class KernelError(Exception):
    code: ErrorCode
    message: str
    context: Optional[dict] = None
    source_component: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "error_code": self.code.value,
            "error_name": self.code.name,
            "message": self.message,
            "context": self.context or {},
            "source": self.source_component
        }
```

**Every component raises `KernelError` — no bare exceptions, no string errors, no silent failures.**

### Gap 10c: Configuration Model

**Resolution: Fully specified `config.yaml` schema.**

```yaml
kernel:
  version: "1.0.0"
  mode: "production"                   # "production" | "development" | "testing"

bootstrap:
  mode: "normal"                       # "genesis" | "normal"
  root_keypair_path: "./keys/kernel_root.pem"
  admin_identity:
    name: "kernel_admin"
    role: "kernel_root"
    type: "user"

identity:
  max_identities: 10000
  signature_algorithm: "hmac_sha256"   # "hmac_sha256" | "ed25519"

policy:
  rules_path: "./schemas/policies.json"
  default_action: "deny"
  evaluation_order: "priority_ascending"

event_bus:
  max_queue_depth: 10000
  subscriber_timeout_seconds: 30
  max_subscribers_per_event: 100

event_store:
  backend: "file"                      # "memory" | "file"
  file_path: "./data/events/"
  max_events: 1000000
  segment_size: 100000

audit:
  backend: "file"                      # "memory" | "file"
  file_path: "./data/audit/"
  segment_max_entries: 100000
  genesis_constant: "COE_KERNEL_GENESIS_v1"

module_loader:
  modules_path: "./modules/"
  forbidden_imports: ["os", "sys", "subprocess", "shutil", "socket",
                      "http", "urllib", "ctypes", "importlib",
                      "multiprocessing", "signal"]
  max_load_retries: 3
  healthcheck_interval_seconds: 60
  max_unhealthy_checks: 3

secrets:
  passphrase_env_var: "COE_KERNEL_VAULT_PASSPHRASE"
  salt_path: "./data/vault.salt"
  kdf_iterations: 600000
  backend: "file"                      # "memory" | "file"
  file_path: "./data/secrets/"

metering:
  flush_interval_seconds: 10
  backend: "memory"

state_engine:
  definitions_path: "./schemas/state_machines/"
  rebuild_on_boot: true

logging:
  level: "INFO"
  format: "json"
```

**Validation:** The kernel validates `config.yaml` against a JSON Schema at boot. Invalid config → `KernelError(CONFIG_INVALID)` → kernel refuses to start.

### Gap 10d: Persistence Model

| Component | Default | Survives Restart? | Mechanism |
|---|---|---|---|
| **Audit Ledger** | `file` | ✅ Yes | Append-only segmented files |
| **Event Store** | `file` | ✅ Yes | Append-only segmented files |
| **Identity Registry** | `file` | ✅ Yes | JSON snapshot + audit reconstruction |
| **Policy Rules** | `file` | ✅ Yes | Static file, loaded at boot |
| **Secrets Vault** | `file` | ✅ Yes | Encrypted file per module scope |
| **Metering** | `memory` | ❌ No | Reset on restart, reconstructable from audit |
| **State Engine** | `audit` | ✅ Yes | Rebuilt from audit ledger on boot |
| **Module Registry** | `reload` | ✅ Yes | Modules re-scanned and re-loaded |

### Gap 10e: Python ABCs for All Components

**Resolution:** Define in `kernel/core/interfaces.py` — every component has a formal ABC. Tests mock the interface. Phase 2–3 extend, never replace.

```python
# kernel/core/interfaces.py
class IdentityServiceInterface(ABC):
    def register_user(self, name, role) -> Identity: ...
    def register_agent(self, name, role) -> Identity: ...
    def register_module(self, name, role) -> Identity: ...
    def assign_role(self, identity_id, role, actor_id) -> None: ...
    def revoke_identity(self, identity_id, actor_id) -> None: ...
    def suspend_identity(self, identity_id, actor_id) -> None: ...
    def get_permissions(self, identity_id) -> list[str]: ...

class PolicyEngineInterface(ABC):
    def evaluate(self, identity_id, capability, context, dry_run=False) -> PolicyDecision: ...
    def load_rules(self, rules_path) -> None: ...

class EventBusInterface(ABC):
    def publish(self, event: Event) -> None: ...
    def subscribe(self, event_type, version, subscriber_id, handler) -> None: ...
    def unsubscribe(self, subscriber_id, event_type) -> None: ...

class AuditLedgerInterface(ABC):
    def append(self, entry: AuditEntry) -> None: ...
    def verify_integrity(self) -> bool: ...
    def iterate(self, action=None) -> Iterator[AuditEntry]: ...

class ModuleLoaderInterface(ABC):
    def load(self, module_path) -> None: ...
    def unload(self, module_name) -> None: ...
    def rollback(self, module_name) -> None: ...

class SecretsVaultInterface(ABC):
    def store_secret(self, module_id, key, value, ttl=None) -> None: ...
    def retrieve_secret(self, module_id, key) -> bytes: ...
    def revoke_secret(self, module_id, key) -> None: ...
    def rotate_secret(self, module_id, key, new_value) -> None: ...

class MeteringInterface(ABC):
    def record(self, identity_id, metric, value) -> None: ...
    def get_usage(self, identity_id) -> dict: ...

class StateEngineInterface(ABC):
    def register_fsm(self, definition) -> None: ...
    def transition(self, fsm_name, entity_id, event_type, identity_id) -> str: ...
    def get_state(self, fsm_name, entity_id) -> str: ...
```

---

## 11. Phase 2 Event Bus Gaps

### Gap 11a: Subscriber Isolation — Memory Boundary

**Resolution:** Object count monitoring only. True isolation requires subprocess. Documented as best-effort.

```python
class IsolationLayer:
    def execute_subscriber(self, handler, event, timeout, max_objects):
        objects_before = len(gc.get_objects())
        result = self._execute_with_timeout(handler, event, timeout)
        delta = len(gc.get_objects()) - objects_before
        if delta > max_objects:
            self._audit("subscriber_memory_abuse", delta=delta)
        return result
```

### Gap 11b: Backpressure — No Draining Strategy

**Resolution: Hysteresis-based backpressure with separate activate/deactivate thresholds.**

```python
class BackpressureController:
    def __init__(self, activate_threshold: int, deactivate_threshold: int):
        self._activate = activate_threshold      # e.g., 10000
        self._deactivate = deactivate_threshold   # e.g., 7000
        self._active = False

    def check(self, queue_depth: int) -> bool:
        if not self._active and queue_depth >= self._activate:
            self._active = True
            # Emit system.backpressure.activated
        elif self._active and queue_depth <= self._deactivate:
            self._active = False
            # Emit system.backpressure.deactivated
        return self._active
```

### Gap 11c: Replay — Idempotency

**Resolution:** Replayed events carry `replay_context` metadata:

```json
{
  "event_id": "original-uuid",
  "replay_context": {
    "is_replay": true,
    "replay_id": "replay-uuid",
    "original_timestamp": "...",
    "replay_timestamp": "..."
  }
}
```

Subscribers check `event.replay_context.is_replay` to decide side-effect behavior. Replay engine does NOT create new event store entries.

---

## 12. Phase 3 Agent Layer Gaps

### Gap 12a: Task Submission Format

**Resolution:**

```json
{
  "type": "agent.task_submitted",
  "version": "1.0",
  "payload": {
    "task_id": "uuid",
    "agent_id": "uuid",
    "instruction": "Create invoice for $100",
    "context": {},
    "constraints": {
      "max_reasoning_steps": 5,
      "max_tokens": 2000,
      "timeout_seconds": 30,
      "deterministic_mode": false
    }
  }
}
```

### Gap 12b: Multi-Step Orchestration Loop

**Resolution: Finite execution cycle with hard upper bound.**

```python
class Orchestrator:
    def execute_task(self, task: AgentTask) -> OrchestratorResult:
        steps = []
        for step_number in range(task.constraints["max_reasoning_steps"]):
            ai_response = self._ai_provider.reason(
                prompt=self._build_prompt(task, steps),
                constraints=task.constraints
            )
            if ai_response["action"] == "complete":
                return OrchestratorResult(status="completed", steps=steps)

            capability = ai_response["capability"]
            if not self._policy_enforcer.check(task.agent_id, capability):
                return OrchestratorResult(status="policy_denied", steps=steps)

            event = self._build_capability_event(task, capability, ai_response["params"])
            self._event_bus.publish(event)

            response = self._await_response(event.correlation_id, timeout=30)
            steps.append(ExecutionStep(step=step_number, capability=capability,
                                       request=ai_response, response=response))

        return OrchestratorResult(status="max_steps_exceeded", steps=steps)
```

**Infinite loops are structurally impossible** — the `for` loop has a hard upper bound.

### Gap 12c: Agent Crash Isolation

**Resolution:** Every agent execution wrapped in a try/except at orchestrator level:

```python
class Orchestrator:
    def safe_execute(self, task: AgentTask) -> OrchestratorResult:
        try:
            return self.execute_task(task)
        except KernelError as e:
            self._audit("agent_execution_error", error=e.to_dict())
            return OrchestratorResult(status="error", error=e)
        except Exception as e:
            self._audit("agent_unhandled_exception", error=str(e))
            return OrchestratorResult(status="crashed", error=str(e))
```

### Gap 12d: AI Provider Hidden State Prevention

**Resolution:** AI providers receive history explicitly via parameter. No mutable state methods on interface. Fresh provider instance per task.

```python
class AIProvider(ABC):
    @abstractmethod
    def reason(self, prompt: str, constraints: dict, 
               history: list[dict]) -> dict:
        """Provider MUST NOT store state between calls.
        History is passed explicitly by the orchestrator."""
        ...
```

Enforced by: (1) interface contract, (2) test: identical inputs → identical outputs, (3) fresh instance per task.

---

## Decisions Required from Spec Author

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Crypto library | stdlib HMAC-SHA256 only vs. allow `cryptography` | Allow `cryptography` |
| 2 | AES for secrets vault | XOR+HMAC (stdlib) vs. Fernet (`cryptography`) | Allow `cryptography` |
| 3 | Metering persistence | In-memory vs. file-backed | In-memory Phase 1 |
| 4 | Module sandboxing depth | Static analysis only vs. builtins restriction vs. subprocess | Static + builtins Phase 1 |
| 5 | Event store default | Memory vs. file-backed | File-backed |

> [!TIP]
> All other gaps have deterministic resolutions above that do not require further decisions. These five items are genuine trade-offs where spec author intent determines the answer.
