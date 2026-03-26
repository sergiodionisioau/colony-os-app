# CRM Module - Autonomous Revenue OS

The **CRM Module** is a standalone logic layer designed to orchestrate autonomous revenue-generating operations. It serves as an specialized agentic system that harvests signals, maps relationships, and executes optimized outreach strategies through a deterministic decision engine.

## Critical Features

### 1. Revenue Knowledge Graph (R-KG)
The **R-KG** is the persistent memory of the CRM module. It maps raw signals (web interactions, API events) to verified entities (accounts, stakeholders), enabling high-fidelity relationship mapping and context-aware decisions.

### 2. Autonomous Agents
The CRM Module utilizes a multi-agent architecture where specialized units handle distinct parts of the revenue cycle. 
- **Prospecting Agent**: Specialized in signal "harvesting" and discovery. It actively monitors external streams to identify high-intent interactions.
- **Deal Strategy Agent**: Maps account hierarchies and identifies the "path to power" within an organization, proposing specific tactics like "Influencer Outreach."

### 3. Agent Layer: How, What, Where
- **Where**: Agent strategies are defined as isolated Python classes within `modules/crm/agents/`.
- **What**: Every agent is an "Identity" within the Kernel. Upon registration, it is allocated a **Metering Budget** (tokens/compute) and a **Capability Policy** (defining strictly what it can access: e.g., `db_read` but not `bus_publish`).
- **How**: The `AgentOrchestrator` (`orchestrator.py`) instantiates these agents and manages their execution cycles, ensuring that context from the Knowledge Graph is correctly injected into their decision-making logic.

### 4. Decision Engine
The **Decision Engine** performs automated **Intent Scoring** by aggregating signals from the R-KG. It applies a confidence-weighted heuristic to determine if an entity has crossed the threshold for proactive outreach.

### 4. Pipeline Controller
Manages the lifecycle of **Revenue Pipelines**. Once a decision is triggered, the controller instantiates a persistent workflow that tracks the progress of the outreach strategy until a terminal state (Closed/Won, Closed/Lost) is reached.

## Data, Analytics, and Prediction Modeling

The CRM Module provides a rich data layer for monitoring revenue health and agent performance. Users and external systems can query the **R-KG** and observe the **Decision Engine's** predictive outputs.

### 1. Revenue Datasets
- **Signal History**: Temporal stream of intent indicators (Web visits, Content consumption) tagged with confidence scores.
- **Buying Committee Maps**: Automated identification of decision-makers and influencers within target entities.
- **Relationship Strength**: Quantified metrics of stakeholder-to-entity bonds based on interaction frequency.

### 2. Predictive Modeling & Statistics
- **Intent Scoring**: A predictive metric (0.0 - 1.0) forecasting the likelihood of an entity entering a "Buying Window."
- **ICP Scoring**: Organizational fit score based on firmographic data (Industry, Size, Tech stack).
- **Conversion Probability**: Statistically derived from historical pipeline completion rates (Completed vs. Rejected).

### 3. How to Pull Data
- **Event-Driven Observation**: Subscribe to the kernel eventspublished by this module:
    - `revenue.signal.detected`: Raw input stream.
    - `revenue.pipeline.created`: Predictive trigger output.
    - `revenue.outcome.closed`: Terminal state for analytics.
- **Interactive Dashboard**: The Next.js UI provides visual representations of the R-KG and real-time intent score charts.
- **Audit Trails**: Every pipeline maintains an immutable `audit_trail` accessible via the `PipelineController` state, recording every agent action and manual approval.

## Entry Points & Lifecycle

The CRM module integrates with the **COE Kernel** via specific lifecycle hooks:

- **`entry.py`**: The primary entry point.
    - `initialize(bus)`: Connects the module to the kernel's EventBus.
    - `handle_event(event)`: The main ingress for kernel events (e.g., `revenue.signal.detected`).
- **`manifest.json`**: Defines the module's identity, permissions (`db_read`, `bus_publish`), and event subscriptions.

## Step-by-Step Guide: Signal to Pipeline

The module follows a deterministic "Signal-to-Decision" loop:

1.  **Signal Detection**: A `revenue.signal.detected` event is published to the Kernel EventBus.
2.  **R-KG Harvesting**: The `Module.handle_event` hook captures the event and adds it to the **Knowledge Graph**.
3.  **Intent Scoring**: The `DecisionEngine` computes a real-time intent score based on signal confidence and frequency.
4.  **Decision Generation**: If the score exceeds a threshold (e.g., > 0.7), the engine generates a `PROPOSER_OUTREACH` decision.
5.  **Strategy Proposal**: The `DealStrategyAgent` proposes an optimized tactic based on the entity's position in the graph.
6.  **Pipeline Activation**: The `PipelineController` creates a new execution thread to track the opportunity.

## Developer Installation Guide

Adding a new agent to the Autonomous Revenue OS requires a specific sequence to maintain kernel-level security and observability.

### Step 1: Define the Agent Strategy
Create a new file in `modules/crm/agents/` (e.g., `retention_agent.py`):
```python
class RetentionAgent:
    def __init__(self, capability_policy: dict):
        self.policy = capability_policy

    def analyze_churn_risk(self, context: dict):
        # Implementation logic here
        return {"risk": "LOW", "confidence": 0.8}
```

### Step 2: Register in Orchestrator
Add your agent to the `AgentOrchestrator.__init__` in `modules/crm/agents/orchestrator.py`:
```python
from modules.crm.agents.retention_agent import RetentionAgent

# ... inside __init__
self.agents["retention"] = RetentionAgent(capability_policy={"db_read": True})
```

### Step 3: Update Capabilities (Optional)
If your agent requires new kernel-level permissions, update the `manifest.json` in the module root to include the necessary scopes (e.g., `EXTERNAL_API_ACCESS`).

### Step 4: Cryptographic Sealing (Critical)
The Kernel will reject any modified module without a valid signature. You **MUST** re-sign the CRM module after adding your agent:
```powershell
python modules/crm/sign_module.py
```
This updates the `signature.sig` file, allowing the `ModuleLoader` to verify your changes.

### Step 5: Verification
1. Restart the Kernel (or trigger a Module Hot-Swap).
2. Observe the `agent.registered` event on the EventBus.
3. Check the CRM Dashboard to see your new agent appearing in the Decision Loop.

## UI & Observation

The CRM module is paired with a specialized **Next.js Dashboard**.
- **Real-Time Monitoring**: Observe the `Decision Loop` as it processes signals.
- **HITL Verification**: High-priority decisions (e.g., `PROPOSER_OUTREACH`) can be routed to the Human-In-The-Loop terminal for final approval.
- **Signal Visualization**: View R-KG relationship maps and entity health scores.

---
*For development details, see [manifest.json](manifest.json) or explore [agents/](agents/).*
