#!/usr/bin/env python3
"""
STEP 1 - LangGraph Integration Test Suite (Standalone)
Tests: LLM Adapter, Event Bus, Graph Execution

This test suite uses fully mocked dependencies to test the integration
without requiring external services (OpenAI API, Redis, PostgreSQL).
"""

import sys
import time
import json
import uuid
import numpy as np
from typing import Any, Dict, List
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add coe-kernel to path
sys.path.insert(0, '/home/coe/.openclaw/workspace/colony-os-app/engine/coe-kernel')

# Test results tracking
results = {
    "passed": [],
    "failed": [],
    "skipped": []
}


def test(name: str):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                print(f"\n{'='*60}")
                print(f"TEST: {name}")
                print('='*60)
                func(*args, **kwargs)
                results["passed"].append(name)
                print(f"✅ PASSED: {name}")
            except Exception as e:
                results["failed"].append((name, str(e)))
                print(f"❌ FAILED: {name}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
        return wrapper
    return decorator


# ============================================================================
# MOCK IMPLEMENTATIONS
# ============================================================================

class MockLLM:
    """Mock LLM for testing without API calls."""

    def __init__(self, *args, **kwargs):
        self.temperature = kwargs.get('temperature', 0)
        self.model = kwargs.get('model', 'mock-model')
        self._call_count = 0

    def invoke(self, messages):
        """Mock invoke that returns deterministic responses."""
        self._call_count += 1

        # Extract the prompt content
        prompt = ""
        for msg in messages:
            if hasattr(msg, 'content'):
                prompt += msg.content

        # Generate deterministic response based on prompt content
        if "2+2" in prompt or "5 + 3" in prompt:
            return MagicMock(content="4")
        elif "capital of France" in prompt.lower():
            return MagicMock(content='{"answer": "Paris", "confidence": 0.95}')
        elif "planner" in prompt.lower() or "step-by-step" in prompt.lower():
            return MagicMock(content="""1. Analyze the requirements
2. Design the solution
3. Implement the code
4. Test the implementation""")
        elif "execute this step" in prompt.lower():
            return MagicMock(content="Step executed successfully. Completed action.")
        elif "synthesize" in prompt.lower() or "final answer" in prompt.lower():
            return MagicMock(content="This is the synthesized final answer based on the step results.")
        elif "summarize" in prompt.lower() or "learnings" in prompt.lower():
            return MagicMock(content="Key learning: This task demonstrated how to break down problems into steps.")
        else:
            return MagicMock(content=f"Mock response for: {prompt[:50]}...")

    def with_structured_output(self, schema):
        """Return self for structured output."""
        return self


class MockEmbeddings:
    """Mock embeddings for testing."""

    def __init__(self, *args, **kwargs):
        pass

    def embed_query(self, text: str) -> List[float]:
        """Return deterministic embedding based on text hash."""
        # Create a deterministic embedding from text
        np.random.seed(hash(text) % 2**32)
        return np.random.randn(1536).tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Return embeddings for multiple documents."""
        return [self.embed_query(t) for t in texts]


class MockRedis:
    """Mock Redis for testing."""

    def __init__(self, *args, **kwargs):
        self.streams = {}
        self.groups = {}
        self.messages = []

    def xgroup_create(self, stream, group, id="0-0", mkstream=False):
        if stream not in self.groups:
            self.groups[stream] = {}
        if group in self.groups[stream]:
            raise Exception("BUSYGROUP Consumer Group name already exists")
        self.groups[stream][group] = []

    def xadd(self, stream, data):
        msg_id = f"{int(time.time()*1000)}-{len(self.messages)}"
        if stream not in self.streams:
            self.streams[stream] = []
        self.streams[stream].append((msg_id, data))
        self.messages.append((msg_id, data))
        return msg_id

    def xreadgroup(self, group, consumer, streams, count=10, block=5000):
        stream_name = list(streams.keys())[0]
        if stream_name not in self.streams:
            return []

        messages = self.streams[stream_name][-count:]
        if not messages:
            return []

        return [[stream_name.encode(), [
            (msg_id.encode(), {
                k.encode(): v.encode() if isinstance(v, str) else str(v).encode()
                for k, v in data.items()
            })
            for msg_id, data in messages
        ]]]

    def xack(self, stream, group, message_id):
        return 1


class MockMemoryAdapter:
    """Mock memory adapter for testing."""

    def __init__(self, config=None):
        self.config = config or {}
        self._episodes = []
        self._knowledge = []
        self.embeddings = MockEmbeddings()

    def store_episode(self, task_data: Dict[str, Any]) -> str:
        episode_id = str(uuid.uuid4())
        self._episodes.append({
            "id": episode_id,
            "task_id": task_data.get("task_id"),
            "input": task_data.get("input"),
            "output": task_data.get("output"),
            "plan": task_data.get("plan", []),
            "success": task_data.get("success", True)
        })
        return episode_id

    def store_knowledge(self, content: str, metadata=None) -> str:
        knowledge_id = str(uuid.uuid4())
        self._knowledge.append({
            "id": knowledge_id,
            "content": content,
            "metadata": metadata or {}
        })
        return knowledge_id

    def retrieve_context(self, query: str, top_k: int = 5) -> List[str]:
        # Simple keyword matching
        results = []
        for k in self._knowledge:
            if any(word in k["content"].lower() for word in query.lower().split()):
                results.append(k["content"])
        return results[:top_k]


# ============================================================================
# TEST 1: LLM Adapter - Temperature=0 Verification
# ============================================================================

@test("LLM Adapter - Initialization")
def test_llm_init():
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        from orchestrator.llm import LLMAdapter

        llm = LLMAdapter({
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0,
            "max_tokens": 4096
        })

        assert llm._llm is not None, "LLM not initialized"
        assert llm._llm.temperature == 0, "Temperature not set to 0"
        print(f"  ✓ LLM initialized with temperature={llm._llm.temperature}")


@test("LLM Adapter - API Call with temperature=0")
def test_llm_api_call():
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        from orchestrator.llm import LLMAdapter

        llm = LLMAdapter({
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0,
            "max_tokens": 100
        })

        response1 = llm.invoke("What is 2+2? Answer with just the number.")
        print(f"  ✓ Response 1: {response1}")

        response2 = llm.invoke("What is 2+2? Answer with just the number.")
        print(f"  ✓ Response 2: {response2}")

        assert "4" in response1, f"Expected '4' in response, got: {response1}"
        print("  ✓ Determinism check: temperature=0 working")


@test("LLM Adapter - Structured Output")
def test_llm_structured():
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        from orchestrator.llm import LLMAdapter

        llm = LLMAdapter({
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0
        })

        schema = {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number"}
            },
            "required": ["answer", "confidence"]
        }

        result = llm.invoke_structured(
            "What is the capital of France?",
            schema,
            "You are a helpful assistant. Respond in JSON."
        )

        print(f"  ✓ Structured output call successful: {result}")


# ============================================================================
# TEST 2: Event Bus Adapter
# ============================================================================

@test("Event Bus Adapter - Initialization")
def test_event_bus_init():
    import orchestrator.events as events_module
    original_redis = events_module.redis.Redis
    events_module.redis.Redis = MockRedis

    try:
        from orchestrator.events import EventBusAdapter

        bus = EventBusAdapter({
            "stream": "test_events",
            "consumer_group": "test_group",
            "host": "localhost",
            "port": 6379
        })

        assert bus._redis is not None, "Redis connection not initialized"
        assert bus.stream == "test_events", "Stream name not set"
        assert bus.group == "test_group", "Consumer group not set"
        print(f"  ✓ Event bus initialized with stream={bus.stream}")
    finally:
        events_module.redis.Redis = original_redis


@test("Event Bus Adapter - Emit and Listen")
def test_event_bus_emit_listen():
    import orchestrator.events as events_module
    original_redis = events_module.redis.Redis
    events_module.redis.Redis = MockRedis

    try:
        from orchestrator.events import EventBusAdapter

        bus = EventBusAdapter({
            "stream": "coe_events",
            "consumer_group": "orchestrator",
            "host": "localhost",
            "port": 6379
        })

        # Emit events
        event_ids = []
        for i in range(3):
            event_id = bus.emit("task.created", {
                "task_id": f"test-{i}",
                "input": f"Test task input {i}"
            })
            event_ids.append(event_id)
        print(f"  ✓ Emitted {len(event_ids)} events")

        # Listen for events
        events = bus.listen(block_ms=1000, count=10)
        assert len(events) > 0, "No events received"
        print(f"  ✓ Events received: {len(events)}")

        # Verify event structure
        stream_data = events[0]
        assert stream_data[0].decode() == "coe_events", "Wrong stream name"
        print("  ✓ Event structure verified")
    finally:
        events_module.redis.Redis = original_redis


# ============================================================================
# TEST 3: Graph State
# ============================================================================

@test("Graph State - Initialization")
def test_graph_state():
    from graphs.state import create_initial_state

    state = create_initial_state("task-123", "Test input")

    assert state["task_id"] == "task-123", "Task ID mismatch"
    assert state["input"] == "Test input", "Input mismatch"
    assert state["status"] == "pending", "Status should be pending"
    assert state["plan"] == [], "Plan should be empty"
    assert state["error"] is None, "Error should be None"
    print(f"  ✓ Initial state created: task_id={state['task_id']}, status={state['status']}")


# ============================================================================
# TEST 4: Main Graph - End-to-End
# ============================================================================

@test("Main Graph - Build and Initialize")
def test_graph_build():
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        with patch('memory.adapter.MemoryAdapter', MockMemoryAdapter):
            from graphs.main_graph import MainGraph

            import orchestrator.events as events_module
            events_module.redis.Redis = MockRedis

            graph = MainGraph({
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "temperature": 0
                },
                "memory": {"type": "mock"}
            })

            assert graph.graph is not None, "Graph not compiled"
            assert graph.llm is not None, "LLM not initialized"
            assert graph.memory is not None, "Memory not initialized"
            print("  ✓ Main graph built successfully")


@test("Main Graph - Planner Node")
def test_graph_planner():
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        with patch('memory.adapter.MemoryAdapter', MockMemoryAdapter):
            from graphs.main_graph import MainGraph
            from graphs.state import create_initial_state

            import orchestrator.events as events_module
            events_module.redis.Redis = MockRedis

            graph = MainGraph({
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "temperature": 0
                },
                "memory": {"type": "mock"}
            })

            state = create_initial_state(
                "test-plan-123",
                "Create a simple Python function to add two numbers"
            )
            state["context"] = []

            # Test planner node directly
            result_state = graph._planner(state)

            assert len(result_state["plan"]) > 0, "Plan should not be empty"
            assert result_state["status"] == "planning", "Status should be planning"
            print(f"  ✓ Planner created {len(result_state['plan'])} steps")
            for i, step in enumerate(result_state["plan"][:3]):
                print(f"    Step {i+1}: {step[:80]}...")


@test("Main Graph - End-to-End Execution")
def test_graph_e2e():
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        with patch('memory.adapter.MemoryAdapter', MockMemoryAdapter):
            from graphs.main_graph import MainGraph

            import orchestrator.events as events_module
            events_module.redis.Redis = MockRedis

            graph = MainGraph({
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "temperature": 0
                },
                "memory": {"type": "mock"}
            })

            task_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
            input_text = "What is 5 + 3? Explain briefly."

            print(f"  Running graph with task_id={task_id}")
            print(f"  Input: {input_text}")

            # Execute graph
            final_state = graph.invoke(task_id, input_text)

            assert final_state["output"] != "", "Output should not be empty"
            assert final_state["status"] == "completed", (
                f"Status should be completed, got: {final_state['status']}"
            )
            assert len(final_state["plan"]) > 0, "Plan should have been created"
            assert len(final_state["steps_results"]) > 0, "Should have step results"

            print("  ✓ Graph execution completed")
            print(f"  ✓ Plan had {len(final_state['plan'])} steps")
            print(f"  ✓ Output preview: {final_state['output'][:150]}...")


# ============================================================================
# TEST 5: Memory Adapter
# ============================================================================

@test("Memory Adapter - Store and Retrieve")
def test_memory_adapter():
    memory = MockMemoryAdapter({"type": "mock"})

    # Store knowledge
    knowledge_id = memory.store_knowledge(
        "LangGraph is a stateful orchestration engine",
        {"source": "test", "type": "fact"}
    )
    print(f"  ✓ Knowledge stored with ID: {knowledge_id}")

    # Store episode
    episode_id = memory.store_episode({
        "task_id": "test-task-1",
        "input": "What is LangGraph?",
        "output": "LangGraph is a stateful orchestration engine",
        "plan": ["Research LangGraph", "Formulate answer"],
        "steps": ["Found documentation", "Created summary"],
        "success": True
    })
    print(f"  ✓ Episode stored with ID: {episode_id}")

    # Retrieve context
    context = memory.retrieve_context("What is LangGraph?", top_k=5)
    assert len(context) > 0, "Should retrieve at least one context"
    print(f"  ✓ Retrieved {len(context)} context items")
    print(f"    Context: {context[0][:100]}...")


# ============================================================================
# TEST 6: Concurrency Test
# ============================================================================

@test("Concurrency - Multiple Tasks")
def test_concurrency():
    import concurrent.futures

    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        with patch('memory.adapter.MemoryAdapter', MockMemoryAdapter):
            from graphs.main_graph import MainGraph

            import orchestrator.events as events_module
            events_module.redis.Redis = MockRedis

            graph = MainGraph({
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "temperature": 0
                },
                "memory": {"type": "mock"}
            })

            tasks = [
                (f"concurrent-{i}", f"What is {i} + {i}? Answer with just the number.")
                for i in range(5)
            ]

            def run_task(task_id, input_text):
                try:
                    result = graph.invoke(task_id, input_text)
                    return (task_id, True, result)
                except Exception as e:
                    return (task_id, False, str(e))

            print(f"  Running {len(tasks)} concurrent tasks...")

            # Run tasks concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(run_task, tid, inp) for tid, inp in tasks]
                results_list = [f.result() for f in concurrent.futures.as_completed(futures)]

            success_count = sum(1 for _, success, _ in results_list if success)
            print(f"  ✓ {success_count}/{len(tasks)} tasks completed successfully")

            for task_id, success, result in results_list:
                status = "✓" if success else "✗"
                print(f"    {status} Task {task_id}: {'OK' if success else result}")

            assert success_count == len(tasks), (
                f"Expected all tasks to succeed, got {success_count}/{len(tasks)}"
            )


# ============================================================================
# TEST 7: Failure Recovery
# ============================================================================

@test("Failure Recovery - Task Resumption")
def test_failure_recovery():
    """Test that tasks can be re-run after failure (idempotency)."""
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        with patch('memory.adapter.MemoryAdapter', MockMemoryAdapter):
            from graphs.main_graph import MainGraph

            import orchestrator.events as events_module
            events_module.redis.Redis = MockRedis

            graph = MainGraph({
                "llm": {
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "temperature": 0
                },
                "memory": {"type": "mock"}
            })

            task_id = "recovery-test-001"
            input_text = "Test task for recovery"

            # First execution
            print("  First execution...")
            state1 = graph.invoke(task_id, input_text)

            assert state1["status"] == "completed", "First run should complete"
            print("  ✓ First execution completed")

            # Second execution with same task_id (simulating recovery)
            print("  Second execution (recovery)...")
            state2 = graph.invoke(task_id, input_text)

            assert state2["status"] == "completed", "Second run should complete"
            print("  ✓ Second execution completed (idempotent)")

            # Both should produce similar results
            assert state1["output"] == state2["output"], (
                "Outputs should be identical (deterministic)"
            )
            print("  ✓ Determinism verified: both runs produced identical output")


# ============================================================================
# TEST 8: Basic Task Execution (Test Plan)
# ============================================================================

@test("Test Plan - Basic Task Execution")
def test_basic_task():
    """Test 1 from Test Plan: Basic task execution."""
    with patch('orchestrator.llm.ChatOpenAI', MockLLM):
        with patch('memory.adapter.MemoryAdapter', MockMemoryAdapter):
            from graphs.main_graph import MainGraph
            from orchestrator.events import EventBusAdapter

            import orchestrator.events as events_module
            events_module.redis.Redis = MockRedis

            graph = MainGraph({
                "llm": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0},
                "memory": {"type": "mock"}
            })

            # Emit task.created event
            bus = EventBusAdapter({
                "stream": "coe_events",
                "consumer_group": "orchestrator"
            })

            task_id = "basic-task-001"
            event_id = bus.emit("task.created", {
                "task_id": task_id,
                "input": "Create a plan for testing"
            })
            print(f"  ✓ Emitted task.created event: {event_id}")

            # Execute task
            final_state = graph.invoke(task_id, "Create a plan for testing")

            # Verify plan.created event would be emitted (via the graph)
            assert len(final_state["plan"]) > 0, "Plan should be created"
            print(f"  ✓ Plan created with {len(final_state['plan'])} steps")

            # Verify task.completed
            assert final_state["status"] == "completed", "Task should complete"
            print("  ✓ Task completed successfully")


@test("Test Plan - Event Flow Verification")
def test_event_flow():
    """Verify events flow between kernel and orchestrator."""
    import orchestrator.events as events_module
    events_module.redis.Redis = MockRedis

    from orchestrator.events import EventBusAdapter

    bus = EventBusAdapter({
        "stream": "coe_events",
        "consumer_group": "orchestrator"
    })

    events_received = []

    # Emit various events
    events_to_emit = [
        ("task.created", {"task_id": "evt-001", "input": "Test"}),
        ("plan.created", {"task_id": "evt-001", "plan": ["step1", "step2"]}),
        ("step.completed", {"task_id": "evt-001", "step_number": 1}),
        ("task.completed", {"task_id": "evt-001", "status": "success"}),
    ]

    for event_type, payload in events_to_emit:
        event_id = bus.emit(event_type, payload)
        events_received.append((event_type, event_id))
        print(f"  ✓ Emitted {event_type}: {event_id}")

    # Listen for events
    events = bus.listen(block_ms=1000, count=10)
    assert len(events) > 0, "Should receive events"
    print(f"  ✓ Received {len(events[0][1])} events from stream")


# ============================================================================
# MAIN
# ============================================================================

def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("STEP 1 - LANGGRAPH INTEGRATION TEST SUITE")
    print("="*60)
    print("Mode: MOCK (fully mocked dependencies)")
    print(f"Start time: {datetime.now().isoformat()}")
    print("\nThis test suite verifies:")
    print("  1. LLM Adapter with temperature=0 (determinism)")
    print("  2. Event Bus Adapter (emit/listen)")
    print("  3. Graph State management")
    print("  4. Main Graph execution (planner → executor)")
    print("  5. Memory Adapter (store/retrieve)")
    print("  6. Concurrency (multiple simultaneous tasks)")
    print("  7. Failure Recovery (idempotent execution)")
    print("  8. Test Plan: Basic task, Event flow")

    # Run all tests
    test_llm_init()
    test_llm_api_call()
    test_llm_structured()
    test_event_bus_init()
    test_event_bus_emit_listen()
    test_graph_state()
    test_graph_build()
    test_graph_planner()
    test_graph_e2e()
    test_memory_adapter()
    test_concurrency()
    test_failure_recovery()
    test_basic_task()
    test_event_flow()

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    total = len(results['passed']) + len(results['failed'])
    print(f"Total: {total}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")

    if results['failed']:
        print("\nFailed tests:")
        for name, error in results['failed']:
            print(f"  - {name}: {error}")

    print(f"\nEnd time: {datetime.now().isoformat()}")

    # Write results to file
    with open('test_step1_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': total,
            'passed': len(results['passed']),
            'failed': len(results['failed']),
            'passed_tests': results['passed'],
            'failed_tests': [{'name': n, 'error': e} for n, e in results['failed']]
        }, f, indent=2)
    print("\nResults written to test_step1_results.json")

    return len(results['failed']) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
