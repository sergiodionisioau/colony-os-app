Phase 4 — Agent Runtime & Modular Execution Engine

1 FULL SYSTEM PROMPT
You are Gemini 3.1 Pro operating as a deterministic systems engineer.

You are building Phase 4 of the CoE Operating System.

You are NOT allowed to:
- Invent missing specifications
- Introduce probabilistic behavior in core execution paths
- Produce non-reproducible builds
- Violate previously defined kernel, event bus, or policy contracts

You MUST:
- Build strictly modular, hot-swappable Lego blocks
- Ensure each module is independently testable
- Ensure every component registers to the kernel via defined interfaces
- Enforce zero-tolerance validation
- Produce deterministic artifacts only
- Fail loudly if assumptions are violated

You are building:

PHASE 4 — AGENT RUNTIME + MODULE LOADER + RECURSIVE IMPROVEMENT ENGINE

Goal:
Create a plug-and-play runtime where:
- Agents can be registered/unregistered
- AI providers can be swapped
- Modules can be mounted/unmounted
- Self-improvement is bounded by policy engine
- No component can escalate privileges

All artifacts must compile.
All contracts must validate.
All tests must pass.

If anything is ambiguous → halt and emit SPEC_BLOCKER.
2️⃣ FULL SPECIFICATION
Phase 4 Objective

Create a deterministic runtime that:

Hosts multiple agents (CoE, Colony, Verified)

Allows provider abstraction (OpenAI, Gemini, local model)

Loads Lego modules dynamically

Allows recursive improvement with guardrails

Maintains immutable audit trail

3️⃣ ARCHITECTURE
               ┌──────────────────────┐
               │      Kernel          │
               └──────────┬───────────┘
                          │
               ┌──────────┴───────────┐
               │      Event Bus       │
               └──────────┬───────────┘
                          │
               ┌──────────┴───────────┐
               │    Policy Engine     │
               └──────────┬───────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────┴───────┐ ┌───────┴───────┐ ┌───────┴────────┐
│ Agent Runtime │ │ Module Loader │ │ Improvement Eng │
└───────┬───────┘ └───────┬───────┘ └────────┬────────┘
        │                 │                   │
   AI Provider        Lego Blocks         Verified Patch
4️⃣ CORE COMPONENTS TO BUILD
4.1 Agent Runtime
Responsibilities:

Instantiate agent identity

Load agent configuration

Bind AI provider

Route input/output via Event Bus

Enforce policy before execution

Log every action

Agent Definition Schema (YAML)
agent:
  id: "cole"
  role: "planner"
  provider: "gemini"
  capabilities:
    - plan
    - analyze
  memory:
    type: "vector"
    backend: "chroma"
Hard Rules:

Agent cannot execute without policy validation

Agent cannot call provider directly

Agent must go through runtime adapter

4.2 AI Provider Adapter Layer

Must support:

OpenAI

Gemini

Local LLM

Future provider

Unified Interface:

class LLMProvider:
    def generate(self, prompt: str, config: dict) -> str:
        pass

Must enforce:

Deterministic temperature=0 in system mode

Token limits

Cost tracking

Timeout

4.3 Module Loader (Lego System)

Each module must contain:

module.yaml
manifest.json
entry.py
tests/

Module Manifest:

{
  "name": "crm_module",
  "version": "1.0.0",
  "permissions": ["db.read", "db.write"],
  "events": ["customer.created"]
}

Loader Responsibilities:

Validate manifest

Verify signature

Register to event bus

Enforce capability scope

Reject on mismatch

4.4 Recursive Improvement Engine

Purpose:
Allow agent to propose improvements to modules.

Strict Constraints:

Cannot modify kernel

Cannot modify policy engine

Must produce diff

Must pass unit tests

Must be approved by human

Must pass static analysis

Improvement Flow:

Agent → Propose Patch
Policy → Validate Scope
CI Engine → Run Tests
Human → Approve
Module → Replace Old Version
Audit → Log Change
5️⃣ ARTIFACTS GEMINI MUST PRODUCE

agent_runtime/

provider_adapters/

module_loader/

improvement_engine/

tests/phase4/

contracts/

ci_config.yaml

threat_model.md

audit_schema.json

No artifact missing.
No placeholder files allowed.

6️⃣ STRICT ZERO-TOLERANCE BASELINE

The build fails if:

Any module can bypass policy

Any agent calls provider directly

Any improvement auto-applies

Any unsigned module loads

Any test missing

Any schema undefined

Any runtime panic not caught

System must:

Crash on violation

Log violation

Prevent escalation

7️⃣ HAPPY PATH DEFINITION

System is considered working when:

Register Agent "Cole"

Register Module "CRM"

Agent requests plan

Provider returns deterministic output

Module processes event

Improvement engine proposes safe patch

Human approves

Patch applied

All logs verifiable

No policy violation

8️⃣ UNIT TEST REQUIREMENTS

Minimum tests:

Agent Runtime

Cannot execute without policy token

Cannot use undefined capability

Cannot exceed token limit

Provider Adapter

Temperature forced to 0 in system mode

Timeout handled

Cost tracking increments

Module Loader

Reject unsigned module

Reject invalid schema

Reject missing permissions

Improvement Engine

Reject patch modifying kernel

Reject patch without diff

Reject failing test patch

Approve valid patch

9️⃣ DONE CRITERIA

Phase 4 is DONE when:

All tests pass

No runtime warnings

Full deterministic rebuild reproducible

Hash of build stable

Agents hot-swappable

Providers hot-swappable

Modules hot-swappable

Improvement bounded

Audit complete

No TODO comments anywhere

10 STRETCH OBJECTIVES (OPTIONAL)

If stable:

Sandboxed WASM module runtime

Distributed multi-node agent mesh

Capability calculus enforcement

Economic cost optimizer

Policy formal proof stub

11 FAILURE CONDITIONS

Immediate halt if:

Circular dependency between modules

Event loop deadlock

Policy bypass

Runtime memory leak

Unbounded recursion

Emit:

PHASE_4_BLOCKER:
<reason>
PHASE 4 SUMMARY

You are not building a chatbot.

You are building:

A deterministic agent operating system runtime
With hot-swappable AI providers
With Lego modules
With bounded self-improvement
With strict governance
With zero escalation risk