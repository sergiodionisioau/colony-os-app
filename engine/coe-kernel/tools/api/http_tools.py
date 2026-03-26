"""HTTP API Tools.

Tools for making HTTP requests to external APIs.
"""

import time
from typing import Any, Dict

import httpx

from tools.schemas import ApiGetInput, ApiPostInput, ToolOutput, ToolStatus


async def api_get(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Execute an HTTP GET request.

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
        input_data = ApiGetInput(**parameters)

        # Execute request
        timeout = httpx.Timeout(input_data.timeout_ms / 1000.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(input_data.url, headers=input_data.headers)
            response.raise_for_status()

            # Try to parse as JSON, fallback to text
            try:
                content = response.json()
                content_type = "json"
            except Exception:
                content = response.text
                content_type = "text"

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="api_get",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={
                "status_code": response.status_code,
                "content": content,
                "content_type": content_type,
                "headers": dict(response.headers),
                "url": str(response.url),
            },
            duration_ms=duration_ms,
        )
    except httpx.HTTPStatusError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="api_get",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            duration_ms=duration_ms,
        )
    except httpx.TimeoutException:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="api_get",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.TIMEOUT,
            error=f"Request timed out after {input_data.timeout_ms}ms",
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="api_get",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )


async def api_post_json(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Execute an HTTP POST request with JSON body.

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
        input_data = ApiPostInput(**parameters)

        # Prepare headers
        headers = input_data.headers or {}
        headers.setdefault("Content-Type", "application/json")

        # Execute request
        timeout = httpx.Timeout(input_data.timeout_ms / 1000.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.post(
                input_data.url, json=input_data.data, headers=headers
            )
            response.raise_for_status()

            # Try to parse as JSON, fallback to text
            try:
                content = response.json()
                content_type = "json"
            except Exception:
                content = response.text
                content_type = "text"

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="api_post_json",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={
                "status_code": response.status_code,
                "content": content,
                "content_type": content_type,
                "headers": dict(response.headers),
                "url": str(response.url),
            },
            duration_ms=duration_ms,
        )
    except httpx.HTTPStatusError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="api_post_json",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=f"HTTP {e.response.status_code}: {e.response.text[:500]}",
            duration_ms=duration_ms,
        )
    except httpx.TimeoutException:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="api_post_json",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.TIMEOUT,
            error=f"Request timed out after {input_data.timeout_ms}ms",
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="api_post_json",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )
