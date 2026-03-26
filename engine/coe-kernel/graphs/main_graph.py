"""Main LangGraph Definition.

Deterministic workflow orchestration with memory integration.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Any, Dict

from graphs.state import AgentState, create_initial_state
from orchestrator.llm import get_llm
from orchestrator.events import emit
from memory.adapter import MemoryAdapter


class MainGraph:
    """Main LangGraph workflow definition."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize graph with configuration."""
        self.config = config or {}
        self.llm = get_llm(self.config.get("llm"))
        self.memory = MemoryAdapter(self.config.get("memory"))
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Define state graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("planner", self._planner)
        workflow.add_node("executor", self._executor)
        workflow.add_node("synthesize", self._synthesize)
        workflow.add_node("store_memory", self._store_memory)

        # Define edges
        workflow.set_entry_point("retrieve_context")
        workflow.add_edge("retrieve_context", "planner")
        workflow.add_edge("planner", "executor")
        workflow.add_edge("executor", "synthesize")
        workflow.add_edge("synthesize", "store_memory")
        workflow.add_edge("store_memory", END)

        # Compile with checkpointing
        return workflow.compile(checkpointer=MemorySaver())

    def _retrieve_context(self, state: AgentState) -> AgentState:
        """Retrieve relevant context from memory."""
        state["status"] = "retrieving_context"

        # Query memory for relevant context
        context = self.memory.retrieve_context(state["input"], top_k=5)
        state["context"] = context

        # Emit event
        emit("memory.retrieved", {
            "task_id": state["task_id"],
            "context_count": len(context)
        })

        return state

    def _planner(self, state: AgentState) -> AgentState:
        """Create execution plan with context."""
        state["status"] = "planning"

        # Build prompt with context
        context_str = "\n".join(state["context"]) if state["context"] else "No relevant context found."

        prompt = f"""You are a deterministic task planner. Break the following task into clear, executable steps.

RELEVANT CONTEXT FROM MEMORY:
{context_str}

TASK:
{state['input']}

Create a step-by-step plan. Each step should be atomic and actionable.
Return ONLY the plan as a numbered list, one step per line."""

        response = self.llm.invoke(prompt)

        # Parse plan
        plan = [line.strip() for line in response.split("\n") if line.strip() and line[0].isdigit()]
        state["plan"] = plan

        # Emit event
        emit("plan.created", {
            "task_id": state["task_id"],
            "plan": plan,
            "step_count": len(plan)
        })

        return state

    def _executor(self, state: AgentState) -> AgentState:
        """Execute each step of the plan."""
        state["status"] = "executing"

        results = []
        for i, step in enumerate(state["plan"]):
            state["current_step"] = i + 1

            # Execute step
            step_prompt = f"""Execute this step from a larger task:

ORIGINAL TASK: {state['input']}

CURRENT STEP ({i+1}/{len(state['plan'])}): {step}

Execute this step and provide the result."""

            step_result = self.llm.invoke(step_prompt)
            results.append(step_result)

            # Emit progress event
            emit("step.completed", {
                "task_id": state["task_id"],
                "step_number": i + 1,
                "total_steps": len(state["plan"])
            })

        state["steps_results"] = results
        return state

    def _synthesize(self, state: AgentState) -> AgentState:
        """Synthesize final output from step results."""
        state["status"] = "synthesizing"

        # Combine all step results
        results_str = "\n\n".join([
            f"Step {i+1}:\n{result}"
            for i, result in enumerate(state["steps_results"])
        ])

        prompt = f"""Synthesize the following step results into a coherent final output.

ORIGINAL TASK: {state['input']}

STEP RESULTS:
{results_str}

Provide a clear, comprehensive final answer."""

        final_output = self.llm.invoke(prompt)
        state["output"] = final_output

        return state

    def _store_memory(self, state: AgentState) -> AgentState:
        """Store task execution in memory."""
        state["status"] = "completed"

        # Store episodic memory
        episode_id = self.memory.store_episode({
            "task_id": state["task_id"],
            "input": state["input"],
            "plan": state["plan"],
            "output": state["output"],
            "steps": state["steps_results"],
            "success": state["error"] is None
        })

        # Extract and store semantic knowledge
        summary_prompt = f"""Summarize the key learnings from this task execution:

Task: {state['input']}
Output: {state['output']}

Provide a concise summary of what was learned that could be useful for future tasks."""

        summary = self.llm.invoke(summary_prompt)
        knowledge_id = self.memory.store_knowledge(
            content=summary,
            metadata={
                "source": "task_execution",
                "task_id": state["task_id"],
                "type": "learning"
            }
        )

        state["memory_ids"] = [episode_id, knowledge_id]

        # Emit completion event
        emit("task.completed", {
            "task_id": state["task_id"],
            "status": "success",
            "output_preview": state["output"][:200],
            "memory_ids": state["memory_ids"]
        })

        return state

    def invoke(self, task_id: str, input_text: str) -> AgentState:
        """Execute graph with initial state."""
        initial_state = create_initial_state(task_id, input_text)

        # Run graph
        final_state = self.graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": task_id}}
        )

        return final_state


def build_graph(config: Dict[str, Any] = None) -> MainGraph:
    """Factory function to build graph."""
    return MainGraph(config)
