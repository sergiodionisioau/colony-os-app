Phase 1 Plan — AI-Native Social Media Module

Module type: Plug-and-play capability module for Colony kernel + event bus + policy engine
Phase objective: Establish the foundation layer only — schema, contracts, orchestration boundaries, safety rails, adapters, canonical post model, approval flow, and deterministic publish pipeline. No uncontrolled autonomy. No platform-specific improvisation. No hidden side effects.

1. Phase 1 Objective

Build a production-safe base module that can plug into the existing kernel, subscribe/publish to the event bus, obey policy engine decisions, and manage a social media workflow through a single canonical control plane.

This phase does not aim to deliver full autonomous growth or full community-management intelligence.
It aims to deliver the operating substrate required for later phases.

Phase 1 must establish
one canonical social content model
one deterministic publish workflow
one approval and policy gate
one adapter contract for channels
one event contract for all module actions
one audit trail for every action
one rollback/failure model
one bounded plug-and-play module package

2. Phase 1 Success Definition

At the end of Phase 1, the module must be able to:

receive a social.post.requested event
validate payload against schema
derive platform variants deterministically
run policy checks
route for approval or auto-approval according to policy
create publish jobs per target channel
send jobs through channel adapters
record all outcomes
emit success/failure events back onto the event bus
expose all actions in a reproducible audit trail

If this is not true, Phase 1 is not complete.

3. Full Prompt for Builder Model / Implementation Team

Use this as the phase execution prompt.

You are building Phase 1 of an AI-native Social Media Module for a modular operating system.

System context:
- Existing infrastructure already includes:
  - kernel
  - event bus
  - policy engine
- This module must be plug-and-play.
- This module must not assume direct ownership of orchestration outside its domain.
- This module must communicate only through explicit APIs, contracts, and events.
- This module must be deterministic, auditable, policy-bound, and reversible where possible.
- This module must not contain hidden side effects, uncontrolled loops, or self-authorized outbound actions.

Primary objective:
Build the foundation layer of a social media module that can:
- accept canonical social post requests
- generate platform variants deterministically
- run policy and approval gates
- publish through adapter interfaces
- track result state
- emit event bus messages
- provide full auditability

Strict baseline:
- zero trust
- zero silent failure
- zero direct posting without policy result
- zero direct posting without audit record
- zero platform-specific logic leaking into core domain
- zero hardcoded channel behavior in orchestration layer
- zero uncontrolled autonomous reply behavior
- zero credential exposure in logs, events, or artifacts
- zero mutation of canonical content after approval without versioning

Required design:
- clear domain model
- clear API contracts
- event schema
- adapter abstraction
- approval workflow
- retry model
- state machine for content and publish jobs
- audit log strategy
- deterministic idempotency strategy
- unit tests
- edge cases
- done criteria

Output required:
1. architecture summary
2. module boundaries
3. domain model
4. event contracts
5. API contracts
6. adapter interface
7. publish state machine
8. approval state machine
9. task breakdown
10. artifacts list
11. test plan
12. edge cases
13. happy path
14. done criteria

Do not skip contracts.
Do not hand-wave integrations.
Do not invent hidden infrastructure.
Prefer explicit schemas and deterministic flow over convenience.
4. Full Spec
4.1 Module name

social_module

4.2 Module purpose

A bounded module that manages:

planned outbound social content
platform variant generation
approval routing
publish execution
publish result tracking
future hooks for replies, reposts, analytics, and optimization
4.3 Module boundary
In scope for Phase 1
canonical post intake
channel target selection
platform variant generation rules
policy engine handshake
approval workflow
publish job creation
outbound adapter execution
result recording
event emission
audit logging
idempotent retries
failure classification
Out of scope for Phase 1
autonomous reply generation and sending
comment triage
sentiment classification
learning loop / self-improvement
analytics scoring engine
community inbox
repost intelligence
campaign optimization
media generation pipeline
direct browser automation for hostile platforms
uncontrolled platform scraping

Phase 1 is foundation only.

5. Core Design Principles
5.1 Canonical-first

All content originates as a canonical post record in your own system.
No platform becomes the source of truth.

5.2 Adapter isolation

Each social platform is an adapter.
The core orchestration layer never embeds platform logic.

5.3 Event-native

Every significant state transition emits a typed event.

5.4 Policy before action

No publish action occurs before a policy outcome exists.

5.5 Approval-aware

No risky content auto-publishes unless explicit policy permits it.

5.6 Immutable auditability

Every decision and external call produces an audit trail.

5.7 Idempotent execution

Same request cannot double-publish accidentally.

5.8 Versioned content

Any edit after approval creates a new version.

6. Logical Architecture
6.1 Components
A. Social Module API

Receives internal requests from kernel or upstream orchestrators.

B. Content Normalizer

Validates and normalizes canonical content.

C. Variant Builder

Produces channel-specific variants from canonical source.

D. Policy Gateway

Sends content for policy evaluation and receives enforcement result.

E. Approval Router

Routes content into:

auto-approved
approval-required
rejected
F. Publish Planner

Creates per-channel publish jobs.

G. Adapter Executor

Calls the appropriate channel adapter.

H. Publish State Tracker

Tracks publish attempts and final status.

I. Audit Logger

Stores event trail, policy results, approval records, adapter calls, failures.

J. Event Emitter

Publishes all module events back to event bus.

7. Data Model
7.1 CanonicalPost

Represents the source-of-truth content unit.

Fields:

id
tenant_id
brand_id
campaign_id nullable
title nullable
canonical_text
media_refs[]
target_channels[]
intent_type
announcement
thought_leadership
campaign
community
support
promotional
risk_level_requested
created_by
created_at
content_version
status
policy_decision_id nullable
approval_record_id nullable
idempotency_key
metadata_json
7.2 PlatformVariant

Derived content for a specific platform.

Fields:

id
canonical_post_id
channel
variant_text
media_refs[]
thread_parts[] nullable
version
generation_rule_id
status
7.3 ApprovalRecord

Fields:

id
canonical_post_id
approval_mode
status
reviewer_id nullable
review_reason
reviewed_at nullable

Statuses:

pending
approved
rejected
expired
7.4 PublishJob

Fields:

id
canonical_post_id
platform_variant_id
channel
scheduled_at nullable
attempt_count
status
last_error_code nullable
last_error_message nullable
external_post_id nullable
published_url nullable
adapter_name
idempotency_key

Statuses:

queued
awaiting_policy
awaiting_approval
ready
dispatching
published
failed_retryable
failed_terminal
cancelled
7.5 PolicyDecision

Fields:

id
subject_type
subject_id
decision
risk_score
rule_hits[]
requires_human_approval
explanation
evaluated_at
7.6 AuditEvent

Fields:

id
aggregate_type
aggregate_id
event_type
payload_json
actor_type
actor_id
occurred_at
correlation_id
8. State Machines
8.1 Canonical Post State Machine

States:

draft
normalized
variants_generated
policy_pending
policy_rejected
approval_pending
approved
publish_planned
publishing
partially_published
published
failed
archived

Transitions:

draft -> normalized
normalized -> variants_generated
variants_generated -> policy_pending
policy_pending -> policy_rejected
policy_pending -> approval_pending
policy_pending -> approved
approval_pending -> approved
approval_pending -> failed
approved -> publish_planned
publish_planned -> publishing
publishing -> partially_published
publishing -> published
publishing -> failed
8.2 Publish Job State Machine

States:

queued
awaiting_policy
awaiting_approval
ready
dispatching
published
failed_retryable
failed_terminal
cancelled

Rules:

never jump from queued to dispatching
never publish without ready
terminal failures cannot retry automatically unless explicitly re-queued
9. Event Bus Contracts
9.1 Inbound Events
social.post.requested

Payload:

canonical_post_id optional
tenant_id
brand_id
canonical_text
media_refs
target_channels
intent_type
requested_schedule optional
created_by
correlation_id
social.post.approval.received

Payload:

canonical_post_id
decision
reviewer_id
review_reason
correlation_id
social.post.retry.requested

Payload:

publish_job_id
reason
actor_id
correlation_id
9.2 Outbound Events
social.post.normalized
social.post.variants.generated
social.post.policy.passed
social.post.policy.rejected
social.post.approval.required
social.post.approved
social.publish.jobs.created
social.publish.dispatched
social.publish.succeeded
social.publish.failed
social.post.partially_published
social.post.completed

All outbound events must include:

tenant_id
brand_id
aggregate_id
correlation_id
timestamp
module_version
10. Internal API Contracts
10.1 Create Canonical Post

POST /social/posts

Request:

canonical_text
media_refs
target_channels
intent_type
metadata

Response:

canonical_post_id
status
10.2 Get Canonical Post

GET /social/posts/{id}

10.3 Submit Approval

POST /social/posts/{id}/approval

10.4 Retry Publish Job

POST /social/publish-jobs/{id}/retry

10.5 List Publish Jobs

GET /social/posts/{id}/publish-jobs

10.6 Health Check

GET /social/health

10.7 Module Capability Descriptor

GET /social/capabilities

Returns:

supported_channels
supported_actions
adapter_health
policy_dependency_status
event_bus_status
module_version
11. Adapter Contract

Each channel adapter must implement the same interface.

11.1 Interface

SocialChannelAdapter

Methods:

validate_variant(variant) -> ValidationResult
publish(variant, publish_context) -> PublishResult
delete(external_post_id) -> DeleteResult optional
healthcheck() -> AdapterHealth
supports(action) -> bool
11.2 PublishResult

Fields:

success
external_post_id
published_url
provider_timestamp
raw_provider_ref
error_code
error_message
retryable
11.3 Adapter rules
no adapter may mutate canonical content
no adapter may bypass policy or approval
no adapter may log secrets
adapters must map provider errors into normalized error classes
12. Supported Phase 1 Channels

Phase 1 should not try to solve every platform at once.

Mandatory adapters for Phase 1
buffer_adapter
bluesky_adapter_stub
mastodon_adapter_stub

Reason:

Buffer acts as early distribution rail
direct adapters are defined early to prevent Buffer lock-in
stubs prove adapter abstraction before deeper implementation
Explicit Phase 1 position on X
X is not a direct Phase 1 adapter unless official paid connector strategy is approved later
X can only be reached through buffer_adapter if Buffer supports the connected profile
no browser automation in Phase 1
no scraping in Phase 1
13. Deterministic Work Flow
Phase 1 happy path flow
upstream system emits social.post.requested
module validates request
canonical post record created
content normalized
platform variants generated
policy engine evaluates
policy passes with either:
auto-approve
approval required
if approval required, wait for explicit approval event
publish planner creates publish jobs
adapter executor dispatches jobs
adapter returns normalized result
publish state updated
audit event stored
outbound event emitted
canonical post marked published or partially_published
14. 0-Tolerance Baseline

This is non-negotiable.

Forbidden conditions
publish without policy result
publish without audit event
publish same idempotency key twice
mutate approved content without version bump
log API tokens, cookies, session IDs, secrets
adapter-specific errors leaking raw credentials
silent retry loops
auto-reply capability hidden inside publish module
fallback to unsupported automation path
posting to wrong tenant or brand context
policy engine timeout treated as approval
approval timeout treated as approval
Required controls
strict schema validation
required tenant isolation
deterministic correlation IDs
idempotency enforcement
explicit retry classification
immutable audit history
versioned content records
explicit adapter capability checks before dispatch
15. Task Breakdown
Task Group A — Module Skeleton
A1

Create package/module structure

A2

Register module with kernel

A3

Implement capability descriptor

A4

Implement health endpoints

Task Group B — Domain Model
B1

Define CanonicalPost schema

B2

Define PlatformVariant schema

B3

Define PublishJob schema

B4

Define ApprovalRecord schema

B5

Define PolicyDecision schema

B6

Define AuditEvent schema

Task Group C — State Machines
C1

Implement canonical post state machine

C2

Implement publish job state machine

C3

Add transition guards

C4

Add invalid transition tests

Task Group D — Event Contracts
D1

Define inbound event schemas

D2

Define outbound event schemas

D3

Implement event serialization

D4

Implement correlation propagation

Task Group E — Policy Handshake
E1

Build policy request mapper

E2

Build policy response validator

E3

Map policy decisions into post/job states

E4

Handle policy timeout and failure states

Task Group F — Approval Flow
F1

Implement approval record store

F2

Implement approval API/event handler

F3

Enforce publish block until approval

F4

Handle reject/expire flows

Task Group G — Variant Generation
G1

Implement channel formatting rules abstraction

G2

Build deterministic variant generator

G3

Support thread split structure placeholder

G4

Add versioning logic

Task Group H — Publish Planning
H1

Create publish jobs per target channel

H2

Add idempotency key per job

H3

Add schedule placeholder support

H4

Add duplicate suppression

Task Group I — Adapter Layer
I1

Define adapter interface

I2

Implement buffer adapter

I3

Implement bluesky stub

I4

Implement mastodon stub

I5

Normalize provider errors

Task Group J — Execution Engine
J1

Implement dispatch orchestrator

J2

Enforce adapter capability checks

J3

Update publish job state from results

J4

Emit outbound result events

Task Group K — Audit Layer
K1

Write audit event service

K2

Attach correlation IDs everywhere

K3

Store raw provider refs safely

K4

Build audit query endpoint

Task Group L — Testing
L1

Schema validation tests

L2

State machine tests

L3

Policy gate tests

L4

Approval gate tests

L5

Idempotency tests

L6

Adapter failure mapping tests

L7

Event emission tests

L8

Tenant isolation tests

16. Subtasks by Build Order
Build order
module skeleton
schemas
state machines
event contracts
policy handshake
approval flow
variant generation
publish planning
adapter interface
buffer adapter
dispatch engine
audit layer
tests
integration smoke pass

This order prevents downstream rework.

17. Required Artifacts
Architecture artifacts
module context diagram
component interaction diagram
publish sequence diagram
state transition diagram
adapter boundary diagram
Specification artifacts
domain schema spec
event contract spec
API contract spec
adapter interface spec
policy handshake spec
approval workflow spec
idempotency spec
audit logging spec
failure classification spec
Code artifacts
module package
schema models
event models
state machine implementation
adapter interface
buffer adapter
stubs
test suite
Operational artifacts
example env file
secret handling doc
runbook
failure recovery runbook
module registration manifest
18. Unit Test Plan
A. Schema Tests
valid canonical post accepted
invalid channel rejected
missing tenant_id rejected
empty canonical_text rejected where required
malformed media refs rejected
B. State Machine Tests
valid state transitions pass
invalid transitions fail
publish blocked before policy pass
publish blocked before approval when required
C. Policy Tests
pass decision routes correctly
reject decision blocks publish
timeout does not publish
malformed policy response fails closed
D. Approval Tests
approval required blocks publish
approval received unlocks publish
rejection cancels jobs
expired approval blocks publish
E. Idempotency Tests
duplicate request with same idempotency key creates no duplicate jobs
duplicate dispatch does not double publish
retry does not override terminal success
F. Adapter Tests
buffer adapter publish success normalized correctly
provider retryable failure maps to failed_retryable
provider terminal failure maps to failed_terminal
unsupported action rejected before dispatch
G. Event Tests
outbound events emitted at each required stage
correlation_id preserved
tenant context preserved
H. Audit Tests
every publish attempt writes audit record
every failure writes audit record
secrets are redacted
19. Edge Cases
Edge Case 1 — Policy engine timeout

Expected:

fail closed
mark post as blocked
emit social.publish.failed
no dispatch occurs
Edge Case 2 — Approval arrives after rejection

Expected:

approval ignored
audit event written
post remains rejected
Edge Case 3 — Duplicate event delivery from event bus

Expected:

idempotency logic suppresses duplicate canonical record or duplicate publish job
no double post occurs
Edge Case 4 — One channel succeeds, one fails

Expected:

canonical post marked partially_published
successful job preserved
failed job retryable or terminal as mapped
Edge Case 5 — Adapter returns success with missing external ID

Expected:

classify as invalid provider response
mark failed_terminal unless adapter contract explicitly allows null external ID
Edge Case 6 — Approved content edited after approval

Expected:

create new content version
invalidate old approval
rerun policy + approval
Edge Case 7 — Wrong tenant credentials bound to adapter

Expected:

adapter dispatch blocked by tenant/brand config validation
audit event written
no outbound publish
20. Happy Path

This defines the exact expected success path.

operator creates canonical post
module validates payload
canonical post stored as version 1
variants generated for target channels
policy engine passes content
content either auto-approves or human approves
publish jobs created
adapter health passes
adapter publishes successfully
publish results normalized and stored
outbound success events emitted
canonical post marked published
audit trail complete and queryable

If any of these 13 steps is missing, happy path is incomplete.

21. Done Criteria

Phase 1 is done only when all conditions below are true.

Functional done
can receive post request
can generate variants
can pass through policy gate
can pause for approval
can create publish jobs
can publish through at least one working adapter
can record outcomes
can emit events
can produce audit trail
Safety done
no publish without policy
no publish without audit
no secrets in logs
duplicate events do not double publish
invalid states blocked
Engineering done
all schemas versioned
all core transitions unit tested
all edge cases covered in tests
adapter contract documented
capability descriptor implemented
failure classes normalized
Operational done
runbook exists
env template exists
module registration documented
dependency health checks implemented
22. Recommended File/Package Layout
social_module/
  api/
    routes.py
    schemas.py
  domain/
    models.py
    enums.py
    state_machines.py
  services/
    normalizer.py
    variant_builder.py
    policy_gateway.py
    approval_router.py
    publish_planner.py
    dispatch_engine.py
    audit_service.py
  adapters/
    base.py
    buffer_adapter.py
    bluesky_stub.py
    mastodon_stub.py
  events/
    inbound.py
    outbound.py
    emitter.py
    handlers.py
  persistence/
    repositories.py
    migrations/
  tests/
    unit/
    integration/
  docs/
    architecture.md
    contracts.md
    runbook.md
23. Build Sequence Recommendation
Sprint 1
module skeleton
schemas
state machines
event contracts
Sprint 2
policy gateway
approval flow
variant builder
publish planner
Sprint 3
adapter interface
buffer adapter
dispatch engine
audit service
Sprint 4
tests
integration pass
hardening
docs
24. Critical Gaps Now Closed

These were the major architectural holes and are now explicitly addressed:

source-of-truth ownership
policy-before-publish enforcement
approval state separation
adapter abstraction
idempotency design
partial publish handling
auditability
tenant isolation
versioned edit model
failure taxonomy
deterministic build order
25. Final Phase 1 Command Intent

Build the plug-and-play substrate, not the fantasy layer.
Do not jump ahead to autonomous replies, analytics optimization, or social growth loops until the module can prove:

deterministic control
safe publish flow
event-native integration
adapter isolation
policy compliance
audit-grade traceability

That is the correct end-to-end Phase 1 plan.