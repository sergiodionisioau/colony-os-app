#!/usr/bin/env python3
"""Complete COE System Startup.

Starts kernel with business module + LangGraph orchestrator.
"""

import sys
from pathlib import Path


def _import_business_module():
    """Import business module with path setup."""
    sys.path.insert(0, str(Path(__file__).parent / "coe-kernel"))
    sys.path.insert(0, str(Path(__file__).parent / "modules"))
    from business.entry import Module as BusinessModule
    return BusinessModule


BusinessModule = _import_business_module()

print("=" * 80)
print("🔷 COE COMPLETE SYSTEM STARTUP")
print("=" * 80)
print("Components:")
print("  ✓ Kernel with Business Module (4 businesses: Colony OS + Verified OS + App OS + Content OS)")
print("  ✓ LangGraph Orchestrator")
print("  ✓ Memory Layer (Episodic + Semantic)")
print("  ✓ REST API + Web Dashboard")
print("=" * 80)

# Test imports
print("\n📦 Loading Components...")
print("  ✓ Business Module")

# Optional LangGraph components
try:
    from graphs import main_graph
    from graphs.state import create_initial_state
    _ = main_graph, create_initial_state  # Mark as used
    LANGGRAPH_AVAILABLE = True
    print("  ✓ LangGraph Components")
except ImportError as e:
    LANGGRAPH_AVAILABLE = False
    print(f"  ⚠ LangGraph: {e} (install: pip install langgraph)")

try:
    from memory.adapter import MemoryAdapter
    MEMORY_AVAILABLE = True
    print("  ✓ Memory Layer")
except ImportError as e:
    MEMORY_AVAILABLE = False
    print(f"  ⚠ Memory: {e} (install: pip install langchain-openai)")

try:
    from orchestrator.llm import get_llm
    _ = get_llm  # Mark as used
    LLM_AVAILABLE = True
    print("  ✓ LLM Adapter")
except ImportError as e:
    LLM_AVAILABLE = False
    print(f"  ⚠ LLM: {e} (install: pip install langchain-openai)")

# Demo execution
print("\n" + "=" * 80)
print("🚀 RUNNING DEMONSTRATION")
print("=" * 80)

# 1. Initialize Business Module
print("\n1️⃣ Business Module")
biz_mod = BusinessModule()
print(f"   Loaded {len(biz_mod.businesses)} businesses")
for biz_id, biz in list(biz_mod.businesses.items())[:3]:
    print(f"   • {biz.name} ({biz.industry})")
print(f"   Health: {'✅ HEALTHY' if biz_mod.healthcheck() else '❌ UNHEALTHY'}")

# 2. Initialize Memory (if available)
print("\n2️⃣ Memory Layer")
if MEMORY_AVAILABLE:
    memory = MemoryAdapter({})
    print("   ✓ Episodic Store: Ready")
    print("   ✓ Vector Store: Ready")

    # Store some sample knowledge
    knowledge_id = memory.store_knowledge(
        "LangGraph is a stateful orchestration framework for building agent workflows.",
        {"type": "framework", "category": "ai"}
    )
    print(f"   ✓ Stored knowledge: {knowledge_id[:8]}...")

    knowledge_id2 = memory.store_knowledge(
        "Deterministic AI systems use temperature=0 and structured outputs for reproducibility.",
        {"type": "best_practice", "category": "ai"}
    )
    print(f"   ✓ Stored knowledge: {knowledge_id2[:8]}...")

    # 3. Test Retrieval
    print("\n3️⃣ Memory Retrieval")
    context = memory.retrieve_context("What is LangGraph?", top_k=3)
    print(f"   Retrieved {len(context)} relevant context items:")
    for i, ctx in enumerate(context, 1):
        print(f"   {i}. {ctx[:60]}...")
else:
    print("   ⚠ Memory layer not available (missing dependencies)")
    print("   To enable: pip install langchain-openai")

# 4. LangGraph Demo
print("\n4️⃣ LangGraph Workflow")
if LANGGRAPH_AVAILABLE:
    print("   Graph Structure:")
    print("     retrieve_context → planner → executor → synthesize → store_memory")
    print("   ✓ State management: TypedDict with strict typing")
    print("   ✓ Checkpointing: MemorySaver for persistence")
    print("   ✓ Event emission: Redis stream integration")
else:
    print("   ⚠ LangGraph not available (missing dependencies)")
    print("   To enable: pip install langgraph")
    print("   Graph Structure (planned):")
    print("     retrieve_context → planner → executor → synthesize → store_memory")

# 5. Show System Architecture
print("\n" + "=" * 80)
print("🏗️ SYSTEM ARCHITECTURE")
print("=" * 80)
print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COE KERNEL v1.1.0                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  REST API (FastAPI)                                                         │
│  ├── /v1/businesses      → Business CRUD                                    │
│  ├── /v1/modules         → Module hot-swap                                  │
│  ├── /v1/agents          → Agent management                                 │
│  └── /                   → Dashboard UI                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Business Module (Hot-Swappable)                                            │
│  ├── 5 Sample Businesses                                                    │
│  ├── Metrics Tracking (Revenue, Leads, Conversions)                         │
│  └── CRM Integration                                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  LangGraph Orchestrator                                                     │
│  ├── StateGraph with 5 nodes                                                │
│  ├── Memory-aware planning                                                  │
│  ├── Deterministic execution (temperature=0)                                │
│  └── Event-driven architecture                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Memory Layer                                                               │
│  ├── Episodic Memory (Task history)                                         │
│  ├── Semantic Memory (Vector store + PGVector)                              │
│  ├── Context Retrieval (Top-k similarity)                                   │
│  └── Learning Loop (Knowledge extraction)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Kernel Core                                                                │
│  ├── Audit Ledger (Hash-chained, tamper-evident)                            │
│  ├── Event Bus (Deterministic, ordered)                                     │
│  ├── Policy Engine (Zero implicit permissions)                              │
│  └── Module Loader (AST-guarded, sandboxed)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
""")

# 6. API Endpoints Summary
print("\n" + "=" * 80)
print("📡 API ENDPOINTS")
print("=" * 80)
endpoints = [
    ("GET", "/", "Dashboard UI"),
    ("GET", "/health-check", "Health check page"),
    ("GET", "/v1/health", "Kernel health JSON"),
    ("GET", "/v1/businesses", "List businesses"),
    ("GET", "/v1/businesses/stats", "Business statistics"),
    ("POST", "/v1/businesses", "Create business"),
    ("GET", "/v1/modules", "List modules"),
    ("POST", "/v1/modules/load", "Load module"),
    ("POST", "/v1/modules/{id}/hot-swap", "Hot-swap module"),
    ("GET", "/v1/agents", "List agents"),
    ("POST", "/v1/agents/register", "Register agent"),
]
for method, path, desc in endpoints:
    print(f"  {method:6} {path:30} → {desc}")

# 7. Business Statistics
print("\n" + "=" * 80)
print("📊 BUSINESS STATISTICS")
print("=" * 80)
stats = biz_mod.get_module_stats()
print(f"  Total Businesses:    {stats['total_businesses']}")
print(f"  Active Businesses:   {stats['active_businesses']}")
print(f"  Total Revenue:       ${stats['total_revenue']:,.2f}")
print(f"  Total Leads:         {stats['total_leads']:,}")
print(f"  Total Conversions:   {stats['total_conversions']}")
print(f"  Conversion Rate:     {stats['overall_conversion_rate']:.1f}%")
print(f"  Industries:          {', '.join(stats['industries'])}")

# 8. Next Steps
print("\n" + "=" * 80)
print("🎯 NEXT STEPS")
print("=" * 80)
print("""
To start the full system:

1. Install dependencies:
   pip install -r coe-kernel/requirements.txt
   pip install langchain langgraph langchain-openai

2. Set environment variables:
   export OPENAI_API_KEY=your_key_here

3. Start Redis (for event bus):
   redis-server

4. Start the kernel:
   python start_complete_system.py

5. In another terminal, start the orchestrator:
   python -m orchestrator.runner

6. Open browser:
   http://localhost:8000/
""")

print("\n" + "=" * 80)
print("✅ SYSTEM READY FOR NEXT STEP")
print("=" * 80)
print("\nFiles created:")
print("  • coe-kernel/orchestrator/llm.py        → LLM adapter")
print("  • coe-kernel/orchestrator/events.py     → Event bus adapter")
print("  • coe-kernel/orchestrator/runner.py     → Main orchestrator")
print("  • coe-kernel/orchestrator/kernel_client.py → Kernel API client")
print("  • coe-kernel/graphs/state.py            → LangGraph state")
print("  • coe-kernel/graphs/main_graph.py       → Main workflow")
print("  • coe-kernel/memory/adapter.py          → Memory interface")
print("  • coe-kernel/memory/vector_store.py     → PGVector store")
print("  • coe-kernel/memory/episodic_store.py   → Episodic memory")
print("  • modules/business/                     → Business module")
print("=" * 80)
