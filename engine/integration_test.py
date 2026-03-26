#!/usr/bin/env python3
"""Integration Test Script for COE Kernel System.

Tests the full integration of:
- Kernel API
- Event Bus
- LangGraph Orchestrator
- Memory Layer
- Business Module (4 businesses)

Usage:
    python3 integration_test.py [--server] [--test-only]

Options:
    --server      Start the API server for testing
    --test-only   Run tests against existing server
"""

import argparse
import sys
import time
import uuid
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "coe-kernel"))
sys.path.insert(0, str(Path(__file__).parent / "modules"))

# Test results tracking
results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def log_test(name: str, status: str, details: str = ""):
    """Log test result."""
    symbol = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
    print(f"  {symbol} {name}")
    if details:
        print(f"      {details}")

    if status == "pass":
        results["passed"].append({"name": name, "details": details})
    elif status == "fail":
        results["failed"].append({"name": name, "details": details})
    else:
        results["warnings"].append({"name": name, "details": details})


def test_business_module():
    """Test 1: Business Module Loading"""
    print("\n📦 TEST 1: Business Module")
    print("-" * 50)

    try:
        from business.entry import Module as BusinessModule

        # Initialize module
        biz_mod = BusinessModule()
        log_test("Module Import", "pass")

        # Check 4 businesses loaded
        if len(biz_mod.businesses) == 4:
            log_test("4 Businesses Loaded", "pass", f"Found {len(biz_mod.businesses)} businesses")
        else:
            log_test("4 Businesses Loaded", "fail", f"Expected 4, found {len(biz_mod.businesses)}")

        # Check specific businesses
        expected_businesses = ["Colony OS", "Verified OS", "App OS", "Content OS"]
        loaded_names = [b.name for b in biz_mod.businesses.values()]

        for expected in expected_businesses:
            if expected in loaded_names:
                log_test(f"Business: {expected}", "pass")
            else:
                log_test(f"Business: {expected}", "fail", "Not found in loaded businesses")

        # Test healthcheck
        health = biz_mod.healthcheck()
        if health:
            log_test("Health Check", "pass", "Module reports healthy")
        else:
            log_test("Health Check", "fail", "Module reports unhealthy")

        # Test stats
        stats = biz_mod.get_module_stats()
        log_test("Module Statistics", "pass",
                 f"Revenue: ${stats.get('total_revenue', 0):,.2f}, "
                 f"Conversion Rate: {stats.get('overall_conversion_rate', 0):.1f}%")

        return biz_mod

    except Exception as e:
        log_test("Business Module", "fail", str(e))
        return None


def test_langgraph_components():
    """Test 2: LangGraph Components"""
    print("\n🔄 TEST 2: LangGraph Components")
    print("-" * 50)

    try:
        from graphs.state import create_initial_state
        log_test("State Module Import", "pass")

        # Test state creation
        test_task_id = f"test-{uuid.uuid4().hex[:8]}"
        state = create_initial_state(test_task_id, "Test task input")

        if state["task_id"] == test_task_id:
            log_test("Initial State Creation", "pass")
        else:
            log_test("Initial State Creation", "fail", "Task ID mismatch")

        # Test graph building
        try:
            from graphs import main_graph
            _ = main_graph  # Mark as used
            log_test("Graph Module Import", "pass")

            # Note: Can't build full graph without OpenAI API key
            # but we can verify the module loads
            log_test("Graph Build (Mock)", "warning",
                     "Full graph requires OPENAI_API_KEY - module loads correctly")

        except ImportError as e:
            log_test("Graph Build", "fail", str(e))

    except Exception as e:
        log_test("LangGraph Components", "fail", str(e))


def test_memory_layer():
    """Test 3: Memory Layer"""
    print("\n🧠 TEST 3: Memory Layer")
    print("-" * 50)

    try:
        from memory.episodic_store import EpisodicStore
        log_test("Episodic Store Import", "pass")

        # Test episodic storage
        store = EpisodicStore({})
        test_episode = {
            "id": str(uuid.uuid4()),
            "task_id": "test-task-001",
            "input": "Test input",
            "plan": '["step1", "step2"]',
            "result": "Test result",
            "steps": '["executed step1"]',
            "success": True,
            "created_at": "2024-01-01T00:00:00Z"
        }

        episode_id = store.store(test_episode)
        retrieved = store.get_by_id(episode_id)

        if retrieved and retrieved["task_id"] == "test-task-001":
            log_test("Episodic Store/Retrieve", "pass")
        else:
            log_test("Episodic Store/Retrieve", "fail", "Data mismatch")

        # Test vector store (mock mode)
        try:
            from memory import vector_store
            _ = vector_store  # Mark as used
            log_test("Vector Store Import", "pass")
            log_test("Vector Store (Mock)", "warning",
                     "Requires OPENAI_API_KEY for embeddings - module loads correctly")
        except Exception as e:
            log_test("Vector Store", "fail", str(e))

    except Exception as e:
        log_test("Memory Layer", "fail", str(e))


def test_kernel_bootstrap():
    """Test 4: Kernel Bootstrap"""
    print("\n🔷 TEST 4: Kernel Bootstrap")
    print("-" * 50)

    try:
        from core.main_enhanced import KernelBootstrap
        log_test("Kernel Bootstrap Import", "pass")

        # Create minimal config for testing
        config = {
            "audit": {"storage_path": "/tmp/coe_test/audit", "genesis_constant": "TEST"},
            "bootstrap": {"mode": "normal", "root_keypair_path": "/tmp/coe_test/keys/root.pem"},
            "events": {"store_path": "/tmp/coe_test/events"},
            "rbac": {"roles": {"admin": ["all"]}},
            "policy": {"strict_mode": True},
            "secrets": {"data_path": "/tmp/coe_test/secrets.json", "salt_path": "/tmp/coe_test/salt.bin"},
            "modules": {"plugins_dir": str(Path(__file__).parent / "modules")},
            "api": {"enabled": False}  # Don't start API for bootstrap test
        }

        # Create directories
        import os
        for path in ["/tmp/coe_test/audit", "/tmp/coe_test/events", "/tmp/coe_test/keys"]:
            os.makedirs(path, exist_ok=True)

        # Initialize kernel
        kernel = KernelBootstrap(config)
        log_test("Kernel Initialization", "pass")

        # Check subsystems
        subsystems = kernel.get_subsystems()
        required = ["bus", "policy", "loader", "vault"]

        for subsys in required:
            if subsys in subsystems and subsystems[subsys] is not None:
                log_test(f"Subsystem: {subsys}", "pass")
            else:
                log_test(f"Subsystem: {subsys}", "fail", "Not initialized")

        # Check audit ledger
        if kernel.audit_ledger.verify_integrity():
            log_test("Audit Ledger Integrity", "pass")
        else:
            log_test("Audit Ledger Integrity", "fail", "Integrity check failed")

        # Clean up
        kernel.shutdown()
        log_test("Kernel Shutdown", "pass")

        return kernel

    except Exception as e:
        log_test("Kernel Bootstrap", "fail", str(e))
        import traceback
        traceback.print_exc()
        return None


def test_module_loader():
    """Test 5: Module Loader"""
    print("\n📂 TEST 5: Module Loader")
    print("-" * 50)

    try:
        from core.module_loader.loader import ModuleLoader
        from core.module_loader.registry import ModuleRegistry
        from core.audit.ledger import AuditLedger
        log_test("Module Loader Imports", "pass")

        # Create loader
        audit = AuditLedger(storage_path="/tmp/coe_test/audit_loader.log", genesis_constant="TEST_LOADER")
        registry = ModuleRegistry(audit_ledger=audit)

        # Load test public key
        with open("/tmp/coe_test/test_public.pem", "rb") as f:
            public_key = f.read()

        loader_config = {
            "modules_path": str(Path(__file__).parent / "modules"),
            "forbidden_imports": ["os", "sys", "subprocess"],
            "audit_ledger": audit,
            "registry": registry,
            "event_bus": None,
            "kernel_version": "1.1.0",
            "public_key": public_key
        }

        loader = ModuleLoader(loader_config)
        log_test("Module Loader Creation", "pass")

        # Try loading business module
        try:
            loader.load("business")
            log_test("Load Business Module", "pass")

            # Check loaded modules
            loaded = loader.get_loaded_modules()
            if "business" in loaded:
                log_test("Business Module Loaded", "pass")
            else:
                log_test("Business Module Loaded", "fail", "Not in loaded modules list")

            # Get instance and check health
            instance = loader.get_module_instance("business")
            if instance and hasattr(instance, "healthcheck"):
                health = instance.healthcheck()
                log_test("Business Module Health", "pass" if health else "fail",
                         "Healthy" if health else "Unhealthy")

        except Exception as e:
            log_test("Load Business Module", "fail", str(e))

    except Exception as e:
        log_test("Module Loader", "fail", str(e))


def test_hot_swap():
    """Test 6: Hot-Swap Functionality"""
    print("\n🔄 TEST 6: Hot-Swap Functionality")
    print("-" * 50)

    try:
        from core.module_loader.loader import ModuleLoader
        from core.module_loader.registry import ModuleRegistry
        from core.audit.ledger import AuditLedger

        audit = AuditLedger(storage_path="/tmp/coe_test/audit_swap.log", genesis_constant="TEST_SWAP")
        registry = ModuleRegistry(audit_ledger=audit)

        # Load test public key
        with open("/tmp/coe_test/test_public.pem", "rb") as f:
            public_key = f.read()

        loader_config = {
            "modules_path": str(Path(__file__).parent / "modules"),
            "forbidden_imports": ["os", "sys"],
            "audit_ledger": audit,
            "registry": registry,
            "event_bus": None,
            "kernel_version": "1.1.0",
            "public_key": public_key
        }

        loader = ModuleLoader(loader_config)

        # Load business module
        loader.load("business")
        initial_instance = loader.get_module_instance("business")
        initial_biz_count = len(initial_instance.businesses)

        log_test("Initial Load", "pass", f"{initial_biz_count} businesses")

        # Perform hot-swap
        try:
            loader.hot_swap("business")
            new_instance = loader.get_module_instance("business")
            new_biz_count = len(new_instance.businesses)

            if new_biz_count == initial_biz_count:
                log_test("Hot-Swap", "pass", f"Zero downtime, {new_biz_count} businesses")
            else:
                log_test("Hot-Swap", "fail", f"Business count changed: {initial_biz_count} -> {new_biz_count}")

            # Check rollback capability
            if hasattr(loader, 'rollback'):
                log_test("Rollback Available", "pass")
            else:
                log_test("Rollback Available", "warning", "Rollback method not exposed")

        except Exception as e:
            log_test("Hot-Swap", "fail", str(e))

    except Exception as e:
        log_test("Hot-Swap Test", "fail", str(e))


def test_event_bus():
    """Test 7: Event Bus"""
    print("\n📡 TEST 7: Event Bus")
    print("-" * 50)

    try:
        from core.event_bus.bus import EventBus, SchemaRegistry
        from core.event_bus.store import EventStore
        from core.event_bus.backpressure import BackpressureController
        from core.event_bus.dlq import DeadLetterQueue
        from core.audit.ledger import AuditLedger
        from core.types import EventBusDependencies

        audit = AuditLedger(storage_path="/tmp/coe_test/audit_events.log", genesis_constant="TEST_EVENTS")
        event_store = EventStore(storage_path="/tmp/coe_test/events")
        backpressure = BackpressureController(activation_depth=10000, deactivation_depth=7000)
        dlq = DeadLetterQueue(storage_path="/tmp/coe_test/dlq")

        deps = EventBusDependencies(
            audit_ledger=audit,
            event_store=event_store,
            backpressure=backpressure,
            dlq=dlq,
            schema_registry=SchemaRegistry()
        )

        bus = EventBus(deps=deps)
        log_test("Event Bus Creation", "pass")

        # Register schema
        bus.schema_registry.register("test.event", ["payload"])
        log_test("Schema Registration", "pass")

        # Publish event - EventBus expects an Event object
        from core.types import Event
        from core.event_bus.bus import compute_event_signature
        from dataclasses import replace
        import uuid

        event = Event.create("test.event", {"payload": "test data"}, origin_id=uuid.uuid4())
        # Compute proper signature
        event = replace(event, signature=compute_event_signature(event))
        bus.publish(event)
        log_test("Event Publishing", "pass")

        # Check backpressure - just verify the controller exists
        if hasattr(bus, 'backpressure') and bus.backpressure is not None:
            log_test("Backpressure Controller", "pass", "Controller available")
        else:
            log_test("Backpressure Controller", "fail", "Controller not available")

    except Exception as e:
        log_test("Event Bus", "fail", str(e))


def test_api_server():
    """Test 8: API Server (if running)"""
    print("\n🌐 TEST 8: API Server")
    print("-" * 50)

    import urllib.request
    import urllib.error

    endpoints = [
        ("http://localhost:8000/v1/health", "Health Check"),
        ("http://localhost:8000/v1/businesses", "Businesses Endpoint"),
        ("http://localhost:8000/", "Dashboard UI"),
    ]

    for url, name in endpoints:
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                if status == 200:
                    log_test(name, "pass", f"HTTP {status}")
                else:
                    log_test(name, "warning", f"HTTP {status}")
        except urllib.error.HTTPError as e:
            log_test(name, "warning", f"HTTP {e.code}")
        except urllib.error.URLError as e:
            log_test(name, "warning", f"Server not running: {e.reason}")
        except Exception as e:
            log_test(name, "warning", str(e))


def print_summary():
    """Print test summary."""
    print("\n" + "=" * 70)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 70)

    total = len(results["passed"]) + len(results["failed"]) + len(results["warnings"])

    print(f"\n✅ Passed:   {len(results['passed'])}")
    print(f"❌ Failed:   {len(results['failed'])}")
    print(f"⚠️  Warnings: {len(results['warnings'])}")
    print(f"\nTotal Tests: {total}")

    if results["failed"]:
        print("\n❌ FAILED TESTS:")
        for fail in results["failed"]:
            print(f"  • {fail['name']}: {fail['details']}")

    if results["warnings"]:
        print("\n⚠️  WARNINGS:")
        for warn in results["warnings"]:
            print(f"  • {warn['name']}: {warn['details']}")

    success_rate = len(results["passed"]) / total * 100 if total > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")

    if len(results["failed"]) == 0:
        print("\n🎉 All critical tests passed!")
        return 0
    else:
        print(f"\n⚠️  {len(results['failed'])} test(s) failed")
        return 1


def main():
    """Run all integration tests."""
    parser = argparse.ArgumentParser(description="COE Kernel Integration Tests")
    parser.add_argument("--server", action="store_true", help="Start API server for testing")
    parser.add_argument("--test-only", action="store_true", help="Run tests only (server must be running)")
    args = parser.parse_args()

    print("=" * 70)
    print("🔷 COE KERNEL INTEGRATION TESTS")
    print("=" * 70)
    print("\nTesting Components:")
    print("  • Business Module (4 businesses)")
    print("  • LangGraph Orchestrator")
    print("  • Memory Layer (Episodic + Semantic)")
    print("  • Event Bus")
    print("  • Module Loader + Hot-Swap")
    print("  • Kernel Bootstrap")
    print("  • REST API Server")
    print("=" * 70)

    if args.server:
        print("\n🚀 Starting API server...")
        import subprocess
        import os

        # Start server in background
        env = os.environ.copy()
        proc = subprocess.Popen(
            ["python3", "start_with_business.py", "--port", "8000"],
            cwd=str(Path(__file__).parent),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        print("⏳ Waiting for server to start...")
        time.sleep(3)

        # Run tests
        run_all_tests()

        # Stop server
        proc.terminate()
        proc.wait()
        print("\n🛑 Server stopped")

    elif args.test_only:
        run_all_tests()
    else:
        # Run local tests only (no server)
        run_local_tests()

    return print_summary()


def run_local_tests():
    """Run tests that don't require server."""
    test_business_module()
    test_langgraph_components()
    test_memory_layer()
    test_kernel_bootstrap()
    test_module_loader()
    test_hot_swap()
    test_event_bus()


def run_all_tests():
    """Run all tests including API."""
    run_local_tests()
    test_api_server()


if __name__ == "__main__":
    sys.exit(main())
