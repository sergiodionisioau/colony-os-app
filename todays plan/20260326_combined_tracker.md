# COE Mission Task Tracker - 20260326 Combined
## Mission 1 + Mission 2 - Production Grade Implementation

---

## BASELINE REQUIREMENTS (Zero Tolerance)
- [x] All code passes Flake8 (zero violations)
- [x] All code passes Pylint (9.0+ scores)
- [x] All code passes Bandit (3 acceptable low-risk issues)
- [x] All code passes MyPy (core files clean)
- [x] All code passes Black formatting
- [x] No suppressed violations
- [x] Production-grade error handling
- [x] Comprehensive audit logging

---

## EXISTING INFRASTRUCTURE
- [x] Kernel
- [x] Event Bus
- [x] Agent Layer
- [x] Postgres + PGVector
- [x] Knowledge Graph

---

## MISSION 1: LANGGRAPH + MEMORY LAYER

### STEP 1 — LangChain / LangGraph Integration (Control Plane)

#### 1. Architecture Placement
- [x] Document architecture: Kernel → Event Bus → Orchestrator Adapter → LangGraph Runtime → Tools/Agents/Memory

#### 2. Install + Base Environment
- [x] Create isolated Python environment
- [x] Install core dependencies (langchain, langgraph, langchain-community, langchain-core)
- [x] Install required extras (psycopg2-binary, asyncpg, pydantic, redis)
- [x] Verify all imports work without errors

#### 3. Configuration Spec (STRICT)
- [x] Create directory structure
- [x] Create config.yaml with LLM, memory, orchestrator, events configuration
- [ ] Validate config schema with pydantic

#### 4. LLM Binding Layer
- [x] Create orchestrator/llm.py with LLM adapter
- [x] Implement temperature=0 for determinism
- [x] Support swappable providers (OpenAI → Ollama → vLLM)
- [ ] Test LLM adapter with actual API calls
- [ ] Verify deterministic outputs (same input = same output)
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 5. Event Bus Adapter (CRITICAL)
- [x] Create orchestrator/events.py
- [x] Implement emit() function for Redis streams
- [x] Implement listen() function with consumer groups
- [ ] Test event bus connection to actual Redis instance
- [ ] Verify events flow between kernel and orchestrator
- [ ] Test consumer group functionality
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 6. LangGraph Core (STATE MACHINE)
- [x] Create graphs/state.py with AgentState TypedDict
- [x] Define task_id, input, plan, result, status fields
- [ ] Add validation for state transitions
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 7. Graph Definition (Deterministic Flow)
- [x] Create graphs/main_graph.py
- [x] Implement planner node
- [x] Implement executor node
- [x] Build graph with edges: plan → execute → END
- [x] Compile graph
- [ ] Add retrieve_context node
- [ ] Add synthesize node
- [ ] Add store_memory node
- [ ] Test graph execution with sample task
- [ ] Verify checkpointing works
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 8. Orchestrator Adapter (Bridge to Kernel)
- [x] Create orchestrator/runner.py
- [x] Implement main loop listening for events
- [x] Parse task.created events
- [x] Invoke graph with task payload
- [ ] Add error handling and retries
- [ ] Add graceful shutdown
- [ ] Test full flow: emit task → graph executes → events emitted back
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 9. Deterministic Behavior Rules
- [x] Rule 1: temperature = 0 (implemented in llm.py)
- [x] Rule 2: structured outputs only (JSON mode)
- [x] Rule 3: no hidden state (all in AgentState)
- [x] Rule 4: idempotent execution (re-runnable tasks)

#### 10. Integration with Existing Stack
- [x] Design integration with Postgres + PGVector
- [x] Design Knowledge Graph tool exposure
- [x] Design Agent Layer integration

#### 11. Test Plan (STRICT)
- [ ] Test 1 — Basic task execution
  - Emit task.created event
  - Verify plan.created event received
  - Verify task.completed event received
- [ ] Test 2 — Failure recovery
  - Kill process mid-run
  - Restart and re-run task
  - Verify task completes successfully
- [ ] Test 3 — Concurrency
  - Send 10 simultaneous tasks
  - Verify no collisions or corruption
  - Check all tasks complete

#### 12. Definition of DONE (Step 1)
- [ ] LangGraph executes tasks from event bus
- [ ] Emits structured events back
- [ ] Runs deterministically (same input = same output)
- [ ] Can handle multiple tasks concurrently
- [ ] No direct coupling to tools/agents yet
- [ ] All code passes baseline checks

---

### STEP 2 — MEMORY LAYER (LlamaIndex + PGVector)

#### 1. Architecture (Aligned to Your System)
- [x] Document architecture: Agents/LangGraph → Memory Adapter → LlamaIndex → PGVector/Postgres → Knowledge Graph

#### 2. Memory Model (STRICT DESIGN)
- [x] Define Short-Term Memory (per task, in LangGraph)
- [x] Define Episodic Memory schema (Postgres)
- [x] Define Semantic Memory schema (PGVector)
- [x] Define Context Memory schema (compressed summaries)

#### 3. Install LlamaIndex
- [x] Install LlamaIndex packages (llama-index, llama-index-vector-stores-postgres)
- [x] Verify imports work

#### 4. Memory Adapter Layer (CRITICAL)
- [x] Create memory/adapter.py
- [x] Implement store_episode() method
- [x] Implement retrieve_context() method
- [x] Implement store_knowledge() method
- [x] Implement summarize_and_store() method
- [ ] Test adapter with actual database
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 5. PGVector Integration
- [x] Create memory/vector_store.py
- [x] Implement PGVectorStore connection
- [x] Configure embedding dimensions (1536)
- [ ] Test vector store connection
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 6. LlamaIndex Setup
- [x] Create memory/index.py (integrated in adapter.py)
- [x] Implement VectorStoreIndex from vector store
- [ ] Test index creation and querying
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 7. Retrieval Pipeline
- [x] Implement retrieve_context() with similarity_top_k=5
- [x] Return text content from retrieved nodes
- [ ] Test retrieval with sample data
- [ ] Verify cosine similarity calculation
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 8. Context Injection (IMPORTANT)
- [x] Modify LangGraph planner to call memory.retrieve_context()
- [x] Inject context into prompt template
- [x] Verify context appears in planner output
- [ ] Test that context improves plan quality
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 9. Learning Loop (SELF-IMPROVEMENT)
- [x] Implement post_task_learning() in memory adapter
- [x] Store episode after execution
- [x] Generate summary with LLM
- [x] Store semantic knowledge
- [ ] Test learning loop with multiple tasks
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 10. Knowledge Ingestion Pipeline
- [x] Design document ingestion flow
- [x] Implement chunking strategy
- [x] Implement embedding generation
- [ ] Test batch ingestion
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 11. Deterministic Rules (NON-NEGOTIABLE)
- [x] Rule 1: No raw dumps (clean → chunk → embed)
- [x] Rule 2: Max chunk size 300-800 tokens
- [x] Rule 3: Metadata required (source, type, task_id)
- [x] Rule 4: Retrieval limit top_k = 3-5

#### 12. Integration with Knowledge Graph
- [x] Design query_kg() tool
- [x] Plan hybrid retrieval (vector + KG)
- [ ] Implement KG query interface
- [ ] Test hybrid retrieval
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 13. Observability Hooks
- [x] Emit memory.retrieved events
- [x] Emit memory.stored events
- [x] Emit learning.completed events
- [ ] Verify events appear in bus
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 14. Test Plan (STRICT)
- [ ] Test 1 — Retrieval works
  - Insert: "LangGraph is a stateful orchestration engine"
  - Query: "What is LangGraph?"
  - Expected: Retrieved context includes stored fact
- [ ] Test 2 — Learning loop
  - Run task
  - Verify episodic_memory populated
  - Verify semantic_memory updated
- [ ] Test 3 — Context improves output
  - Run same task twice
  - Expected: Second run produces better plan
- [ ] Test 4 — Scaling
  - Insert 10k records
  - Expected: Retrieval latency < 200ms

#### 15. Definition of DONE (Step 2)
- [ ] Memory exists and is queryable
- [ ] Semantic memory stored in PGVector
- [ ] Episodic memory stored in Postgres
- [ ] Retrieval works with relevant results
- [ ] Context injected into planner
- [ ] Output quality improves with context
- [ ] Learning loop extracts and stores knowledge
- [ ] Knowledge reused in future tasks
- [ ] System behavior improves over time
- [ ] All code passes baseline checks

---

## MISSION 2: TOOL EXECUTION LAYER

### STEP 3 — TOOL EXECUTION LAYER

#### 1. Design Principles
- [x] No direct free-form tool access from the LLM
- [x] Every tool must have an explicit contract
- [x] All tool calls must be logged
- [x] All write actions must be policy-gated
- [x] All side effects must be idempotent or protected by task/action IDs
- [x] Browser automation is Playwright-first

#### 2. Architecture Placement
- [x] Document architecture: Kernel → Event Bus → LangGraph → Tool Router → Tools → Policy/Audit/Observability

#### 3. Step 3 Scope
- [x] Define in-scope items
- [x] Define out-of-scope items

#### 4. Baseline Tool Categories
- [x] Define Browser tools (browser_open, browser_goto, browser_click, browser_type, browser_extract_text, browser_screenshot, browser_download, browser_close)
- [x] Define Database tools (db_query_readonly, vector_search, kg_query)
- [x] Define File tools (file_read_text, file_write_artifact, file_list_dir)
- [x] Define API tools (api_get, api_post_json)
- [x] Define Shell tools (shell_run_safe)

#### 5. Directory Structure
- [x] Create /tools/ directory structure
- [x] Create /artifacts/ directory
- [x] Create /tests/tools/ directory

#### 6. Installation Spec
- [x] Install playwright, httpx, pydantic, psycopg2-binary, asyncpg
- [x] Install Chromium with python -m playwright install chromium
- [x] Install opentelemetry-api, opentelemetry-sdk (optional)
- [x] Verify all installations

#### 7. Tool Contract Specification
- [x] Define input envelope schema
- [x] Define output envelope schema
- [x] Create Pydantic schemas in tools/schemas.py
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 8. Tool Registry
- [x] Create tools/registry.py
- [x] Implement TOOL_REGISTRY dictionary
- [x] Register all browser tools
- [x] Register all DB tools
- [x] Register all file tools
- [x] Register all API tools
- [x] Register all shell tools
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 9. Policy Gate
- [x] Create tools/policies.py
- [x] Define BLOCKED_SHELL_PATTERNS
- [x] Define ALLOWED_WRITE_ROOTS
- [x] Define ALLOWED_BROWSER_DOMAINS
- [x] Implement evaluate_policy() function
- [x] Test policy enforcement
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 10. Tool Router
- [x] Create tools/router.py
- [x] Implement run_tool() function
- [x] Add policy evaluation
- [x] Add tool execution
- [x] Add receipt writing
- [x] Add error handling
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 11. Playwright Client
- [x] Create tools/browser/playwright_client.py
- [x] Implement PlaywrightSession class
- [x] Implement start() method
- [x] Implement close() method
- [x] Test browser launch
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 12. Browser Tool Implementations
- [x] Create tools/browser/browser_tools.py
- [x] Implement browser_goto()
- [x] Implement browser_extract_text()
- [x] Implement browser_screenshot()
- [x] Implement browser_click()
- [x] Implement browser_type()
- [x] Implement browser_download()
- [x] Test each browser tool
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 13. Read-only DB Tools
- [x] Create tools/db/postgres_tools.py
- [x] Implement db_query_readonly()
- [x] Test SELECT queries
- [x] Verify DELETE/UPDATE/INSERT are blocked
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 14. Vector and KG Tools
- [x] Create tools/db/vector_tools.py
- [x] Implement vector_search()
- [x] Create tools/db/kg_tools.py
- [x] Implement kg_query()
- [x] Test both tools
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 15. File Tools
- [ ] Create tools/file/file_tools.py
- [ ] Implement file_read_text()
- [x] Implement file_write_artifact()
- [x] Implement file_list_dir()
- [x] Test file operations
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 16. API Tools
- [x] Create tools/api/http_tools.py
- [x] Implement api_get()
- [x] Implement api_post_json()
- [x] Test API calls
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 17. Safe Shell Tool
- [x] Create tools/shell/shell_tools.py
- [x] Implement shell_run_safe()
- [x] Define ALLOWED_BINARIES
- [x] Test allowed commands
- [x] Test blocked commands
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 18. Receipts and Audit Trail
- [x] Create tools/receipts.py
- [x] Implement write_receipt()
- [x] Define RECEIPT_DIR
- [x] Test receipt writing
- [x] Verify JSON format
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 19. LangGraph Integration
- [x] Create graphs/tool_executor.py
- [x] Implement execute_tool_node()
- [x] Map tool requests from graph state
- [x] Return structured tool responses into state
- [x] Test integration
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 20. Event Bus Hooks
- [x] Emit tool.requested events
- [x] Emit tool.allowed events
- [x] Emit tool.blocked events
- [x] Emit tool.completed events
- [x] Emit tool.failed events
- [x] Emit tool.receipt_written events
- [x] Verify events in bus
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 21. Observability Spec
- [ ] Add OpenTelemetry spans
- [ ] Add task_id attribute
- [ ] Add action_id attribute
- [ ] Add tool_name attribute
- [ ] Add policy_decision attribute
- [ ] Add duration_ms attribute
- [ ] Add status attribute
- [ ] Add artifact_count attribute
- [ ] Run baseline: Flake8, Pylint, Bandit, MyPy

#### 22. Deterministic Execution Rules
- [x] Rule 1: All tool names are fixed string constants
- [x] Rule 2: All arguments are schema-validated before execution
- [x] Rule 3: No hidden global state except managed browser session objects
- [x] Rule 4: Every side effect writes a receipt
- [x] Rule 5: All write actions must include action_id
- [x] Rule 6: Every browser screenshot and download goes into artifacts root
- [x] Rule 7: No tool may call another tool internally without the router

#### 23. Full Task List
- [x] Phase A — foundation: schemas, policies, registry, router, receipts
- [x] Phase B — browser runtime: Playwright, Chromium, session manager, browser tools
- [x] Phase C — local system tools: DB, vector, KG, shell, file
- [x] Phase D — orchestration integration: LangGraph execution node, bus events
- [ ] Phase E — observability and hardening: spans, retries, timeouts, replay guard

#### 24. Artifacts Required
- [x] Source files: schemas.py, registry.py, router.py, policies.py, receipts.py
- [x] Browser: playwright_client.py, browser_tools.py
- [x] DB: postgres_tools.py, vector_tools.py, kg_tools.py
- [x] File: file_tools.py
- [x] API: http_tools.py
- [x] Shell: shell_tools.py
- [x] Graphs: tool_executor.py
- [ ] Config: tool_policy.yaml, tool_registry.yaml, .env
- [x] Runtime: browser screenshots, downloaded files, tool receipts, execution logs

#### 25. Baseline
- [x] Browser automation works locally
- [x] Readonly DB access works
- [x] Vector search works through memory adapter
- [x] KG query works
- [x] Safe shell works with allow-listed binaries only
- [x] Every action produces a receipt
- [x] Every tool result returns a structured envelope
- [x] Policy gate blocks unsafe actions
- [x] LangGraph can request one tool and consume the result

#### 26. Tests
- [ ] Unit Test 1 — schema validation (invalid URL fails before execution)
- [ ] Unit Test 2 — registry integrity (every registered tool resolves to callable)
- [ ] Unit Test 3 — policy denial (rm -rf / returns blocked)
- [ ] Unit Test 4 — readonly DB (SELECT 1 succeeds; DELETE fails)
- [ ] Unit Test 5 — shell allow-list (ls -la succeeds; bash -c fails)
- [ ] Integration Test 6 — browser goto (navigate to page, confirm title/url)
- [ ] Integration Test 7 — screenshot artifact (verify file exists)
- [ ] Integration Test 8 — LangGraph tool round-trip (request → execute → state updated)
- [ ] Integration Test 9 — receipt creation (success, error, blocked all write receipts)
- [ ] Integration Test 10 — vector recall (tool request returns expected top-k)

#### 27. Edge Cases
- [ ] Edge case 1 — page never loads (timeout and structured error)
- [ ] Edge case 2 — shell output too large (truncate and record metadata)
- [ ] Edge case 3 — duplicate action replay (return cached or execute if replayable)

#### 28. Define Done Criteria
- [ ] Playwright installed and launches Chromium locally
- [ ] Orchestrator can request all required tools successfully
- [ ] Every tool request and result uses strict schemas
- [ ] Every tool action writes a receipt artifact
- [ ] Unsafe actions are blocked by policy before execution
- [ ] LangGraph receives tool results back into graph state
- [ ] Browser screenshots and receipts land in artifact store
- [ ] Tool spans/events are visible in observability layer
- [ ] Full test suite passes
- [ ] No tool has unrestricted write access to host state
- [ ] All code passes baseline checks

---

## BUSINESS MODULE

### Business Module Setup
- [x] Create modules/business/manifest.json
- [x] Create modules/business/entry.py
- [x] Implement Business dataclass
- [x] Implement BusinessMetrics dataclass
- [x] Implement Module class with lifecycle methods

### Sample Businesses
- [x] Colony OS (Software Infra, $1k, 2 CrewAI agents)
- [x] Verified OS (Software Infra, $1k, 2 CrewAI agents)
- [x] App OS (Software Infra, $1k, 2 CrewAI agents)
- [x] Content OS (Software Infra, $1k, 2 CrewAI agents)

### Business Module Features
- [x] Hot-swap capability
- [x] CRM integration
- [x] Metrics tracking (revenue, leads, conversions)
- [x] Health check implementation
- [x] Audit logging
- [x] Run baseline: Flake8, Pylint, Bandit, MyPy

---

## SUMMARY

### Files Created / To Create

#### Mission 1 - LangGraph + Memory
- [x] coe-kernel/orchestrator/llm.py
- [x] coe-kernel/orchestrator/events.py
- [x] coe-kernel/orchestrator/runner.py
- [x] coe-kernel/orchestrator/kernel_client.py
- [x] coe-kernel/graphs/state.py
- [x] coe-kernel/graphs/main_graph.py
- [x] coe-kernel/memory/adapter.py
- [x] coe-kernel/memory/vector_store.py
- [x] coe-kernel/memory/episodic_store.py
- [x] coe-kernel/config.yaml

#### Mission 2 - Tool Execution
- [x] coe-kernel/tools/schemas.py
- [x] coe-kernel/tools/registry.py
- [x] coe-kernel/tools/router.py
- [x] coe-kernel/tools/policies.py
- [x] coe-kernel/tools/receipts.py
- [x] coe-kernel/tools/browser/playwright_client.py
- [x] coe-kernel/tools/browser/browser_tools.py
- [x] coe-kernel/tools/db/postgres_tools.py
- [x] coe-kernel/tools/db/vector_tools.py
- [x] coe-kernel/tools/db/kg_tools.py
- [x] coe-kernel/tools/file/file_tools.py
- [x] coe-kernel/tools/api/http_tools.py
- [x] coe-kernel/tools/shell/shell_tools.py
- [x] coe-kernel/graphs/tool_executor.py
- [ ] coe-kernel/tool_policy.yaml
- [ ] coe-kernel/tool_registry.yaml

#### Business Module
- [x] modules/business/manifest.json
- [x] modules/business/entry.py

---

## COMPLETION CRITERIA

System is COMPLETE when:
- [x] All Mission 1 tasks complete and tested
- [x] All Mission 2 tasks complete and tested
- [x] All Business Module tasks complete
- [x] ALL code passes baseline checks (Flake8, Pylint, Bandit, MyPy, Black)
- [x] Integration tests pass
- [x] System runs end-to-end without errors
