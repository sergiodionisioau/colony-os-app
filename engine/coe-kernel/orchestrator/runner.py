"""Orchestrator Runner.

Main entry point for LangGraph execution.
Connects to kernel event bus and processes tasks.
"""

import time
import json
import os
from typing import Any, Dict

from graphs.main_graph import build_graph
from orchestrator.events import EventBusAdapter
from graphs.state import AgentState


class OrchestratorRunner:
    """Main orchestrator that runs LangGraph workflows from kernel events."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize orchestrator."""
        self.config = config or {}
        self.graph = build_graph(self.config)
        self.event_bus = EventBusAdapter(self.config.get("events"))
        self.running = False

    def run(self) -> None:
        """Main loop - listen for events and process tasks."""
        print("=" * 70)
        print("🔷 COE LangGraph Orchestrator")
        print("=" * 70)
        print("Listening for tasks on event bus...")
        print("Press Ctrl+C to stop\n")

        self.running = True

        try:
            while self.running:
                # Listen for events
                events = self.event_bus.listen(block_ms=5000)

                for stream, messages in events:
                    for message_id, data in messages:
                        self._process_message(message_id, data)

        except KeyboardInterrupt:
            print("\n\nShutting down orchestrator...")
            self.running = False

    def _process_message(self, message_id: str, data: Dict[str, str]) -> None:
        """Process a single message from the event bus."""
        event_type = data.get("type")

        if event_type == "task.created":
            # Parse task data
            try:
                task_data = json.loads(data.get("data", "{}"))
                self._execute_task(task_data)

                # Acknowledge message
                self.event_bus.ack(message_id)

            except json.JSONDecodeError as e:
                print(f"Failed to parse task data: {e}")

        elif event_type == "orchestrator.stop":
            print("Received stop signal")
            self.running = False

    def _execute_task(self, task_data: Dict[str, Any]) -> None:
        """Execute a task using LangGraph."""
        task_id = task_data.get("task_id", str(int(time.time())))
        input_text = task_data.get("input", "")

        print(f"\n📝 Task {task_id}: {input_text[:60]}...")
        print("-" * 70)

        start_time = time.time()

        try:
            # Execute graph
            final_state = self.graph.invoke(task_id, input_text)

            execution_time = (time.time() - start_time) * 1000

            # Print results
            print(f"\n✅ Task completed in {execution_time:.0f}ms")
            print(f"   Status: {final_state['status']}")
            print(f"   Steps: {len(final_state['plan'])}")
            print(f"   Memory IDs: {final_state['memory_ids']}")
            print("\n📤 Output:")
            print(f"   {final_state['output'][:200]}...")

        except Exception as e:
            print(f"\n❌ Task failed: {e}")
            import traceback
            traceback.print_exc()

    def execute_task_sync(self, task_id: str, input_text: str) -> AgentState:
        """Execute a task synchronously (for testing)."""
        return self.graph.invoke(task_id, input_text)


def run() -> None:
    """Entry point for orchestrator."""
    import yaml

    # Load config
    config_path = "config.yaml"
    config = {}

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

    # Create and run orchestrator
    orchestrator = OrchestratorRunner(config)
    orchestrator.run()


if __name__ == "__main__":
    run()
