Phase 3 Plan — AI-Native Social Media Module

Phase name: Autonomous Campaign Engine + Analytics + Optimization Loop
Module type: Plug-and-play autonomous social media module for kernel + event bus + policy engine
Dependencies: Phase 1 and Phase 2 complete, stable, and audited

1. Phase 3 Objective

Build the autonomous operating layer of the social media module.

Phase 3 upgrades the system from:

Phase 1: controlled outbound publishing
Phase 2: controlled two-way engagement

to:

autonomous campaign planning
autonomous content generation
autonomous scheduling
autonomous experimentation
autonomous engagement optimization
bounded self-improvement
closed-loop learning from outcomes

But this autonomy is not unconstrained.
It must remain:

policy-bound
auditable
reversible
rate-limited
tenant-isolated
brand-safe
kill-switchable
Phase 3 must establish
campaign planning engine
content pipeline orchestration
scheduling intelligence
analytics ingestion + normalization
performance scoring
experiment engine
learning/memory layer for social performance
bounded autonomous decision loop
clear human override and emergency stop paths

This phase is where the module becomes AI-native, but still governed.

2. Phase 3 Success Definition

At the end of Phase 3, the module must be able to:

generate a campaign plan from defined goals and constraints
produce a structured content calendar
autonomously generate post candidates and engagement candidates
score and prioritize them using policy + strategy rules
schedule and publish within allowed bounds
ingest analytics and engagement outcomes
evaluate what performed well or poorly
update future content decisions based on measured outcomes
run bounded experiments without violating policy
stop safely when risk, drift, or anomalies are detected

If it cannot complete this loop deterministically and safely, Phase 3 is not complete.

3. Full Prompt for Builder Model / Implementation Team
You are building Phase 3 of an AI-native Social Media Module for a modular operating system.

Existing infrastructure already includes:
- kernel
- event bus
- policy engine
- Phase 1 publishing foundation
- Phase 2 unified inbox and community-control layer

Primary objective:
Build the autonomous campaign and optimization layer that can:
- plan campaigns from defined objectives
- generate content plans and content candidates
- schedule content autonomously within policy bounds
- ingest analytics and engagement outcomes
- score content performance
- run bounded experiments
- improve future content decisions through a governed feedback loop

Strict baseline:
- zero uncontrolled autonomy
- zero publish without policy result
- zero outbound action without audit trail
- zero hidden self-modification
- zero self-expansion of permissions
- zero direct optimization that bypasses brand/policy constraints
- zero cross-tenant contamination
- zero mutation of historical performance records
- zero learning updates without versioning
- zero autonomous crisis response without escalation policy
- zero silent drift in prompts, templates, or decision rules

Required design:
- campaign domain model
- content calendar model
- analytics model
- experiment model
- memory/learning model
- autonomous decision loop
- bounded optimization strategy
- scheduling engine
- performance scoring model
- rollback and kill-switch design
- event contracts
- API contracts
- unit tests
- edge cases
- done criteria

Output required:
1. architecture summary
2. module boundaries
3. domain model
4. campaign workflow
5. analytics workflow
6. learning workflow
7. experiment workflow
8. autonomous decision state machine
9. event contracts
10. API contracts
11. task breakdown
12. artifacts list
13. test plan
14. edge cases
15. happy path
16. done criteria

Prefer explicit governance over convenience.
Fail closed.
Do not invent hidden background magic.
Autonomy must remain bounded and inspectable.
4. Phase 3 Full Spec
4.1 Phase purpose

Transform the social module into an autonomous but governed social operating system.

This means the module can:

plan content against business goals
create and manage campaigns
learn from outcomes
adapt posting behavior
improve content structure and timing
optimize within declared policies
4.2 In scope
campaign planning
content calendar generation
post idea generation
content candidate scoring
schedule optimization
analytics ingestion
engagement metric normalization
performance attribution
experiment creation and tracking
learning memory updates
bounded optimization rules
automatic content retries only where policy allows
drift detection
autonomous execution windows
module kill switch / pause controls
4.3 Out of scope
fully autonomous brand repositioning
unsupervised political/legal/cultural crisis responses
manipulative botnet tactics
deceptive persona farming
fake engagement generation
shadow accounts
mass coordinated amplification outside approved assets
unsandboxed prompt rewriting of its own governance core
unbounded model self-improvement
real-money ad-buying autonomy in this phase
5. Core Design Principles
5.1 Objective-bound autonomy

The system may act only toward declared campaign goals.

5.2 Memory is versioned

Learned rules, preferences, and performance conclusions are stored as versioned records.

5.3 Experiments are bounded

No experiment may exceed a configured traffic or content-risk budget.

5.4 Strategy over instinct

All autonomous actions must trace back to:

campaign objective
policy decision
learned rule
experiment plan
or human-defined strategy
5.5 Optimization never overrides policy

Performance gains never justify violating brand, compliance, or trust constraints.

5.6 Safe degradation

If analytics, learning, or scheduling fails, the module falls back to controlled/manual-safe mode.

5.7 Explainable autonomy

Every autonomous decision must be explainable through stored rationale and event history.

6. Logical Architecture
6.1 New Phase 3 components
A. Campaign Planner

Builds campaign plans from business objectives, target audience, themes, and constraints.

B. Content Calendar Engine

Creates a structured posting calendar with priorities, slots, and channel allocations.

C. Content Strategy Generator

Produces content ideas, formats, hooks, and CTA variants from campaign goals.

D. Scoring Engine

Scores candidates based on:

policy fit
brand fit
novelty
strategic relevance
learned historical performance
channel suitability
E. Scheduler Optimizer

Assigns publish windows based on:

channel rules
rate limits
historical performance
campaign urgency
queue health
F. Analytics Ingestion Service

Collects post-level and campaign-level metrics from supported adapters.

G. Metrics Normalizer

Normalizes engagement data into canonical metrics.

H. Performance Evaluator

Determines content performance and campaign effectiveness.

I. Experiment Manager

Creates, tracks, limits, and evaluates structured A/B/n experiments.

J. Learning Memory Service

Stores durable learnings:

winning hooks
bad-performing patterns
audience preferences
channel timing patterns
CTA effectiveness
K. Autonomous Decision Controller

Runs the bounded decision loop:
plan → generate → score → schedule → publish → measure → learn → adapt

L. Safety Governor / Kill Switch

Pauses autonomy on anomaly, drift, policy breach, or operator command.

7. Domain Model
7.1 CampaignPlan

Fields:

id
tenant_id
brand_id
name
objective_type
awareness
engagement
lead_gen
thought_leadership
launch
retention
goal_statement
target_audience
approved_channels[]
start_date
end_date
content_pillars[]
cta_library[]
constraints_json
risk_budget
experiment_budget
status
version
created_by
created_at

Statuses:

draft
approved
active
paused
completed
archived
cancelled
7.2 ContentCalendar

Fields:

id
campaign_plan_id
calendar_window_start
calendar_window_end
generation_version
status
created_at
7.3 CalendarSlot

Fields:

id
content_calendar_id
channel
slot_time
slot_type
post
thread
repost
reply_window
experiment_slot
priority
status
assigned_candidate_id nullable
7.4 ContentCandidate

Fields:

id
campaign_plan_id
calendar_slot_id nullable
candidate_type
post
thread
repost
quote
reply_template
canonical_draft
target_channels[]
hook_type
cta_type
theme
novelty_score
strategy_score
brand_score
performance_prior_score
final_score
status
generation_version
policy_decision_id nullable
approval_record_id nullable

Statuses:

drafted
scored
rejected
approval_pending
approved
scheduled
published
expired
archived
7.5 MetricSnapshot

Fields:

id
tenant_id
brand_id
channel
canonical_post_id
external_post_id
captured_at
impressions
likes
comments
replies
reposts
shares
clicks
profile_visits
follower_delta
saves
raw_payload_ref
7.6 PerformanceEvaluation

Fields:

id
canonical_post_id
campaign_plan_id nullable
evaluation_window
engagement_rate
normalized_score
outcome_class
poor
below_expected
expected
outperformer
anomaly
explanations[]
evaluated_at
evaluator_version
7.7 Experiment

Fields:

id
campaign_plan_id
experiment_type
hook_test
timing_test
channel_test
cta_test
format_test
hypothesis
variant_a_candidate_id
variant_b_candidate_id
variant_n_ids[]
traffic_budget
risk_budget
status
winner_candidate_id nullable
result_summary nullable
created_at

Statuses:

drafted
approved
running
completed
cancelled
invalidated
7.8 LearningRule

Fields:

id
tenant_id
brand_id
rule_type
timing_preference
hook_preference
cta_preference
format_preference
channel_preference
risk_constraint
scope
rule_statement
evidence_refs[]
confidence_score
valid_from
valid_to nullable
status
version

Statuses:

proposed
active
deprecated
rejected
7.9 AutonomousRun

Fields:

id
tenant_id
brand_id
campaign_plan_id nullable
run_type
planning
generation
scoring
scheduling
analytics
learning_update
experiment_eval
status
started_at
ended_at nullable
result_summary
policy_summary
anomaly_flags[]

Statuses:

started
completed
failed
blocked
cancelled
8. State Machines
8.1 CampaignPlan State Machine
draft
approved
active
paused
completed
archived
cancelled

Valid transitions:

draft -> approved
approved -> active
active -> paused
paused -> active
active -> completed
* -> cancelled
completed -> archived
8.2 ContentCandidate State Machine
drafted
scored
rejected
approval_pending
approved
scheduled
published
expired
archived

Rules:

no scheduling before policy/approval complete
no publish from rejected
any edit after approval invalidates approval and resets state
8.3 Experiment State Machine
drafted
approved
running
completed
cancelled
invalidated

Rules:

cannot run without explicit experiment budget
cannot exceed budget/risk thresholds
anomaly can invalidate running experiment
8.4 Autonomous Decision Loop State Machine
idle
planning
generating
scoring
gating
scheduling
executing
measuring
learning
paused
blocked
failed

Rules:

cannot enter executing without gated approved artifacts
cannot enter learning without valid metric inputs
blocked state requires human or policy reset
paused state preserves state but halts outbound autonomy
9. Workflows
9.1 Campaign workflow
business goal submitted
campaign plan drafted
constraints applied
plan reviewed/approved
content calendar generated
content candidates generated
candidates scored
approved candidates scheduled
publishing executed
metrics collected
campaign evaluated
learning rules proposed/applied
9.2 Analytics workflow
metric fetch requested
adapters return raw metric payloads
metrics normalized
metric snapshots stored
evaluations generated
anomalies checked
results published to event bus
learning engine consumes evaluations
9.3 Learning workflow
performance evaluations aggregated
evidence threshold checked
new learning rule proposed
policy/strategy validation performed
rule activated or rejected
future scoring/scheduling updated via versioned rule
9.4 Experiment workflow
experiment hypothesis created
variants generated
risk/traffic budget validated
experiment approved
slots assigned
variants executed
performance measured
winner selected or invalidated
learning rule candidate emitted
10. Event Bus Contracts
10.1 Inbound events
social.campaign.create.requested

Payload:

tenant_id
brand_id
objective_type
goal_statement
target_audience
approved_channels[]
start_date
end_date
content_pillars[]
constraints_json
correlation_id
social.calendar.generate.requested

Payload:

campaign_plan_id
window_start
window_end
correlation_id
social.content.generate.requested

Payload:

campaign_plan_id
slot_ids[]
correlation_id
social.analytics.fetch.requested

Payload:

tenant_id
brand_id
channel_filters[]
post_refs[]
correlation_id
social.autonomy.pause.requested

Payload:

tenant_id
brand_id
reason
actor_id
correlation_id
social.autonomy.resume.requested

Payload:

tenant_id
brand_id
actor_id
correlation_id
10.2 Outbound events
social.campaign.created
social.campaign.approved
social.campaign.activated
social.calendar.generated
social.content.candidates.generated
social.content.candidates.scored
social.content.candidates.approval.required
social.content.candidates.approved
social.schedule.generated
social.analytics.snapshots.ingested
social.performance.evaluated
social.experiment.created
social.experiment.completed
social.learning.rule.proposed
social.learning.rule.activated
social.autonomy.paused
social.autonomy.blocked
social.autonomy.resumed
social.anomaly.detected

All must include:

tenant_id
brand_id
aggregate_id
correlation_id
timestamp
module_version
11. Internal API Contracts
11.1 Create campaign

POST /social/campaigns

11.2 Get campaign

GET /social/campaigns/{id}

11.3 Approve campaign

POST /social/campaigns/{id}/approve

11.4 Generate calendar

POST /social/campaigns/{id}/calendar/generate

11.5 Generate candidates

POST /social/campaigns/{id}/candidates/generate

11.6 List candidates

GET /social/campaigns/{id}/candidates

11.7 Approve candidate

POST /social/candidates/{id}/approve

11.8 Generate schedule

POST /social/campaigns/{id}/schedule/generate

11.9 Fetch analytics

POST /social/analytics/fetch

11.10 List evaluations

GET /social/evaluations

11.11 Create experiment

POST /social/experiments

11.12 Pause autonomy

POST /social/autonomy/pause

11.13 Resume autonomy

POST /social/autonomy/resume

11.14 Capabilities endpoint

GET /social/autonomy/capabilities

Returns:

autonomous_features_enabled
supported_channels
supported_metrics_by_channel
experiment_types_enabled
autonomy_status
safety_governor_status
module_version
12. Deterministic Plan
Build order
campaign domain
content calendar domain
content candidate engine
scoring model
scheduler optimizer
analytics ingestion + normalization
performance evaluation engine
experiment manager
learning memory service
autonomous controller
safety governor
API + event integration
test suite
integration hardening

This build order ensures:

strategy before optimization
measurement before learning
governance before autonomy
13. 0-Tolerance Baseline
Forbidden conditions
autonomous publish without policy result
autonomous publish without audit record
learning rule activation without versioning
self-rewriting of policy constraints
self-expansion into unsupported channels
silent prompt/template drift
metric ingestion treated as valid without schema checks
anomaly ignored while autonomy continues
experiments running beyond budget
optimization choosing policy-disallowed content
analytics gaps treated as proof of success
cross-campaign contamination of learning without scope controls
using engagement spikes alone as truth without context
autonomous crisis escalation without human path
multiple competing autonomous runs mutating same campaign state without lock control
Required controls
campaign-scoped locks
scheduler conflict detection
experiment budget enforcement
learning rule versioning
anomaly detection thresholds
kill switch
pause/resume control
safe fallback mode
confidence thresholds for learning updates
explicit approval requirements by risk class
audit logs for every autonomous run
14. Task Breakdown
Task Group A — Campaign Domain
A1

Define CampaignPlan schema

A2

Define campaign constraints model

A3

Define campaign state machine

A4

Implement campaign approval flow

Task Group B — Content Calendar
B1

Define ContentCalendar schema

B2

Define CalendarSlot schema

B3

Implement slot allocation rules

B4

Implement channel/time constraint enforcement

Task Group C — Content Candidate Engine
C1

Define ContentCandidate schema

C2

Build candidate generation service

C3

Implement channel-format variation logic

C4

Implement content versioning/reset rules

Task Group D — Scoring Engine
D1

Define scoring feature set

D2

Implement novelty scoring

D3

Implement strategy relevance scoring

D4

Implement brand-fit scoring

D5

Implement historical performance prior scoring

D6

Implement final weighted score calculation

Task Group E — Scheduler Optimizer
E1

Implement slot assignment engine

E2

Implement publish window optimizer

E3

Implement queue conflict detection

E4

Implement schedule freeze/lock rules

Task Group F — Analytics Layer
F1

Define MetricSnapshot schema

F2

Implement adapter metric-fetch extension

F3

Implement raw metric normalization

F4

Implement metric retention/versioning

Task Group G — Performance Evaluation
G1

Define PerformanceEvaluation schema

G2

Implement normalized score formula

G3

Implement baseline/expected-performance comparison

G4

Implement anomaly classification

Task Group H — Experiment Manager
H1

Define Experiment schema

H2

Implement experiment approval and budget rules

H3

Implement variant assignment

H4

Implement winner selection logic

H5

Implement invalidation logic

Task Group I — Learning Memory
I1

Define LearningRule schema

I2

Implement evidence aggregation

I3

Implement confidence thresholding

I4

Implement activation/deprecation logic

I5

Implement scoped rule application

Task Group J — Autonomous Controller
J1

Define AutonomousRun schema

J2

Implement autonomous decision loop

J3

Implement run locks and concurrency controls

J4

Implement state recovery on interruption

Task Group K — Safety Governor
K1

Implement pause/resume controls

K2

Implement kill switch

K3

Implement anomaly thresholds

K4

Implement fallback-to-manual-safe mode

K5

Implement blocked-state recovery path

Task Group L — Events and APIs
L1

Define Phase 3 event schemas

L2

Implement campaign/calendar/candidate APIs

L3

Implement analytics/evaluation APIs

L4

Implement autonomy control APIs

L5

Implement capability endpoint

Task Group M — Testing
M1

Campaign tests

M2

Calendar tests

M3

Candidate scoring tests

M4

Scheduler tests

M5

Analytics normalization tests

M6

Evaluation tests

M7

Experiment tests

M8

Learning rule tests

M9

Autonomy safety tests

M10

Tenant isolation tests

15. Subtasks by Build Sequence
Sequence 1 — Strategic substrate
campaign plan schema
calendar schema
candidate schema
core states
Sequence 2 — Decision engines
candidate generation
scoring
scheduling
Sequence 3 — Measurement substrate
analytics ingestion
normalization
evaluation
Sequence 4 — Adaptive intelligence
experiments
learning rules
scoped optimization
Sequence 5 — Autonomy control
autonomous loop
run locks
safety governor
pause/kill
Sequence 6 — Surface and hardening
APIs
events
docs
tests
integration pass
16. Required Artifacts
Architecture artifacts
phase 3 system diagram
campaign lifecycle diagram
autonomous decision loop diagram
analytics pipeline diagram
experiment lifecycle diagram
safety governor decision diagram
Specification artifacts
campaign schema spec
calendar schema spec
candidate scoring spec
schedule optimization spec
analytics normalization spec
performance evaluation spec
experiment governance spec
learning rule spec
autonomy governor spec
anomaly detection spec
Code artifacts
campaign services
candidate services
scoring engine
scheduler
analytics services
evaluation engine
experiment manager
learning service
autonomy controller
safety governor
tests
Operational artifacts
autonomy runbook
pause/kill recovery runbook
experiment approval runbook
anomaly response playbook
module capability manifest
environment template updates
17. Unit Test Plan
A. Campaign tests
valid campaign created
invalid date range rejected
unapproved campaign cannot activate
paused campaign cannot schedule new autonomous actions
B. Calendar tests
slots generated within approved window
disallowed channel excluded
duplicate slot conflict blocked
schedule freeze prevents reassignment
C. Candidate tests
candidate generated with correct campaign linkage
edit invalidates approval
rejected candidate cannot be scheduled
unsupported channel candidate blocked
D. Scoring tests
weighting formula deterministic
novelty score penalizes near-duplicate content
historical prior applied only within scope
missing features handled safely
E. Scheduler tests
best slot chosen within constraints
conflicting jobs blocked
rate limits respected
paused autonomy stops scheduling
F. Analytics tests
raw metrics normalized correctly
missing fields fail safely
duplicate snapshots deduped correctly
invalid provider payload rejected
G. Evaluation tests
normalized score computed correctly
anomaly flagged when metric spike exceeds threshold
below-expected outcome classified correctly
sparse data handled conservatively
H. Experiment tests
experiment cannot run without budget
winner chosen only with valid evidence
anomaly invalidates experiment
cancelled experiment does not emit learning activation
I. Learning rule tests
insufficient evidence cannot activate rule
version bump occurs on rule update
deprecated rule no longer influences scoring
cross-brand leakage blocked
J. Autonomous controller tests
run transitions valid
blocked state halts execution
interrupted run can recover safely
duplicate concurrent run blocked by lock
K. Safety tests
kill switch halts outbound actions
pause preserves state without execution
policy timeout blocks autonomy
anomaly triggers blocked or paused state
18. Edge Cases
Edge Case 1 — Analytics API returns partial data

Expected:

partial snapshot marked incomplete
no aggressive learning update
evaluation downgraded in confidence
audit event written
Edge Case 2 — One post goes viral due to controversy

Expected:

anomaly detection flags outlier
not automatically treated as a winning template
policy/brand review required before rule activation
Edge Case 3 — Learning engine proposes harmful but high-performing pattern

Expected:

policy/brand constraints reject activation
rule stored as rejected
no future scoring benefit applied
Edge Case 4 — Calendar generated during paused autonomy

Expected:

planning may continue if policy allows
no scheduling/execution occurs
run state remains paused for outbound actions
Edge Case 5 — Two autonomous runs target same campaign

Expected:

campaign lock prevents concurrent mutation
second run blocked or queued
no duplicate schedules or candidate clashes
Edge Case 6 — Experiment winner has low sample size

Expected:

no automatic winner activation
result marked inconclusive
no learning rule activated
Edge Case 7 — Metric spike caused by platform bug

Expected:

anomaly flagged
evaluation confidence reduced
learning activation blocked pending validation
Edge Case 8 — Candidate approved, then learning rule changes

Expected:

already-approved candidate remains version-stable unless explicit re-score policy exists
no silent mutation to scheduled content
Edge Case 9 — Scheduler chooses slot beyond campaign window

Expected:

validation failure
no schedule created
audit event emitted
Edge Case 10 — Safety governor kill switch triggered mid-run

Expected:

in-flight run moves to cancelled or blocked safely
no new outbound action begins
full audit trail preserved
19. Happy Path
operator creates and approves campaign
campaign activated
calendar generated for approved channels and dates
content candidates generated for slots
candidates scored using strategy + historical priors
policy passes and approval completes where needed
scheduler assigns candidates to slots
Phase 1 publishing pipeline executes posts
Phase 2 inbox layer receives engagement
analytics snapshots ingested
performance evaluator scores results
experiment manager identifies tested variants
learning service proposes one valid improvement rule
rule approved and activated
next candidate batch uses updated scoring inputs
autonomy continues safely with full traceability
20. Done Criteria
Functional done
campaign can be created, approved, and activated
calendar can be generated deterministically
content candidates can be generated and scored
scheduler can assign publish windows
analytics can be ingested and normalized
performance can be evaluated
experiments can run within budget
learning rules can be proposed and activated version-safely
autonomous controller can run full loop
safety governor can pause/block/kill autonomy
Safety done
no autonomous publish without policy
no autonomous run without audit
no learning activation without evidence threshold
no anomaly ignored during active autonomy
no concurrent campaign mutation without lock
no cross-tenant or cross-brand learning leakage
no self-modifying governance core
Engineering done
all core schemas versioned
all state machines implemented
all scoring formulas documented
all experiment budgets enforced
all learning rules versioned
all core paths unit tested
all edge cases covered in tests
Operational done
autonomy runbook exists
anomaly response playbook exists
kill-switch procedure exists
experiment approval procedure exists
metric ingestion dependencies documented
capability endpoint operational
21. Full Workflow to Build
Step 1 — Lock phase boundaries

Freeze scope:

autonomy yes
uncontrolled self-evolution no
campaign optimization yes
unbounded social manipulation no
Step 2 — Build strategy substrate

Implement:

campaign model
calendar model
candidate model
states and locks
Step 3 — Build generation and scoring

Implement:

content strategy generation
candidate generation
feature extraction
weighted scoring
approval reset rules
Step 4 — Build scheduling

Implement:

slot assignment
conflict control
publish window optimization
freeze rules
Step 5 — Build analytics and evaluation

Implement:

metric fetch
snapshot store
normalization
performance evaluation
anomaly flags
Step 6 — Build experiments

Implement:

experiment creation
budget enforcement
winner logic
invalidation logic
Step 7 — Build learning memory

Implement:

evidence aggregation
rule proposal
activation/deprecation
scoped application
Step 8 — Build autonomous controller

Implement:

full loop state machine
concurrency controls
recovery
tracing
Step 9 — Build safety governor

Implement:

pause
resume
kill
fallback safe mode
anomaly blocking
Step 10 — Integrate with Phase 1 and Phase 2

Ensure:

Phase 1 handles publishing
Phase 2 handles community input
Phase 3 only orchestrates bounded autonomy on top
Step 11 — Hardening

Run:

unit tests
integration tests
failure injection tests
anomaly simulation
recovery drills
22. Critical Gaps Filled

These are the major gaps that Phase 3 closes beyond Phase 2:

campaign-level objective planning
structured content calendar generation
scoring engine for autonomous prioritization
analytics normalization layer
performance evaluation model
experiment governance
learning memory with scoped rule activation
autonomous decision loop
anomaly detection
kill-switch and pause architecture
23. Recommended Package Additions
social_module/
  autonomy/
    domain/
      campaign_models.py
      calendar_models.py
      candidate_models.py
      experiment_models.py
      learning_models.py
      autonomous_run_models.py
      state_machines.py
    services/
      campaign_planner.py
      calendar_engine.py
      candidate_generator.py
      scoring_engine.py
      scheduler_optimizer.py
      analytics_ingestor.py
      metrics_normalizer.py
      performance_evaluator.py
      experiment_manager.py
      learning_service.py
      autonomy_controller.py
      safety_governor.py
    api/
      campaign_routes.py
      analytics_routes.py
      experiment_routes.py
      autonomy_routes.py
    tests/
      unit/
        test_campaigns.py
        test_calendar.py
        test_scoring.py
        test_scheduler.py
        test_analytics.py
        test_experiments.py
        test_learning_rules.py
        test_autonomy_controller.py
        test_safety_governor.py
24. Final Phase 3 Command Intent

Build governed autonomy, not reckless automation.

Phase 3 is complete only when the social module can autonomously:

plan
generate
score
schedule
publish
measure
evaluate
learn
adapt

while remaining fully:

policy-bound
event-native
auditable
tenant-isolated
rate-limited
reversible
kill-switchable

That is the correct end-to-end Phase 3 plan for an autonomous plug-and-play social media module.