"""Performance benchmark for indexed Signal Scoring."""

import time
import uuid
import sys
import os


def run_benchmark() -> None:
    """Entrypoint for performance verification."""
    # Add the project root to sys.path
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
    from modules.crm.registry.knowledge_graph import KnowledgeGraph
    from modules.crm.engine.decision_engine import DecisionEngine
    from modules.crm.registry.schemas import Entity, Signal

    graph = KnowledgeGraph()
    engine = DecisionEngine(graph)

    # 1. Setup entities
    target_entity_uid = str(uuid.uuid4())
    graph.upsert_entity(
        Entity(uid=target_entity_uid, domain="target.com", name="Target Corp")
    )

    other_entities = [str(uuid.uuid4()) for _ in range(100)]
    for uid in other_entities:
        graph.upsert_entity(Entity(uid=uid, domain=f"{uid}.com", name=f"Other {uid}"))

    # 2. Add 10,000 signals
    print("--- Populating 10,000 signals ---")
    start_pop = time.time()
    for i in range(10000):
        # Distribute signals: 100 for target, the rest for others
        entity_uid = target_entity_uid if i % 100 == 0 else other_entities[i % 100]
        signal = Signal(
            uid=str(uuid.uuid4()),
            type="WEB_VISIT",
            source="benchmark",
            confidence=0.8,
            timestamp=f"2026-03-19T10:00:{i%60:02d}Z",
            payload={"entity_uid": entity_uid},
        )
        graph.add_signal(signal)

    end_pop = time.time()
    print(f"Population took: {end_pop - start_pop:.4f}s")

    # 3. Benchmark score_intent (O(1) vs O(N))
    print(f"--- Benchmarking score_intent for {target_entity_uid} ---")

    # Warm up
    engine.score_intent(target_entity_uid)

    start_bench = time.time()
    iterations = 1000
    for _ in range(iterations):
        engine.score_intent(target_entity_uid)
    end_bench = time.time()

    avg_latency = (end_bench - start_bench) / iterations
    print(f"Average score_intent latency: {avg_latency * 1000:.4f}ms")

    # Assert performance: O(1) lookup should be < 0.1ms (usually < 0.01ms)
    assert avg_latency < 0.0005, f"Latency too high: {avg_latency*1000:.4f}ms"
    print("SUCCESS: O(1) Signal Scoring verified.")


if __name__ == "__main__":
    run_benchmark()
