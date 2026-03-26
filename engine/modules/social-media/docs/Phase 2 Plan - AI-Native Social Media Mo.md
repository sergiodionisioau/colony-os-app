Phase 2 Plan — AI-Native Social Media Module

Phase name: Community Control + Unified Inbox + Reply/Repost Execution
Module type: Plug-and-play extension for kernel + event bus + policy engine
Dependency: Phase 1 foundation completed and stable

1. Phase 2 Objective

Build the community interaction layer on top of Phase 1 so the module can:

ingest mentions, comments, replies, repost/reshare signals
normalize them into one canonical inbox
classify and prioritize interactions
draft deterministic reply candidates
gate all outbound interaction through policy + approval
execute supported replies/reposts through adapters
emit full audit trails and event-bus state changes

Phase 2 is where the module moves from outbound publishing only to controlled two-way social operation.

This phase still does not permit uncontrolled autonomy.
It introduces bounded engagement orchestration.

2. Phase 2 Success Definition

At the end of Phase 2, the module must be able to:

ingest inbound interaction data from supported channels
normalize all interactions into one canonical schema
classify each interaction deterministically
score urgency/risk/actionability
create reply or repost action candidates
run policy checks before any outbound interaction
require approval where policy dictates
execute replies/reposts via adapter contracts where supported
track all outcomes and failures
emit complete event and audit trails

If this does not happen end to end, Phase 2 is not complete.

3. Full Prompt for Builder Model / Implementation Team
You are building Phase 2 of an AI-native Social Media Module for a modular operating system.

Existing infrastructure already includes:
- kernel
- event bus
- policy engine
- Phase 1 social publishing substrate:
  - canonical post model
  - platform variants
  - approval flow
  - publish jobs
  - adapter abstraction
  - audit logging
  - outbound event contracts

Primary objective of Phase 2:
Build the community-control layer that ingests inbound social interactions, normalizes them into a unified inbox, classifies them, creates controlled action candidates, routes them through policy and approval gates, and executes supported replies/reposts through adapters.

Strict baseline:
- zero trust
- zero silent outbound interaction
- zero reply without policy result
- zero reply without audit record
- zero autonomous engagement loops
- zero self-authorized escalation into unsupported actions
- zero hidden scraping side effects
- zero direct adapter calls that bypass inbox/action state
- zero credential leakage
- zero cross-tenant contamination
- zero mutation of inbound source records

Required design:
- unified inbox domain model
- interaction normalization contracts
- action candidate model
- reply/repost state machines
- classification pipeline
- risk and priority model
- approval workflow for engagement
- adapter action interface extensions
- polling/webhook ingestion contracts
- idempotent ingestion strategy
- audit strategy
- unit tests
- edge cases
- done criteria

Output required:
1. architecture summary
2. module boundaries
3. domain model
4. event contracts
5. API contracts
6. ingestion pipeline
7. inbox state machine
8. action candidate state machine
9. adapter extensions
10. task breakdown
11. artifacts list
12. test plan
13. edge cases
14. happy path
15. done criteria

Prefer explicit contracts over convenience.
Fail closed.
Do not invent hidden background behavior.
Do not assume all platforms support the same engagement actions.
4. Phase 2 Full Spec
4.1 Phase purpose

Add a unified community operations layer to the social module.

This layer must support:

inbound interaction ingestion
mention/comment/reply/repost normalization
queue management
reply candidate drafting
repost/share candidate drafting
action approval and execution
escalation to human review
future hooks for analytics and learning
4.2 In scope
polling/webhook intake for supported adapters
canonical interaction model
unified inbox
interaction classification
risk routing
priority routing
reply candidate generation
repost/share candidate generation
policy gating for engagement
approval gating for engagement
action execution for supported platforms
audit logging
event contracts
idempotent interaction ingest
thread linkage to canonical post where available
4.3 Out of scope
DMs/private messaging
autonomous sentiment warfare / growth hacking
bot swarm behavior
mass follow/unfollow strategies
community analytics optimization
self-tuning model prompts
fully autonomous crisis management
scraping-led hostile automation for restricted platforms
voice/video reply generation
deep lead qualification workflows
cross-platform identity resolution beyond deterministic references
5. Core Design Principles
5.1 Inbox-first

No reply/repost action occurs directly from adapter output.
Everything must pass through the canonical inbox.

5.2 Source immutability

Inbound records are immutable.
Derived classification and action candidates are separate records.

5.3 Action candidates, not instant actions

AI may propose actions.
It does not directly execute them unless policy allows.

5.4 Platform asymmetry respected

Not all platforms support:

replies
quote/repost
delete
edit
thread continuation

The system must encode this explicitly.

5.5 Deterministic classification

Initial classification must use explicit rules and bounded model outputs, not freeform drift.

5.6 Fail closed

If ingestion, classification, policy, or approval fails:

no outbound action occurs
5.7 Human override

Sensitive categories must always support manual review.

6. Logical Architecture
6.1 New components in Phase 2
A. Interaction Ingestion Gateway

Receives inbound interactions from polling jobs or webhook receivers.

B. Interaction Normalizer

Maps platform-specific payloads into canonical interaction records.

C. Unified Inbox Service

Stores, indexes, and exposes normalized interactions.

D. Classifier Engine

Assigns:

interaction type
intent
risk
urgency
recommended handling class
E. Action Candidate Builder

Creates:

reply candidate
repost candidate
ignore candidate
escalate candidate
F. Engagement Policy Gateway

Runs policy checks on proposed outbound interaction.

G. Engagement Approval Router

Handles approval for risky or high-value interactions.

H. Engagement Executor

Dispatches approved replies/reposts through adapters.

I. Thread/Context Resolver

Links interactions to:

canonical post
external post reference
prior thread history
brand account context
J. Inbox Event Emitter

Emits lifecycle events for every inbox and action state change.

7. Domain Model
7.1 SocialInteraction

Canonical immutable record of an inbound item.

Fields:

id
tenant_id
brand_id
channel
interaction_type
mention
reply
comment
repost
quote
reaction
unknown
external_interaction_id
external_post_id
external_parent_id nullable
author_handle
author_display_name nullable
author_platform_id nullable
body_text
media_refs[]
provider_timestamp
ingested_at
raw_payload_ref
canonical_post_id nullable
thread_key nullable
dedupe_key
status

Statuses:

ingested
normalized
classified
actioned
archived
failed
7.2 InteractionClassification

Fields:

id
interaction_id
intent_class
praise
complaint
support_request
lead_signal
spam
abuse
question
neutral
unknown
risk_class
low
medium
high
critical
priority_class
low
normal
high
urgent
recommended_action
ignore
reply
repost
escalate
manual_review
confidence_score
rule_hits[]
classified_at
classifier_version
7.3 InboxItem

Operational queue wrapper for interaction handling.

Fields:

id
interaction_id
tenant_id
brand_id
queue_status
assigned_to nullable
sla_due_at nullable
sort_score
last_transition_at

Queue statuses:

new
triaged
awaiting_policy
awaiting_approval
ready
executing
completed
ignored
escalated
failed
7.4 ActionCandidate

Derived outbound action proposal.

Fields:

id
interaction_id
canonical_post_id nullable
action_type
reply
repost
quote_repost
ignore
escalate
proposed_text nullable
proposed_media_refs[]
target_channel
target_external_parent_id
status
generation_mode
content_version
policy_decision_id nullable
approval_record_id nullable
idempotency_key
created_at

Statuses:

drafted
policy_pending
policy_rejected
approval_pending
approved
ready
dispatching
succeeded
failed_retryable
failed_terminal
cancelled
7.5 EngagementExecution

Tracks outbound community action result.

Fields:

id
action_candidate_id
adapter_name
attempt_count
external_result_id nullable
published_url nullable
error_code nullable
error_message nullable
retryable
executed_at nullable
8. State Machines
8.1 Interaction State Machine
ingested
normalized
classified
actioned
archived
failed

Valid transitions:

ingested -> normalized
normalized -> classified
classified -> actioned
classified -> archived
* -> failed
8.2 InboxItem State Machine
new
triaged
awaiting_policy
awaiting_approval
ready
executing
completed
ignored
escalated
failed

Rules:

cannot jump from new to executing
cannot execute without candidate
cannot enter ready without successful policy decision
cannot leave awaiting_approval without explicit approval or rejection
8.3 ActionCandidate State Machine
drafted
policy_pending
policy_rejected
approval_pending
approved
ready
dispatching
succeeded
failed_retryable
failed_terminal
cancelled

Rules:

draft must exist before policy
no dispatch without ready
approval invalidated on content mutation
terminal success cannot be retried as a new send without explicit regenerate/requeue
9. Supported Action Classes in Phase 2
Mandatory
reply
ignore
escalate
Conditional
repost
quote_repost
Not supported in Phase 2
bulk reply campaigns
DM outreach
thread hijack behavior
mass amplification loops
auto-follow or engagement farming
10. Adapter Extensions

Phase 1 adapter contract must be extended.

10.1 Extended interface

CommunityCapableSocialAdapter

Methods:

fetch_interactions(fetch_context) -> InteractionBatchResult
normalize_incoming(raw_item) -> NormalizedInteraction
publish_reply(action_candidate, context) -> ExecutionResult
publish_repost(action_candidate, context) -> ExecutionResult
supports_inbox() -> bool
supports_reply() -> bool
supports_repost() -> bool
supports_quote_repost() -> bool
10.2 Rules
adapters must declare support explicitly
unsupported actions must fail before dispatch planning
fetched raw records must be stored safely by reference, not dumped into logs
provider timestamps must be preserved
10.3 Phase 2 mandatory adapters
buffer_adapter extended only where Buffer-supported workflows make sense
bluesky_adapter minimal direct inbox/reply support if available in your stack
mastodon_adapter minimal direct inbox/reply support if available in your stack
10.4 Explicit X position in Phase 2
direct X control remains out of scope unless official connector strategy is later approved
X-origin interactions may only be handled through a supported intermediary rail if available
no scraping-based core dependency
no browser automation in baseline Phase 2
11. Ingestion Strategy
11.1 Intake modes

Two supported mechanisms:

adapter polling
webhook receiver

Each interaction must be normalized into the same canonical schema.

11.2 Idempotency

Every interaction must have:

provider identity
dedupe key
tenant scope
brand scope

Duplicate delivery must not duplicate inbox items or action candidates.

11.3 Thread resolution

Where possible, interactions should be linked to:

external post
canonical post
earlier thread context
prior handled action candidate

If deterministic linkage is not possible, mark as unlinked.

12. Classification Model

Phase 2 classification must be deterministic and bounded.

12.1 Required outputs
intent class
risk class
priority class
recommended action
confidence score
rule hits
12.2 Initial method

Use:

strict rules first
bounded classifier second
fallback unknown classes if confidence insufficient
12.3 Examples
spam keywords -> ignore
abuse/toxicity -> escalate
direct product question -> reply
positive endorsement -> ignore or repost candidate depending policy
complaint with legal indicators -> manual_review / escalate
13. Event Bus Contracts
13.1 Inbound events
social.interactions.fetch.requested

Payload:

tenant_id
brand_id
channels[]
correlation_id
social.interaction.ingest.requested

Payload:

tenant_id
brand_id
channel
raw_payload_ref
correlation_id
social.action.approval.received

Payload:

action_candidate_id
decision
reviewer_id
reason
correlation_id
social.action.retry.requested

Payload:

action_candidate_id
actor_id
reason
correlation_id
13.2 Outbound events
social.interaction.ingested
social.interaction.normalized
social.interaction.classified
social.inbox.item.created
social.action.candidate.created
social.action.policy.passed
social.action.policy.rejected
social.action.approval.required
social.action.approved
social.action.dispatch.started
social.action.dispatch.succeeded
social.action.dispatch.failed
social.inbox.item.escalated
social.inbox.item.completed

All must include:

tenant_id
brand_id
aggregate_id
correlation_id
timestamp
module_version
14. Internal API Contracts
14.1 Fetch interactions

POST /social/inbox/fetch

14.2 List inbox items

GET /social/inbox

Filters:

status
channel
risk_class
priority_class
intent_class
14.3 Get inbox item

GET /social/inbox/{id}

14.4 Get interaction

GET /social/interactions/{id}

14.5 Create action candidate manually

POST /social/inbox/{id}/actions

14.6 Approve action

POST /social/actions/{id}/approval

14.7 Retry action

POST /social/actions/{id}/retry

14.8 Ignore inbox item

POST /social/inbox/{id}/ignore

14.9 Escalate inbox item

POST /social/inbox/{id}/escalate

14.10 Capability endpoint

GET /social/community/capabilities

Returns:

supported_inbox_channels
supported_actions_by_channel
policy_dependency_status
adapter_health
ingestion_modes
module_version
15. Deterministic Workflow
15.1 Happy path flow
system requests interaction fetch
adapter fetches raw interactions
raw items normalized into canonical SocialInteraction
interaction classified
inbox item created
action candidate generated
policy evaluates proposed action
if low-risk and allowed, action becomes ready
if required, explicit approval received
engagement executor dispatches through supported adapter
result normalized and stored
inbox item completed
full audit trail written
outbound events emitted
16. 0-Tolerance Baseline
Forbidden
direct reply from raw adapter event
direct repost from classifier output
execute without policy decision
execute without audit record
unsupported adapter action silently downgraded to another action
auto-reply loops between bots/accounts
replying to same interaction twice from duplicate delivery
mutation of source interaction text
approval timeout treated as approval
policy timeout treated as approval
secret leakage in raw payload or logs
cross-tenant reply routing
quote/repost on channels that do not support it
speculative thread linkage presented as truth
Required controls
strict schema validation
dedupe on inbound interactions
idempotent action generation
policy-before-execution enforcement
approval invalidation on action text edits
anti-loop detection
channel capability enforcement
immutable raw payload references
tenant/brand credential validation before dispatch
17. Task Breakdown
Task Group A — Inbox Domain
A1

Define SocialInteraction schema

A2

Define InteractionClassification schema

A3

Define InboxItem schema

A4

Define ActionCandidate schema

A5

Define EngagementExecution schema

Task Group B — Ingestion Pipeline
B1

Implement polling intake contract

B2

Implement webhook intake contract

B3

Implement raw payload reference storage

B4

Implement dedupe strategy

B5

Implement thread/context linker

Task Group C — Classification
C1

Define deterministic rule library

C2

Implement bounded classifier interface

C3

Implement confidence threshold logic

C4

Implement recommended action mapper

C5

Implement fallback unknown handling

Task Group D — Inbox Workflow
D1

Implement inbox state machine

D2

Implement triage service

D3

Implement assign/ignore/escalate flows

D4

Implement SLA/sort scoring

Task Group E — Action Candidates
E1

Implement reply candidate builder

E2

Implement repost candidate builder

E3

Implement ignore/escalate candidate pathways

E4

Implement content versioning and edit invalidation

Task Group F — Policy + Approval
F1

Integrate engagement policy request mapper

F2

Validate engagement policy responses

F3

Implement approval record for actions

F4

Block execution until policy + approval satisfied

Task Group G — Adapter Extensions
G1

Extend base adapter contracts

G2

Implement inbox fetch for supported adapters

G3

Implement reply execution methods

G4

Implement repost execution methods where supported

G5

Normalize execution errors

Task Group H — Execution Engine
H1

Implement engagement dispatch orchestrator

H2

Add capability checks per action/channel

H3

Track execution attempts and outcomes

H4

Implement retry classification

Task Group I — Events + Audit
I1

Define inbox/action event schemas

I2

Implement event handlers and emitters

I3

Extend audit log coverage

I4

Attach correlation IDs end to end

Task Group J — APIs + Ops
J1

Implement inbox APIs

J2

Implement action approval/retry APIs

J3

Implement capability endpoint

J4

Update runbook and recovery procedures

Task Group K — Testing
K1

Schema tests

K2

Ingestion dedupe tests

K3

Classification tests

K4

State machine tests

K5

Policy/approval tests

K6

Adapter capability tests

K7

Execution tests

K8

Tenant isolation tests

K9

Anti-loop tests

18. Subtasks by Build Order
domain schemas
ingestion contracts
state machines
classification rules
inbox service
action candidate builder
policy/approval flow
adapter extensions
execution engine
events + audit
APIs
tests
integration hardening
19. Required Artifacts
Architecture artifacts
unified inbox context diagram
ingestion sequence diagram
reply execution sequence diagram
inbox state machine diagram
action candidate state diagram
adapter capability matrix
Specification artifacts
interaction schema spec
inbox schema spec
classification spec
action candidate spec
engagement policy contract
adapter engagement extension spec
dedupe/idempotency spec
anti-loop spec
escalation policy spec
Code artifacts
inbox domain models
ingestion services
classifier
action candidate services
adapter extensions
engagement executor
event handlers
audit extensions
test suite
Operational artifacts
env template updates
polling/webhook configuration guide
moderation runbook
failure recovery runbook
escalation handling playbook
20. Unit Test Plan
A. Schema tests
valid interaction accepted
missing tenant rejected
unsupported interaction type rejected
malformed external IDs rejected
invalid action type rejected
B. Ingestion tests
duplicate raw interaction does not create duplicate inbox item
duplicate webhook delivery dedupes correctly
missing parent reference handled safely
unknown provider payload fails closed
C. Classification tests
spam classified as ignore
abuse classified as escalate
product question classified as reply
praise does not auto-reply unless rule permits
low-confidence classification falls back to manual or unknown
D. State machine tests
inbox valid transitions pass
invalid transitions fail
action cannot dispatch before ready
edited candidate invalidates approval
E. Policy and approval tests
policy pass enables ready state
policy reject blocks dispatch
approval required blocks dispatch
approval rejection cancels action
F. Adapter tests
unsupported reply action blocked before execution
retryable failure maps correctly
terminal failure maps correctly
successful reply stores external result id
G. Anti-loop tests
self-authored interaction ignored
bot-to-bot loop candidate blocked
same interaction cannot generate duplicate sent reply
H. Tenant isolation tests
wrong tenant credentials blocked
cross-brand interaction cannot produce outbound action
raw payload references isolated correctly
I. Audit tests
every classification writes audit record
every dispatch writes audit record
secrets redacted from raw payload storage references
21. Edge Cases
Edge Case 1 — Duplicate webhook delivered 5 times

Expected:

one interaction record
one inbox item
no duplicate reply candidate
audit records show dedupe outcome
Edge Case 2 — Interaction from own brand account

Expected:

marked self-originated
ignored or archived by anti-loop policy
no reply candidate created
Edge Case 3 — Policy engine timeout on reply

Expected:

fail closed
candidate remains blocked
no dispatch occurs
audit + failure event emitted
Edge Case 4 — Action approved, then candidate edited

Expected:

approval invalidated
version bumped
policy rerun required
execution blocked until new approval path completes
Edge Case 5 — Adapter claims reply supported but returns unsupported error

Expected:

capability mismatch logged
job marked failed_terminal or configuration error
adapter health degraded
Edge Case 6 — One inbox item generates multiple possible actions

Expected:

one primary executable candidate unless policy explicitly allows more
alternatives stored as non-executed proposals
no parallel conflicting actions
Edge Case 7 — External thread linkage ambiguous

Expected:

mark unlinked/ambiguous
do not invent conversation history
require conservative handling
Edge Case 8 — Abuse or legal threat

Expected:

escalate
no auto-reply
critical priority
audit event and alert event emitted
22. Happy Path
supported adapter fetches a new mention
interaction normalized and stored
classifier marks it as question, low risk, high priority
inbox item created and triaged
reply candidate drafted
policy passes reply
approval not required under low-risk rules
action candidate marked ready
adapter publishes reply successfully
execution recorded
inbox item completed
outbound success event emitted
audit trail fully queryable
23. Done Criteria
Functional done
can ingest interactions from at least one supported channel
can normalize into unified inbox
can classify interactions deterministically
can create reply candidate
can policy-gate outbound engagement
can approval-gate when required
can execute at least one reply action through one working adapter
can ignore/escalate safely
can emit events and audit results
Safety done
no direct outbound engagement from raw inbound payload
no auto-send without policy
no duplicate replies from duplicate deliveries
no secrets in logs
anti-loop protection active
invalid/unsupported actions blocked
Engineering done
schemas versioned
state machines enforced
adapter engagement interface documented
all core paths unit tested
edge cases covered
failure taxonomy normalized
Operational done
moderation runbook exists
webhook/polling config documented
escalation path documented
failure recovery documented
capability endpoint operational
24. Recommended Package Additions
social_module/
  community/
    ingestion/
      polling.py
      webhooks.py
      normalizer.py
      dedupe.py
    domain/
      interaction_models.py
      inbox_models.py
      action_models.py
      state_machines.py
    services/
      classifier.py
      triage.py
      candidate_builder.py
      thread_resolver.py
      engagement_policy_gateway.py
      engagement_executor.py
    api/
      inbox_routes.py
      action_routes.py
    tests/
      unit/
        test_ingestion.py
        test_classifier.py
        test_inbox_state_machine.py
        test_action_candidates.py
        test_anti_loop.py
25. Build Sequence Recommendation
Sprint 1
schemas
state machines
ingestion contracts
dedupe design
Sprint 2
classifier
inbox service
action candidate builder
Sprint 3
policy + approval integration
adapter extensions
engagement executor
Sprint 4
APIs
audit/event expansion
tests
hardening
26. Critical Gaps Closed in Phase 2

Phase 1 left these major capabilities intentionally open. Phase 2 closes them:

unified inbox architecture
immutable inbound interaction records
deterministic classification model
reply/repost candidate abstraction
anti-loop controls
engagement approval pathway
adapter inbox/reply extensions
thread/context linkage
duplicate ingress suppression
conservative escalation logic
27. Final Phase 2 Command Intent

Build controlled two-way engagement, not autonomous social chaos.

Phase 2 is complete only when the module can safely:

listen
classify
propose
gate
execute
audit

without ever bypassing:

kernel boundaries
event bus contracts
policy engine decisions
approval controls
tenant isolation

That is the correct end-to-end Phase 2 plan for a plug-and-play social media module.