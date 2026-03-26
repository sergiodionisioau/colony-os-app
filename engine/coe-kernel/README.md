# COE Kernel - Autonomous Revenue Agent Command Center

The **COE Kernel** is a zero-trust, deterministic OS (operating system) designed to orchestrate autonomous agents and hardened logic layers. It serves as the authoritative hub for messaging, state management, security, and module lifecycle.

## Core Roles & Architecture

The kernel operates on a **Zero Tolerance Baseline**, enforcing strict boundaries between subsystems to ensure system integrity and deterministic behavior.

- **Lifecycle Management**: Deterministic boot sequence supporting **Genesis** and **Normal** modes via `KernelBootstrap`.
- **Security Orchestration**: Multi-level policy enforcement, ED25519 signature verification, and secrets management.
- **Sandbox Isolation**: Executing unverified external code through AST guards and restricted namespaces.
- **Subsystem Synchronization**: Wiring the EventBus, PolicyEngine, and StateEngine into an integrated, isolated environment.

## Getting Started

### Prerequisites
- Python 3.11+
- Dependencies: `pip install cryptography PyYAML jsonschema pytest`

### Simple Setup
```python
from core.main import KernelBootstrap
import yaml

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

kernel = KernelBootstrap(config)
subsystems = kernel.get_subsystems()
bus = subsystems["bus"]
```

## Bootstrap Integrity

The kernel enforces a strict genesis-to-operation lifecycle to ensure the root of trust is never compromised.

- **Genesis Mode**: Used for initial system birth. The kernel generates a unique 32-byte root keypair (saved to `root_keypair_path`) and registers the initial `kernel_root` identity. Once complete, it automatically flips the configuration to `normal` mode.
- **Normal Mode**: The standard operational state. The kernel verifies the cryptographic integrity of the `AuditLedger` and reconstructs the global state machine from immutable logs before allowing event processing.

## EventBus: The Nervous System

The EventBus is the asynchronous backbone of the kernel, routing strictly typed and ordered actions across all agents and modules.

### Key Features
- **Strict Typing**: All events must match registered JSON schemas in the `SchemaRegistry`.
- **Monotonic Routing**: Ensures events are processed in a deterministic, sequential order.
- **Backpressure Handling**: Protects subscribers from floods using configurable thresholds.
- **Dead-Letter Queue (DLQ)**: Captures failed or unroutable events for later audit and replay.
- **Isolation Layer**: Executes subscriber handlers within memory and timeout constraints to prevent resource exhaustion.

### Interaction Pattern
Agents and modules interact with the EventBus via the `EventBusInterface`:
```python
# Publishing an Event
bus.publish(Event(type="agent.task_completed", payload={"task_id": "...", "status": "success"}))

# Subscribing to an Event
bus.subscribe("agent.task_assigned", my_handler, subscriber_id="agent_123")
```

## Processes for Agents

Autonomous agents are managed via the **Agent Runtime** and **Orchestrator**, which provide a controlled execution environment.

- **Process Isolation**: Agents operate within their own task-specific containers, mediated by the `AgentOrchestrator`.
- **Identity & Delegation**: Every agent is assigned a unique, verifiable identity with scoped capabilities.
- **Working Memory**: Scoped key-value persistence via the `MemoryAdapterInterface` for session state and context.
- **Budgeting & Metering**: Real-time tracking of resource consumption (tokens, time, memory) via the `MeteringInterface`.

## Data, Statistics, and Monitoring

The COE Kernel provides comprehensive observability into system health, agent performance, and resource utilization. Developers can pull real-time metrics and historical audit logs for deep-trace observation.

### Event Bus Observability
- **Subscriber Health**: Track success rates, failure counts, and average execution latency (ms) per agent/subscriber.
- **Resource Pressure**: Monitor memory warnings when a handler exceeds isolated memory bounds.
- **Throughput & Backpressure**: Real-time visibility into the activation depth of backpressure controllers.
- **Reliability (DLQ)**: Access Dead-Letter Queue volumes and error reasons for unroutable events.

### Agent & Resource Metrics
- **Resource Metering**: Pull real-time consumption data (e.g., tokens, compute) per identity via the `MeteringInterface`.
- **Budget Tracking**: Monitor `system.budget_exceeded` events to identify resource-hungry agents.
- **Orchestration State**: Observe active task counts and execution progress across the agent runtime.

### Immutable Traceability
- **Audit Ledger**: A cryptographically-linked log of every kernel mutation, providing 100% traceability of actor actions.
- **State Transitions**: Reconstruct the complete lifecycle of any entity by replaying FSM transitions from the ledger.
- **Integrity Status**: Automated verification of the cryptographic chain to ensure logs have not been tampered with.

## Security & Module Signing

To maintain the zero-trust boundary, the `ModuleLoader` rejects any code that does not pass strict security checks.

### AST Analysis (AST Guards)
Every module is parsed into an Abstract Syntax Tree before execution. The loader blocks access to sensitive Python builtins and modules, including:
- **Prohibited Imports**: `os`, `sys`, `subprocess`, `socket`, `http`, `importlib`.
- **Restricted Builtins**: `eval`, `exec`, `open`, `__import__`.

### Cryptographic Signing
All modules must be cryptographically signed using **ED25519**. The loader expects a `signature.sig` file in the module directory containing a signature of the module's content hash.
```bash
# Modules failing verification will raise kernel.MODULE_SIGNATURE_INVALID
```

## Hot-Swap & ShadowBus Protocol

The kernel supports atomic, zero-downtime updates of logic layers (Modules) via a safe cutover protocol:
1. **Validation**: The new module version is loaded into an isolated sandbox.
2. **ShadowBus**: Subscriptions are mirrored to a "Shadow Bus" instance.
3. **Verification**: The module is verified against live or simulated traffic without affecting the real EventBus.
4. **Cutover**: On success, the registry atomically redirects traffic to the new instance and unloads the legacy code.
5. **Rollback**: Any failure during validation triggers an automatic rollback to the previous version.

## Connecting Modules & Databases

The kernel facilitates the connection of external logic (Modules) and state persistence (Databases/FSMs) through standardized interfaces.

## 🏗️ Layer-by-Layer Instructions & Evidence

The COE Kernel is composed of five critical layers, each enforcing a specific dimension of the system's "Zero Tolerance" security posture.

---

### 1. Kernel Layer (Bootstrap & Audit)
**Role**: Orchestrates the deterministic startup sequence and maintains the immutable "Golden Record" of all system mutations.

#### 🛠️ Instructions
- **Initialization**: Use `KernelBootstrap(config)` to wire subsystems. The order is strictly enforced: `Audit` -> `EventBus` -> `Identity` -> `Policy` -> `Secrets` -> `ModuleLoader` -> `Metering` -> `State`.
- **Mode Switching**: Set `mode: genesis` in `config.yaml` for the first run to generate root keys. Switch to `normal` for production to enable state reconstruction from the ledger.

#### 📄 Documented Evidence: `core/main.py`
The bootstrap sequence (lines 45-81) ensures that the **Audit Ledger** is the first subsystem initialized, binding all subsequent components to its immutability:
```python
# 1. Audit Ledger MUST be first, as all other systems bind to it.
self.audit_ledger = AuditLedger(...)

# 2. Event Bus routing requires Audit...
self.event_bus = self._init_event_bus(config)
```

#### 📄 Documented Evidence: `core/audit/ledger.py`
Cryptographic chaining (lines 75-80) ensures every entry is linked to the previous state:
```python
def append(self, actor_id, action, status, metadata):
    entry_hash = self._hash_payload(f"{self._last_hash}{actor_id}{action}{status}{json.dumps(metadata)}")
    self._last_hash = entry_hash # Immutable chain link
```

---

### 2. Event Bus (Routing, Backpressure & DLQ)
**Role**: The asynchronous nervous system for strictly-typed, ordered messaging.

#### 🛠️ Instructions
- **Schema Validation**: Register all event types in the `SchemaRegistry` with expected fields.
- **Backpressure**: Configure `backpressure_activation_depth` in `config.yaml`. When reached, the bus will block new publications to protect subscribers.
- **DLQ Management**: Failed executions are automatically moved to the Dead-Letter Queue. Use `bus.dlq.replay()` to re-process casualties.

#### 📄 Documented Evidence: `core/event_bus/bus.py`
Mandatory signature verification (lines 78-83) blocks unsigned or tampered events:
```python
def verify_event_signature(event: Event) -> bool:
    if not event.signature or event.signature == "N/A":
        return False
    expected = compute_event_signature(event)
    return event.signature == expected
```

---

### 3. Policy Engine (Capabilities & RBAC)
**Role**: Deterministic evaluation of "Who can do What" across the trust boundary.

#### 🛠️ Instructions
- **Rule Definitions**: Define rules as `capability` or `event_auth` types.
- **Ordering**: Rules are prioritized (lower is higher) and "Deny" always takes precedence over "Allow" at the same priority level.
- **Evaluation**: The kernel calls `policy_engine.evaluate(identity_id, capability, context)` before any sensitive operation.

#### 📄 Documented Evidence: `core/policy/engine.py`
Deterministic rule sorting (lines 31-37) ensures consistent enforcement:
```python
self.rules = sorted(
    raw_rules,
    key=lambda x: (
        x.get("priority", 999),
        0 if x.get("action") == "deny" else 1,
    ),
)
```

---

### 4. Agent Runtime (Isolation & Metering)
**Role**: Lifecycle manager for autonomous agents, providing process isolation and resource capping.

#### 🛠️ Instructions
- **Registration**: Agents must register via `AgentRuntime.register(AgentDefinition)`. This allocates a unique Identity ($G4-01$) and a token budget.
- **Resource Metering**: Monitor `agent.budget_exceeded` events. The runtime uses the `MeteringLayer` to cap token/compute usage in real-time.

#### 📄 Documented Evidence: `core/agent_runtime/runtime.py`
Agent-specific budget allocation (lines 53-55) happens atomically during registration:
```python
# Allocate budget in MeteringLayer
self._metering.allocate(str(identity.id), "ai_tokens", agent_def.token_budget)
```

---

### 5. Secure Lego Module Loader (AST & Signing)
**Role**: Safely loads, validates, and hot-swaps logic layers (Modules).

#### 🛠️ Instructions
- **Signing**: Run `tools/sign_module.py --path <module_path>` before loading.
- **AST Guards**: Ensure your module does not import `os`, `sys`, or `subprocess`. The kernel will reject modules with illegal instructions.
- **Hot-Swap**: Update a module's code and call `loader.load_module(path)`. The kernel uses the **ShadowBus** protocol to verify the new version before cutover.

#### 📄 Documented Evidence: `core/module_loader/loader.py`
The `ModuleEventProxy` (lines 31-54) sanitizes all outgoing events from the module sandbox:
```python
def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
    # Translates and signs events before they hit the real bus
    event = Event(..., origin_id=self._origin_id, payload=payload, ...)
    event = replace(event, signature=compute_event_signature(event))
    self._bus.publish(event)
```

---

### Configuration Reference (`config.yaml`)

| Section | Key | Description |
| :--- | :--- | :--- |
| **bootstrap** | `mode` | `genesis` or `normal` startup mode. |
| **audit** | `storage_path` | Persistent location for the tamper-evident ledger. |
| **events** | `backpressure_activation_depth` | Queue depth at which backpressure starts. |
| **modules** | `forbidden_imports` | List of Python modules blocked by the AST parser. |
| **secrets** | `passphrase_env_var` | Env var containing the vault decryption key. |

### Connectivity & State Persistence

---
*For detailed API specifications, refer to [interfaces.py](core/interfaces.py).*
