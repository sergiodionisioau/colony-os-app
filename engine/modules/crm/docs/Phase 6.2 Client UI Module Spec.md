# Specification: CRM Client UI Module (Phase 6.2)

The **CRM Client UI Module** is the professional interaction layer for the Autonomous Revenue OS. It transforms raw agent telemetry and Knowledge Graph data into high-fidelity visualizations, predictive dashboards, and a deterministic Command Command Center for Human-In-The-Loop (HITL) oversight.

## 1. Core Value Proposition
When a user "buys" this module, they receive:
- **Absolute Transparency**: Real-time visibility into why agents are making decisions.
- **Predictive Edge**: Statistical modeling of prospect intent, deal velocity, and funnel conversion.
- **Full Lifecycle Visibility**: Real-time tracking of the client journey from first signal to advocate.
- **Sovereign Control**: A hard-gate for all revenue-impacting actions.
- **SaaS Transition Bridge**: Protocols for migrating data from Monday, Hubspot, and Mailchimp into a unified R-KG.
- **Agent Orchestration Transparency**: Deep-dive into how agents are organizing and executing tasks.
- **Immutable Trust**: Direct integration with the Kernel Audit Ledger for 100% auditability.

---

## 2. Functional Specification (The View Layer)

### A. The Executive Command Center (Dashboard)
- **Signal Velocity Hub**: A "Heat Map" of incoming signals (WEB, API, CONTENT) across all entities.
- **Revenue Funnels (Waterfall View)**: 
    - **Traditional Funnel**: Prospect -> Lead -> SQL -> Customer.
    - **Agentic Funnel**: Signals -> Staged Pipelines -> Approved Actions -> Revenue.
- **Pipeline Health Dashboard**: 
    - **Total Pipeline Value (TPV)**: Aggregated opportunity value of all staged/approved pipelines.
    - **Sales Velocity**: Average time from "Signal Detected" to "Pipeline Completed."
    - **Win/Loss Prediction**: Bayesian probability scoring for individual deals.
- **Agent Orchestration Topology**: 
    - **Orchestra View**: Visual graph showing the `AgentOrchestrator` dispatching specialized tasks to the `Prospector` and `Strategist`.
    - **Capability Gauges**: Real-time display of agent resource consumption (tokens/compute) vs. allocated budget.
- **Global Kill-Switch**: Emergency pause for all autonomous operations.

### B. Revenue Knowledge Graph (R-KG) & Lifecycle Visualizer
- **Relational Force Graph**: Interactive 2D/3D force-directed graphs showing stakeholder-to-entity bonds.
- **Client Lifecycle Journey**: A temporal timeline showing the *complete history* of a client—from the first marketing signal to current deal status.
- **Buying Committee Identification**: Visual clusters highlighting Decision Makers vs. Influencers based on interaction frequency (Data Points #1, #2, #3).
- **Entity Health Scores**: Color-coded nodes reflecting `intent_score` and `icp_score`.

### C. HITL Verification Hub (The Gatekeeper)
- **Pending Action Queue**: List of `STAGED` pipelines awaiting user review.
- **"Trust Verified" Badge**: Interactive element that, when clicked, displays:
    - **ShadowBus Report**: Proof of code integrity and AST isolation.
    - **Heuristic Explanation**: Plain-English rationale for the current outreach strategy.
- **Control Interface**: Buttons for `Approve`, `Reject`, and `Tune Strategy`.

### D. The Audit Ledger Explorer (The Black Box)
- **Historical Replay**: Chronological timeline of every event for a specific account.
- **Accountability Logs**: Every human approval is anchored to a User ID and timestamp.
- **Golden Record Verification**: Comparative view proving the UI matches the Immutable Ledger in the Kernel.

### E. The SaaS Ingress Bridge (Data Migration)
- **Monday/Hubspot/Mailchimp Adapters**: Pre-built connectors that ingest legacy "Leads" and "Contacts" and transform them into **Entities** and **Identities** in the R-KG.
- **Mapping Logic**: Automated AST scanners that identify custom fields in legacy CRMs and map them to Revenue OS capabilities (e.g., mapping Hubspot "Lifecycle Stage" to R-KG `intent_score` heuristics).

### F. The Agentic Workbench (Human-Machine Collaboration)
- **"The Co-Pilot's Chair"**: A visual workspace where a human and an agent co-edit a strategy (e.g., a salesperson adjusting a prospecting strategy in real-time).
- **Proactive Signal Ingestion**: Instead of waiting for reports, the Workbench shows "Live Threads" where agents are actively harvesting data, allowing the human to "nudge" the agent toward specific targets.
- **Confidence Calibration**: A visual slider for users to define "Automation Thresholds" (e.g., "Auto-approve if Confidence > 0.9, but STAGE if Churn Risk is detected").

---

## 3. Future-Forward Analytics (2026-2028 Trends)

As we move toward the 2026-2028 window, the data points to several critical shifts in CRM requirements:

### A. Autonomous Context Synthesis
- **Generative Insights**: Users no longer "filter" data; they query the R-KG via natural language (e.g., *"Show me all Fintech accounts with a hiring spike in DevRel"*).
- **Synthesis Engine**: Agents summarize thousands of signals into a single "Account Vibe" score, anticipating churn before traditional metrics flag it.

### B. Hyper-Personalization at Scale
- **Signal-to-Content Loop**: The UI previews agent-generated content (emails, social posts) that is hyper-personalized based on R-KG relationship data, awaiting HITL approval.

### C. Self-Healing Data Infrastructure
- **Autonomous Enrichment**: Agents actively clean and repair CRM data (e.g., updating roles via LinkedIn signals) without human intervention, maintaining a "Cleanliness Score" in the UI.

### D. Ethical AI & Absolute Transparency
- **Decision "Black Box" Opening**: Clients will demand not just "what" the AI decided, but a "Traceable Rationale" showing the exact data points and weights used—directly integrated with the Audit Ledger.

## 4. Metrics & Prediction Modeling
1. **Engagement Delta**: Tracking the rate of change in an entity's `intent_score` over 7 days.
2. **Churn Risk Analysis**: Sentiment analysis of interaction logs (calls/emails) to flag at-risk accounts (Data Point #10).
3. **CLV Projection**: Projected Customer Lifetime Value based on entity industry and historical purchase history (Data Point #8).

---

## 4. Deterministic Implementation Plan (The Roadmap)

### Phase 1: Data Bridge (Weeks 1-2)
- [ ] Implement `EventBus` listeners for UI telemetry.
- [ ] Create GraphQL/REST wrappers for `KnowledgeGraph.get_buying_committee()` and `PipelineController.get_staged_pipelines()`.
- [ ] Connect the `AuditLedger` stream to the UI backend.

### Phase 2: Visualization Layer (Weeks 3-4)
- [ ] Build the Glassmorphic Command Center using Next.js/React.
- [ ] Integrate D3.js or Sigma.js for R-KG relationship mapping.
- [ ] Develop the "Pulse" visualization for real-time signal velocity.

### Phase 3: HITL & Governance (Weeks 5-6)
- [ ] Implement the `STAGED` action review workflow.
- [ ] Build the "Trust Verified" modal with ShadowBus report parsing.
- [ ] Add the Agent Kill-Switch and Policy Tuning inputs.

### Phase 4: Statistical Modeling (Weeks 7-8)
- [ ] Integrate the predictive heuristic engine for CLV and Churn Risk.
- [ ] Build the forecasting dashboard (Pipeline Velocity graphs).

---

## 5. Strict Baseline for Review

- **Zerohallucination Policy**: No data point in the UI can exist without a corresponding entry in the Kernel Audit Ledger.
- **Hard-Link Verification**: Every "Trust Verified" badge must point to a specific, signed `ShadowBus` validation event ID.
- **Absolute Latency Gate**: Command Center metrics must update within <500ms of an EventBus publication.
