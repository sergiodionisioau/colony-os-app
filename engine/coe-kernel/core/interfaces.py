"""Abstract Base Classes defining the explicit contract boundaries for the COE Kernel.

All core subsystems MUST implement these interfaces to guarantee isolated,
deterministic, and interchangeable architectures under the Zero Tolerance Baseline.
"""

import abc
from typing import Any, Dict, Iterator, List, Optional
import uuid

from core.types import AuditEntry, DelegationToken, Event, Identity, PolicyDecision
from core.agent.types import (
    AgentTaskSpec,
    AgentTaskResult,
    AIResponse,
    AIMessage,
    ProviderConfig,
    AgentDefinition,
    Patch,
    CIResult,
)


class AuditLedgerInterface(abc.ABC):
    """Tamper-evident log managing cryptographic trust across the kernel."""

    @abc.abstractmethod
    def append(
        self, actor_id: str, action: str, status: str, metadata: Dict[str, Any]
    ) -> AuditEntry:
        """Appends a new immutable record to the ledger."""

    @abc.abstractmethod
    def verify_integrity(self) -> bool:
        """Validates the cryptographic hash chain of the entire ledger."""

    @abc.abstractmethod
    def iterate(self, action: Optional[str] = None) -> Iterator[AuditEntry]:
        """Provides an ordered iterator over the ledger entries."""


class IdentityServiceInterface(abc.ABC):
    """Manages role-based registration and delegation."""

    @abc.abstractmethod
    def register_agent(
        self, name: str, role: str, parent_id: str, signing_key: bytes
    ) -> Identity:
        """Registers a delegated identity attached to a parent."""

    @abc.abstractmethod
    def register_identity(
        self,
        name: str,
        role: str,
        parent_id: Optional[str],
        identity_type: str,
        *args: Any,
        **kwargs: Any,
    ) -> Identity:
        """Registers an identity without parental constraints (Bootstrap/Root)."""

    @abc.abstractmethod
    def get_identity(self, identity_id: str) -> Identity:
        """Retrieves an identity by its UUID string."""

    @abc.abstractmethod
    def suspend_identity(self, identity_id: str, actor_id: str) -> None:
        """Suspends an identity."""

    @abc.abstractmethod
    def reinstate_identity(self, identity_id: str, actor_id: str) -> None:
        """Re-activates a suspended identity."""

    @abc.abstractmethod
    def revoke_identity(self, identity_id: str, actor_id: str) -> None:
        """Revokes an identity."""

    @abc.abstractmethod
    def get_role_capabilities(self, role: str) -> List[str]:
        """Role capability bindings."""

    @abc.abstractmethod
    def create_delegation(
        self,
        delegator_id: uuid.UUID,
        delegate_id: uuid.UUID,
        scope: list[str],
        ttl_seconds: int,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Creates a delegation token."""

    @abc.abstractmethod
    def verify_delegation(self, token: DelegationToken) -> bool:
        """Verifies if a delegation token is valid."""

    @abc.abstractmethod
    def revoke_delegation(self, token_id: uuid.UUID) -> None:
        """Revokes a delegation token."""


class PolicyEngineInterface(abc.ABC):
    """Determines binary authorization strictly off deterministic rulesets."""

    @abc.abstractmethod
    def evaluate(
        self,
        identity_id: str,
        capability: str,
        context: Dict[str, Any],
        dry_run: bool = False,
    ) -> PolicyDecision:
        """Evaluates an explicit allow/deny outcome."""

    @abc.abstractmethod
    def load_rules(self, raw_rules: List[Dict[str, Any]]) -> None:
        """Loads and compiles rule definitions deterministically."""


class SecretsVaultInterface(abc.ABC):
    """Manages encrypted at-rest variables (e.g., API keys)."""

    @abc.abstractmethod
    def store_secret(
        self, identity_id: str, key: str, value: str, ttl: Optional[int] = None
    ) -> None:
        """Encrypts and stores a string variable payload."""

    @abc.abstractmethod
    def retrieve_secret(self, identity_id: str, key: str) -> str:
        """Retrieves and decrypts a variable payload if authorized."""

    @abc.abstractmethod
    def rotate_secret(self, module_id: uuid.UUID, key: str, new_value: bytes) -> None:
        """Atomically replaces a secret value, wiping the old value."""

    @abc.abstractmethod
    def revoke_secret(self, module_id: uuid.UUID, key: str) -> None:
        """Revokes access to a secret without deleting it entirely from history."""


class EventBusInterface(abc.ABC):
    """Nervous system routing strictly typed and ordered actions."""

    @abc.abstractmethod
    def publish(self, event: Event) -> None:
        """Routes a single versioned event via monotonic execution."""

    @abc.abstractmethod
    def subscribe(
        self,
        event_type: str,
        handler: Any,
        subscriber_id: str = "",
    ) -> None:
        """Registers a synchronous handler for an event scope."""

    @abc.abstractmethod
    def unsubscribe(self, subscriber_id: str, event_type: str) -> None:
        """Removes a subscriber for a specific event type."""

    @abc.abstractmethod
    def replay_events(
        self, start_sequence: int, end_sequence: int, replay_id: str
    ) -> None:
        """Replays historical events idempotently through the subscriber graph."""

    @abc.abstractmethod
    def get_dlq_metrics(self) -> Dict[str, Any]:
        """Provides visibility into Dead-Letter Queue volumes and thresholds."""


class MeteringInterface(abc.ABC):
    """Enforces rigid resource constraints natively in-memory."""

    @abc.abstractmethod
    def allocate(self, identity_id: str, metric: str, amount: int) -> None:
        """Assigns an absolute token allocation for a specific identity."""

    @abc.abstractmethod
    def consume(self, identity_id: str, metric: str, amount: int) -> bool:
        """Removes allocation tokens explicitly denying if exceeding limits."""

    @abc.abstractmethod
    def record(self, identity_id: uuid.UUID, metric: str, value: float) -> None:
        """Records metric consumption and evaluates thresholds against policy."""

    @abc.abstractmethod
    def get_usage(self, identity_id: uuid.UUID) -> Dict[str, float]:
        """Provides visibility into metric usage across an identity."""


class StateEngineInterface(abc.ABC):
    """Finite state machine tracker for deterministic step processing."""

    @abc.abstractmethod
    def register_fsm(
        self, name: str, version: str, transitions: List[Dict[str, Any]]
    ) -> None:
        """Registers strict path rules for a workflow."""

    @abc.abstractmethod
    def transition(
        self, fsm_name: str, entity_id: str, event_type: str, identity_id: str
    ) -> str:
        """Applies an explicit mutation verifying pathing rules,
        returning new state.
        """

    @abc.abstractmethod
    def set_active_state(self, entity_id: str, state: str) -> None:
        """Manually overrides the active state for an entity (System/Maintenance)."""

    @abc.abstractmethod
    def get_active_state(self, fsm_name: str, entity_id: str) -> str:
        """Returns the current active state for an entity in an FSM."""

    @abc.abstractmethod
    def rebuild_from_audit(self) -> None:
        """Replays all state_transition audit entries to reconstruct state."""


class ModuleLoaderInterface(abc.ABC):
    """Sandboxing gatekeeper loading unverified external code via AST guards."""

    @abc.abstractmethod
    def load(self, module_name: str) -> None:
        """AST scans and executes an isolated module layer."""

    @abc.abstractmethod
    def unload(self, module_name: str) -> None:
        """Safely removes an invoked module from RAM."""

    @abc.abstractmethod
    def rollback(self, module_name: str) -> None:
        """Rolls back to the previous module version on load failure."""

    @abc.abstractmethod
    def get_loaded_modules(self) -> List[str]:
        """Returns the list of currently loaded module names."""


class ModuleInterface(abc.ABC):
    """Interface that loadable modules should implement for lifecycle."""

    @abc.abstractmethod
    def initialize(self, kernel_context: Any) -> None:
        """Initializes the module with the kernel context."""

    @abc.abstractmethod
    def healthcheck(self) -> Any:  # Returns HealthStatus eventually
        """Evaluates module internal status."""

    @abc.abstractmethod
    def shutdown(self) -> None:
        """Safely shuts down module internals."""


class AIProviderInterface(abc.ABC):
    """Stateless LLM adapter. MUST NOT store state between calls."""

    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        history: List[AIMessage],
        config: ProviderConfig,
    ) -> AIResponse:
        """Calls the provider. History is passed explicitly on every call."""

    @abc.abstractmethod
    def provider_id(self) -> str:
        """Stable identifier string for this provider e.g. 'openai_gpt4'."""


class MemoryAdapterInterface(abc.ABC):
    """Scoped key-value store for agent working memory."""

    @abc.abstractmethod
    def store(self, key: str, value: Any, scope_id: uuid.UUID) -> None:
        """Stores a value in memory associated with a specific scope."""

    @abc.abstractmethod
    def retrieve(self, key: str, scope_id: uuid.UUID) -> Optional[Any]:
        """Retrieves a value from memory for a specific scope."""

    @abc.abstractmethod
    def clear(self, scope_id: uuid.UUID) -> None:
        """Clears all memory associated with a specific scope."""


class AgentOrchestratorInterface(abc.ABC):
    """Finite-step execution controller for agent task processing."""

    @abc.abstractmethod
    def execute(self, task: AgentTaskSpec) -> AgentTaskResult:
        """Runs the agent task. Returns result regardless of outcome. Never raises."""

    @abc.abstractmethod
    def get_active_tasks(self) -> List[uuid.UUID]:
        """Returns task_ids of currently executing tasks."""


class AgentRuntimeInterface(abc.ABC):
    """Lifecycle manager for agent registration and task dispatch."""

    @abc.abstractmethod
    def register(self, agent_def: AgentDefinition) -> Identity:
        """Creates identity, allocates budget. Emits agent.registered."""

    @abc.abstractmethod
    def unregister(self, agent_id: str) -> None:
        """Revokes identity, clears budget. Emits agent.unregistered."""

    @abc.abstractmethod
    def execute(self, task: AgentTaskSpec) -> AgentTaskResult:
        """Delegates to Orchestrator. Wraps all exceptions — never panics."""


class ImprovementEngineInterface(abc.ABC):
    """Bounded self-improvement controller. Kernel paths are immutable."""

    @abc.abstractmethod
    def propose_patch(self, patch: Patch) -> None:
        """Validates scope, emits improvement.patch_proposed."""

    @abc.abstractmethod
    def approve_patch(self, patch_id: uuid.UUID, approver_id: str) -> None:
        """Runs CI, hot-swaps module on pass, emits patch_applied or patch_rejected."""

    @abc.abstractmethod
    def reject_patch(self, patch_id: uuid.UUID, reason: str) -> None:
        """Emits improvement.patch_rejected. Audits reason."""


class CIGateInterface(abc.ABC):
    """Contract for local or remote CI test execution."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Reports if the CI execution environment is ready."""

    @abc.abstractmethod
    def run_tests(self, patch: Patch) -> CIResult:
        """Executes patch.test_vector in a subprocess sandbox. Returns CIResult."""
