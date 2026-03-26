"""PostgreSQL Database Tools.

Read-only database query tools with write protection.
"""

import os
import time
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from tools.schemas import DbQueryInput, ToolOutput, ToolStatus


def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment."""
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
        "user": os.environ.get("POSTGRES_USER", "coe"),
        "password": os.environ.get("POSTGRES_PASSWORD", "coe_password"),
        "database": os.environ.get("POSTGRES_DB", "coe_memory"),
    }


class ReadonlyConnection:
    """Database connection with read-only enforcement."""

    def __init__(self, config: Optional[Dict[str, str]] = None):
        """Initialize connection.

        Args:
            config: Database configuration
        """
        self.config = config or get_db_config()
        self._conn: Optional[Any] = None

    def __enter__(self) -> "ReadonlyConnection":
        """Context manager entry."""
        self._conn = psycopg2.connect(
            host=self.config["host"],
            port=self.config["port"],
            user=self.config["user"],
            password=self.config["password"],
            database=self.config["database"],
        )
        # Set read-only mode
        self._conn.set_session(readonly=True, autocommit=True)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def execute(
        self, query: str, parameters: Optional[List[Any]] = None, max_rows: int = 1000
    ) -> List[Dict[str, Any]]:
        """Execute read-only query.

        Args:
            query: SQL query to execute
            parameters: Query parameters
            max_rows: Maximum rows to return

        Returns:
            Query results as list of dictionaries
        """
        if not self._conn:
            raise RuntimeError("Connection not established")

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, parameters)

            # Check if query returns results
            if cur.description:
                return cur.fetchmany(max_rows)
            else:
                return []


async def db_query_readonly(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Execute a read-only database query.

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
        input_data = DbQueryInput(**parameters)

        # Execute query
        with ReadonlyConnection() as conn:
            rows = conn.execute(
                query=input_data.query,
                parameters=input_data.parameters,
                max_rows=input_data.max_rows,
            )

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="db_query_readonly",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={
                "rows": rows,
                "row_count": len(rows),
                "columns": list(rows[0].keys()) if rows else [],
            },
            duration_ms=duration_ms,
        )
    except psycopg2.Error as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="db_query_readonly",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=f"Database error: {e}",
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="db_query_readonly",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )
