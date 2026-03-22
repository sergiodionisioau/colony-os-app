# Colony OS - Knowledge Graph Schema

## Core Philosophy

> Tasks are first-class citizens. Everything else connects to them.

```
┌─────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE GRAPH                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐      ┌──────────┐      ┌──────────────────┐      │
│  │  AGENT   │──────│   TASK   │──────│   CONVERSATION   │      │
│  └──────────┘      └──────────┘      └──────────────────┘      │
│       │                 │                  │                   │
│       │                 │                  │                   │
│  ┌──────────┐      ┌──────────┐      ┌──────────────────┐      │
│  │  SKILL   │      │ RESOURCE │      │      FACT        │      │
│  └──────────┘      └──────────┘      └──────────────────┘      │
│                            │                                     │
│                       ┌──────────┐                             │
│                       │ PROJECT  │                             │
│                       └──────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Entity Types

### 1. AGENT (Node)
```
- id: UUID
- name: String (e.g., "Coe", "Codex", "Qwen")
- type: Enum [orchestrator, specialist, sub-agent, external]
- model: String (e.g., "ollama/kimi-k2.5:cloud")
- capabilities: String[] (skills/tools it can use)
- status: Enum [active, idle, offline, error]
- created_at: Timestamp
- last_seen: Timestamp
- metadata: JSON (cost tracking, token usage, etc.)
```

**Relationships:**
- AGENT `-[:CREATED_BY]->` TASK
- AGENT `-[:ASSIGNED_TO]->` TASK
- AGENT `-[:HAS_SKILL]->` SKILL
- AGENT `-[:PARTICIPATED_IN]->` CONVERSATION

### 2. TASK (Central Node)
```
- id: UUID
- title: String
- description: Text
- type: Enum [coding, research, review, planning, analysis, communication, maintenance]
- status: Enum [backlog, todo, in_progress, blocked, review, done, cancelled]
- priority: Integer (1-5, 1 = highest)
- complexity: Enum [trivial, simple, moderate, complex, epic]
- estimated_duration: Interval
- actual_duration: Interval
- created_at: Timestamp
- started_at: Timestamp
- completed_at: Timestamp
- due_date: Timestamp (optional)
- roi_score: Float (calculated from impact/effort)
- prediction_confidence: Float (ML model confidence)
```

**Relationships:**
- TASK `-[:DEPENDS_ON]->` TASK (blocking dependencies)
- TASK `-[:RELATED_TO]->` TASK
- TASK `-[:SUBTASK_OF]->` TASK
- TASK `-[:BELONGS_TO]->` PROJECT
- TASK `-[:REQUIRES]->` RESOURCE
- TASK `-[:PRODUCES]->` FACT
- TASK `-[:LINKS_TO]->` CONVERSATION

### 3. CONVERSATION (Node)
```
- id: UUID
- channel: String (telegram, discord, webchat, etc.)
- channel_id: String (channel-specific ID)
- summary: Text (AI-generated)
- key_points: String[] (extracted entities/actions)
- sentiment: Float (-1 to 1)
- token_count: Integer
- started_at: Timestamp
- ended_at: Timestamp
- is_resolved: Boolean
```

**Relationships:**
- CONVERSATION `-[:CONTAINS]->` FACT
- CONVERSATION `-[:TRIGGERED]->` TASK

### 4. FACT (Node)
```
- id: UUID
- content: Text
- type: Enum [decision, insight, error, preference, constraint, contact, project_state]
- confidence: Float (0-1, based on source/extraction)
- source: String (conversation_id, document, etc.)
- extracted_at: Timestamp
- valid_until: Timestamp (optional, for time-sensitive facts)
- embedding: Vector (for semantic search)
```

**Relationships:**
- FACT `-[:RELATES_TO]->` FACT
- FACT `-[:CONTRADICTS]->` FACT (for conflict resolution)
- FACT `-[:SUPERSEDES]->` FACT (versioning)

### 5. SKILL (Node)
```
- id: UUID
- name: String
- description: Text
- category: Enum [communication, coding, data, automation, analysis]
- requirements: JSON (tools, APIs, etc.)
- success_rate: Float (tracked over time)
- avg_duration: Interval
```

**Relationships:**
- SKILL `-[:REQUIRES]->` SKILL (prerequisites)
- SKILL `-[:COMPOSES]->` SKILL (complex skills)

### 6. RESOURCE (Node)
```
- id: UUID
- name: String
- type: Enum [api_key, credential, file, compute, budget]
- value: Encrypted (if sensitive)
- cost_per_use: Float
- quota_remaining: Float
- expires_at: Timestamp
```

### 7. PROJECT (Node)
```
- id: UUID
- name: String
- description: Text
- status: Enum [planning, active, paused, completed, archived]
- goals: String[]
- metrics: JSON (KPIs, progress)
- start_date: Timestamp
- target_date: Timestamp
```

## Task Management Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     TASK LIFECYCLE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BACKLOG                                                        │
│     │                                                           │
│     ▼                                                           │
│  ┌─────────────┐    ROI Score + Prediction Model              │
│  │   SCORE     │    Impact × Confidence ÷ Effort              │
│  └─────────────┘                                                │
│     │                                                           │
│     ▼                                                           │
│  ┌─────────────┐    Auto-schedule based on:                     │
│  │  SCHEDULE   │    - Agent availability                        │
│  └─────────────┘    - Dependencies                               │
│     │                - Resource constraints                      │
│     ▼                - Due dates                               │
│  ┌─────────────┐                                                │
│  │   ASSIGN    │    Match task to best agent:                   │
│  └─────────────┘    - Required skills                            │
│     │                - Current load                              │
│     ▼                - Cost optimization                         │
│  ┌─────────────┐                                                │
│  │  EXECUTE    │    Track:                                      │
│  └─────────────┘    - Token usage                                │
│     │                - Time spent                              │
│     ▼                - Blockers                                  │
│  ┌─────────────┐                                                │
│  │   VERIFY    │    Check completion criteria:                   │
│  └─────────────┘    - Output quality                             │
│     │                - Tests pass                                │
│     ▼                - User acceptance                           │
│  ┌─────────────┐                                                │
│  │   DONE      │    Extract learnings → FACTS                    │
│  └─────────────┘    Update agent performance                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Model Routing Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODEL ROUTER                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐               │
│  │   KIMI     │  │   QWEN     │  │ DEEPSEEK   │               │
│  │  k2.5:cloud│  │ 2.5:3b     │  │ -r1:1.5b   │               │
│  │            │  │            │  │            │               │
│  │ Primary    │  │ Fallback   │  │ Reasoning  │               │
│  │ 262k ctx   │  │ 128k ctx   │  │ 128k ctx   │               │
│  │ $$$        │  │ Free       │  │ Free       │               │
│  └────────────┘  └────────────┘  └────────────┘               │
│       │               │               │                        │
│       └───────────────┴───────────────┘                        │
│                  │                                               │
│                  ▼                                               │
│         ┌─────────────┐                                          │
│         │   ROUTER    │  Decision Logic:                        │
│         └─────────────┘                                          │
│                  │                                               │
│    ┌─────────────┼─────────────┐                               │
│    │             │             │                               │
│    ▼             ▼             ▼                               │
│ Task type    Rate limit   Reasoning?                          │
│ Complexity   Available   Token budget                          │
│ Urgency      Cost cap    Context size                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Routing Rules

1. **Priority to Kimi** (ollama/kimi-k2.5:cloud)
   - Default for: Complex tasks, long context, production code
   - Unless: Rate limited → fallback to Qwen

2. **Qwen 2.5:3b** (Local fallback)
   - Use when: Kimi rate limited, simple tasks, quick responses
   - Good for: Summaries, classifications, short generations
   - Benefits: No rate limits, zero cost, always available

3. **DeepSeek R1** (Reasoning)
   - Use when: Planning, analysis, multi-step reasoning required
   - Benefits: Chain-of-thought visible, good for task breakdown

### Automatic Fallback

```python
# Pseudocode for router
def route_task(task):
    if task.requires_reasoning:
        return "deepseek-r1:1.5b"
    
    if kimi_available and task.complexity != "trivial":
        return "kimi-k2.5:cloud"
    
    if kimi_rate_limited or task.complexity == "trivial":
        return "qwen2.5:3b"  # Fast local fallback
    
    return "kimi-k2.5:cloud"  # Default
```

## Task Examples

| Task | Complexity | Assigned To | Model | Estimated |
|------|-----------|-------------|-------|-----------|
| "Summarize this PR" | Trivial | Me | Qwen | 30s |
| "Review codebase for bugs" | Complex | Codex | Kimi | 10m |
| "Plan architecture for feature X" | Epic | Me + Subagents | DeepSeek R1 → Kimi | 1h |
| "Write tests for auth module" | Moderate | Codex | Kimi | 5m |
| "Fix typo in README" | Trivial | Me | Qwen | 10s |

## Next Steps

1. ✅ Design complete
2. ⏳ Implement Postgres + pgvector
3. ⏳ Create tables/views
4. ⏳ Build task scheduler
5. ⏳ Add model router
6. ⏳ Connect to OpenClaw

Ready to implement? I'll work on Postgres installation while you review this schema.
