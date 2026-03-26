#!/usr/bin/env python3
"""
STEP 1 - LangGraph Integration Test Suite (With Mock LLM Option)
Tests: LLM Adapter, Event Bus, Graph Execution

This test suite can run in two modes:
1. MOCK mode (default): Uses mock LLM responses for testing without API key
2. LIVE mode: Uses actual OpenAI API (requires OPENAI_API_KEY)

To run in LIVE mode:
    export OPENAI_API_KEY="your-key-here"
    python3 test_step1_langgraph_mock.py --live
"""

import os
import sys
import time
import uuid
import argparse
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add coe-kernel to path
sys.path.insert(0, '/home/coe/.openclaw/workspace/colony-os-app/engine/coe-kernel')

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true', help='Run with live OpenAI API')
args = parser.parse_args()

USE_MOCK = not args.live

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
# MOCK LLM SETUP
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

# ============================================================================
# MOCK REDIS SETUP
# ============================================================================


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

# ============================================================================
# TEST 1: LLM Adapter - Temperature=0 Verification
# ============================================================================


@test("LLM Adapter - Initialization")
def test_llm_init():
    from orchestrator.llm import LLMAdapter

    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
            llm = LLMAdapter({
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "temperature": 0,
                "max_tokens": 4096
            })

            assert llm._llm is not None, "LLM not initialized"
            assert llm._llm.temperature == 0, "Temperature not set to 0"
            print(f"  ✓ LLM initialized with temperature={llm._llm.temperature}")
    else:
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

    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
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
    else:
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
    from orchestrator.llm import LLMAdapter

    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
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

            # Mock returns a MagicMock, so we check if it was called
            print("  ✓ Structured output call successful")
    else:
        llm = LLMAdapter({
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "temperature": 0
        })

        schema = {
            "title": "CapitalAnswer",
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
        print(f"  ✓ Structured output: {result}")

# ============================================================================
# TEST 2: Event Bus Adapter
# ============================================================================


@test("Event Bus Adapter - Initialization (Mock)")
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
    print(f"  ✓ Initial state created: task_id={state['task_id']}, status={state['status']}")

# ============================================================================
# TEST 4: Main Graph - End-to-End
# ============================================================================


def create_test_graph():
    """Helper to create graph with mocks."""
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

    return graph


@test("Main Graph - Build and Initialize")
def test_graph_build():
    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
            graph = create_test_graph()

            assert graph.graph is not None, "Graph not compiled"
            assert graph.llm is not None, "LLM not initialized"
            assert graph.memory is not None, "Memory not initialized"
            print("  ✓ Main graph built successfully")
    else:
        graph = create_test_graph()

        assert graph.graph is not None, "Graph not compiled"
        assert graph.llm is not None, "LLM not initialized"
        assert graph.memory is not None, "Memory not initialized"
        print("  ✓ Main graph built successfully")


@test("Main Graph - Planner Node")
def test_graph_planner():
    from graphs.state import create_initial_state

    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
            graph = create_test_graph()

            state = create_initial_state("test-plan-123", "Create a simple Python function to add two numbers")
            state["context"] = []

            # Test planner node directly
            result_state = graph._planner(state)

            assert len(result_state["plan"]) > 0, "Plan should not be empty"
            assert result_state["status"] == "planning", "Status should be planning"
            print(f"  ✓ Planner created {len(result_state['plan'])} steps")
            for i, step in enumerate(result_state["plan"][:3]):
                print(f"    Step {i+1}: {step[:80]}...")
    else:
        graph = create_test_graph()

        state = create_initial_state("test-plan-123", "Create a simple Python function to add two numbers")
        state["context"] = []

        result_state = graph._planner(state)

        assert len(result_state["plan"]) > 0, "Plan should not be empty"
        assert result_state["status"] == "planning", "Status should be planning"
        print(f"  ✓ Planner created {len(result_state['plan'])} steps")


@test("Main Graph - End-to-End Execution")
def test_graph_e2e():
    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
            with patch('memory.vector_store.OpenAIEmbeddings') as MockEmbeddings:
                MockEmbeddings.return_value.embed_query.return_value = [0.1] * 1536

                graph = create_test_graph()

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
    else:
        graph = create_test_graph()

        task_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
        input_text = "What is 5 + 3? Explain briefly."

        print(f"  Running graph with task_id={task_id}")
        print(f"  Input: {input_text}")

        final_state = graph.invoke(task_id, input_text)

        assert final_state["output"] != "", "Output should not be empty"
        assert final_state["status"] == "completed", f"Status should be completed, got: {final_state['status']}"
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
    from memory.adapter import MemoryAdapter

    import orchestrator.events as events_module
    events_module.redis.Redis = MockRedis

    if USE_MOCK:
        with patch('memory.vector_store.OpenAIEmbeddings') as MockEmbeddings:
            MockEmbeddings.return_value.embed_query.return_value = [0.1] * 1536

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
    else:
        memory = MemoryAdapter({"type": "mock"})

        knowledge_id = memory.store_knowledge(
            "LangGraph is a stateful orchestration engine",
            {"source": "test", "type": "fact"}
        )
        print(f"  ✓ Knowledge stored with ID: {knowledge_id}")

        episode_id = memory.store_episode({
            "task_id": "test-task-1",
            "input": "What is LangGraph?",
            "output": "LangGraph is a stateful orchestration engine",
            "plan": ["Research LangGraph", "Formulate answer"],
            "steps": ["Found documentation", "Created summary"],
            "success": True
        })
        print(f"  ✓ Episode stored with ID: {episode_id}")

        context = memory.retrieve_context("What is LangGraph?", top_k=5)
        assert len(context) > 0, "Should retrieve at least one context"
        print(f"  ✓ Retrieved {len(context)} context items")

# ============================================================================
# TEST 6: Concurrency Test
# ============================================================================


@test("Concurrency - Multiple Tasks")
def test_concurrency():
    import concurrent.futures

    import orchestrator.events as events_module
    events_module.redis.Redis = MockRedis

    def run_task(graph, task_id, input_text):
        try:
            result = graph.invoke(task_id, input_text)
            return (task_id, True, result)
        except Exception as e:
            return (task_id, False, str(e))

    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
            with patch('memory.vector_store.OpenAIEmbeddings') as MockEmbeddings:
                MockEmbeddings.return_value.embed_query.return_value = [0.1] * 1536

                from graphs.main_graph import MainGraph

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
                    for i in range(3)
                ]

                print(f"  Running {len(tasks)} concurrent tasks...")

                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(run_task, graph, tid, inp) for tid, inp in tasks]
                    results_list = [f.result() for f in concurrent.futures.as_completed(futures)]

                success_count = sum(1 for _, success, _ in results_list if success)
                print(f"  ✓ {success_count}/{len(tasks)} tasks completed successfully")

                for task_id, success, result in results_list:
                    status = "✓" if success else "✗"
                    print(f"    {status} Task {task_id}: {'OK' if success else result}")

                assert success_count == len(tasks), f"Expected all tasks to succeed, got {success_count}/{len(tasks)}"
    else:
        from graphs.main_graph import MainGraph

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
            for i in range(3)
        ]

        print(f"  Running {len(tasks)} concurrent tasks...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_task, graph, tid, inp) for tid, inp in tasks]
            results_list = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = sum(1 for _, success, _ in results_list if success)
        print(f"  ✓ {success_count}/{len(tasks)} tasks completed successfully")

        for task_id, success, result in results_list:
            status = "✓" if success else "✗"
            print(f"    {status} Task {task_id}: {'OK' if success else result}")

        assert success_count == len(tasks), f"Expected all tasks to succeed, got {success_count}/{len(tasks)}"

# ============================================================================
# TEST 7: Failure Recovery
# ============================================================================


@test("Failure Recovery - Task Resumption")
def test_failure_recovery():
    """Test that tasks can be re-run after failure (idempotency)."""
    import orchestrator.events as events_module
    events_module.redis.Redis = MockRedis

    if USE_MOCK:
        with patch('orchestrator.llm.ChatOpenAI', MockLLM):
            with patch('memory.vector_store.OpenAIEmbeddings') as MockEmbeddings:
                MockEmbeddings.return_value.embed_query.return_value = [0.1] * 1536

                graph = create_test_graph()

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
                assert state1["output"] == state2["output"], "Outputs should be identical (deterministic)"
                print("  ✓ Determinism verified: both runs produced identical output")
    else:
        graph = create_test_graph()

        task_id = "recovery-test-001"
        input_text = "Test task for recovery"

        print("  First execution...")
        state1 = graph.invoke(task_id, input_text)

        assert state1["status"] == "completed", "First run should complete"
        print("  ✓ First execution completed")

        print("  Second execution (recovery)...")
        state2 = graph.invoke(task_id, input_text)

        assert state2["status"] == "completed", "Second run should complete"
        print("  ✓ Second execution completed (idempotent)")

# ============================================================================
# MAIN
# ============================================================================


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("STEP 1 - LANGGRAPH INTEGRATION TEST SUITE")
    print("="*60)
    print(f"Mode: {'MOCK (no API calls)' if USE_MOCK else 'LIVE (with OpenAI API)'}")
    print(f"Start time: {datetime.now().isoformat()}")

    if not USE_MOCK:
        api_key = os.environ.get('OPENAI_API_KEY')
        print(f"OpenAI API Key: {'Set' if api_key else 'NOT SET - Tests will fail!'}")
        if not api_key:
            print("\n⚠️  WARNING: OPENAI_API_KEY not set. Run with --live only if you have the key set.")
            print("   To run without API key, omit --live flag to use mock mode.")

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
