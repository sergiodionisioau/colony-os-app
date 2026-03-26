"""Knowledge Graph Tools.

Tools for querying the Knowledge Graph using Cypher.
"""

import os
import time
from typing import Any, Dict

from tools.schemas import KgQueryInput, ToolOutput, ToolStatus


def get_kg_config() -> Dict[str, str]:
    """Get Knowledge Graph configuration from environment."""
    return {
        "uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.environ.get("NEO4J_USER", "neo4j"),
        "password": os.environ.get("NEO4J_PASSWORD", "password"),
    }


async def kg_query(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Execute a Cypher query against the Knowledge Graph.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    start_time = time.time()

    try:
        # Validate input
        input_data = KgQueryInput(**parameters)

        # Try to use Neo4j if available
        try:
            from neo4j import GraphDatabase

            config = get_kg_config()
            driver = GraphDatabase.driver(
                config["uri"], auth=(config["user"], config["password"])
            )

            with driver.session() as session:
                result = session.run(input_data.cypher, input_data.parameters or {})
                records = [dict(record) for record in result]

            driver.close()

        except Exception:
            # Fallback to mock results for testing
            records = [
                {
                    "mock": True,
                    "message": "Neo4j not available, returning mock data",
                    "query_preview": (
                        input_data.cypher[:100] if input_data.cypher else ""
                    ),
                }
            ]

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="kg_query",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={"records": records, "count": len(records)},
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="kg_query",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )
