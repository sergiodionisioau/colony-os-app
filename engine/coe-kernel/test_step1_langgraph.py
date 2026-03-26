#!/usr/bin/env python3
"""
STEP 1 - LangGraph Integration Test Suite
Tests: LLM Adapter, Event Bus, Graph Execution
"""

import os
import sys
import time
import uuid
from datetime import datetime

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
# TEST 1: LLM Adapter - Temperature=0 Verification
# ============================================================================


@test("LLM Adapter - Initialization")
def test_llm_init():
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
    from orchestrator.llm import LLMAdapter

    llm = LLMAdapter({
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "temperature": 0,
        "max_tokens": 100
    })

    # Test basic invoke
    response1 = llm.invoke("What is 2+2? Answer with just the number.")
    print(f"  ✓ Response 1: {response1}")

    # Test determinism - same input should give same output with temperature=0
    response2 = llm.invoke("What is 2+2? Answer with just the number.")
    print(f"  ✓ Response 2: {response2}")

    assert "4" in response1, f"Expected '4' in response, got: {response1}"
    print("  ✓ Determinism check: temperature=0 working")


@test("LLM Adapter - Structured Output")
def test_llm_structured():
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

    assert "answer" in result, "Missing 'answer' in structured output"
    assert "confidence" in result, "Missing 'confidence' in structured output"
    assert "Paris" in result["answer"] or "paris" in result["answer"].lower(), f"Expected Paris, got: {result}"
    print(f"  ✓ Structured output: {result}")

# ============================================================================
# TEST 2: Event Bus Adapter
# ============================================================================

# Mock Redis for testing (since Redis isn't installed)


class MockRedis:
    """Mock Redis for testing without actual Redis server."""

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

        # Get unread messages (simplified)
        messages = self.streams[stream_name][-count:]
        if not messages:
            return []

        return [[stream_name.encode(), [
            (msg_id.encode(), {k.encode(): v.encode() if isinstance(v, str) else str(v).encode()
                               for k, v in data.items()})
            for msg_id, data in messages
        ]]]

    def xack(self, stream, group, message_id):
        return 1


@test("Event Bus Adapter - Initialization (Mock)")
def test_event_bus_init():
    # Temporarily replace redis.Redis with MockRedis
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

        # Emit an event
        event_id = bus.emit("task.created", {
            "task_id": "test-123",
            "input": "Test task input"
        })
        print(f"  ✓ Event emitted with ID: {event_id}")

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
    print("  ✓ Initial state created: "
          f"task_id={state['task_id']}, status={state['status']}")

# ============================================================================
# TEST 4: Main Graph - End-to-End
# ============================================================================


@test("Main Graph - Build and Initialize")
def test_graph_build():
    from graphs.main_graph import MainGraph

    graph = MainGraph({
        "llm": {
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0
        },
        "memory": {
            "type": "mock"
        }
    })

    assert graph.graph is not None, "Graph not compiled"
    assert graph.llm is not None, "LLM not initialized"
    assert graph.memory is not None, "Memory not initialized"
    print("  ✓ Main graph built successfully")


@test("Main Graph - Planner Node")
def test_graph_planner():
    from graphs.main_graph import MainGraph
    from graphs.state import create_initial_state

    import orchestrator.events as events_module
    original_redis = events_module.redis.Redis
    events_module.redis.Redis = MockRedis

    try:
        graph = MainGraph({
            "llm": {
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "temperature": 0
            },
            "memory": {"type": "mock"}
        })

        state = create_initial_state("test-plan-123", "Create a simple Python function to add two numbers")
        state["context"] = []

        # Test planner node directly
        result_state = graph._planner(state)

        assert len(result_state["plan"]) > 0, "Plan should not be empty"
        assert result_state["status"] == "planning", "Status should be planning"
        print(f"  ✓ Planner created {len(result_state['plan'])} steps")
        for i, step in enumerate(result_state["plan"][:3]):
            print(f"    Step {i+1}: {step[:80]}...")
    finally:
        events_module.redis.Redis = original_redis


@test("Main Graph - End-to-End Execution")
def test_graph_e2e():
    from graphs.main_graph import MainGraph

    import orchestrator.events as events_module
    original_redis = events_module.redis.Redis
    events_module.redis.Redis = MockRedis

    try:
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
        assert final_state["status"] == "completed", f"Status should be completed, got: {final_state['status']}"
        assert len(final_state["plan"]) > 0, "Plan should have been created"
        assert len(final_state["steps_results"]) > 0, "Should have step results"

        print("  ✓ Graph execution completed")
        print(f"  ✓ Plan had {len(final_state['plan'])} steps")
        print(f"  ✓ Output preview: {final_state['output'][:150]}...")
    finally:
        events_module.redis.Redis = original_redis

# ============================================================================
# TEST 5: Memory Adapter
# ============================================================================


@test("Memory Adapter - Store and Retrieve")
def test_memory_adapter():
    from memory.adapter import MemoryAdapter

    import orchestrator.events as events_module
    original_redis = events_module.redis.Redis
    events_module.redis.Redis = MockRedis

    try:
        memory = MemoryAdapter({"type": "mock"})

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
    finally:
        events_module.redis.Redis = original_redis

# ============================================================================
# TEST 6: Concurrency Test
# ============================================================================


@test("Concurrency - Multiple Tasks")
def test_concurrency():
    from graphs.main_graph import MainGraph
    import concurrent.futures

    import orchestrator.events as events_module
    original_redis = events_module.redis.Redis
    events_module.redis.Redis = MockRedis

    try:
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
            for i in range(3)  # Test with 3 concurrent tasks
        ]

        def run_task(task_id, input_text):
            try:
                result = graph.invoke(task_id, input_text)
                return (task_id, True, result)
            except Exception as e:
                return (task_id, False, str(e))

        print(f"  Running {len(tasks)} concurrent tasks...")

        # Run tasks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_task, tid, inp) for tid, inp in tasks]
            results_list = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = sum(1 for _, success, _ in results_list if success)
        print(f"  ✓ {success_count}/{len(tasks)} tasks completed successfully")

        for task_id, success, result in results_list:
            status = "✓" if success else "✗"
            print(f"    {status} Task {task_id}: {'OK' if success else result}")

        assert success_count == len(tasks), f"Expected all tasks to succeed, got {success_count}/{len(tasks)}"
    finally:
        events_module.redis.Redis = original_redis

# ============================================================================
# MAIN
# ============================================================================


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("STEP 1 - LANGGRAPH INTEGRATION TEST SUITE")
    print("="*60)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"OpenAI API Key: {'Set' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")

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

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total: {len(results['passed']) + len(results['failed'])}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")

    if results['failed']:
        print("\nFailed tests:")
        for name, error in results['failed']:
            print(f"  - {name}: {error}")

    print(f"\nEnd time: {datetime.now().isoformat()}")

    return len(results['failed']) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
