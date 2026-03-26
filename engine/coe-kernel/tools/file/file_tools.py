"""File Tools.

Tools for reading files and writing artifacts.
"""

import os
import time
from pathlib import Path
from typing import Any, Dict

from tools.schemas import (
    FileListInput,
    FileReadInput,
    FileWriteInput,
    ToolOutput,
    ToolStatus,
)
from tools.policies import is_path_allowed

# Default artifacts directory
DEFAULT_ARTIFACTS_DIR = Path(
    "/home/coe/.openclaw/workspace/colony-os-app/engine/coe-kernel/artifacts"
)


def _get_artifacts_dir() -> Path:
    """Get artifacts directory."""
    path = Path(os.environ.get("COE_ARTIFACTS_DIR", DEFAULT_ARTIFACTS_DIR))
    path.mkdir(parents=True, exist_ok=True)
    return path


async def file_read_text(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Read text from a file.

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
        input_data = FileReadInput(**parameters)

        # Check path is allowed
        if not is_path_allowed(input_data.path, for_write=False):
            return ToolOutput(
                tool_name="file_read_text",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error="Path not allowed for reading",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Read file
        path = Path(input_data.path)
        if not path.exists():
            return ToolOutput(
                tool_name="file_read_text",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error=f"File not found: {input_data.path}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Check size
        size = path.stat().st_size
        if size > input_data.max_bytes:
            return ToolOutput(
                tool_name="file_read_text",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error=f"File too large: {size} bytes (max: {input_data.max_bytes})",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        content = path.read_text(encoding=input_data.encoding)

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="file_read_text",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={
                "content": content,
                "path": str(path.resolve()),
                "size": size,
                "encoding": input_data.encoding,
            },
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="file_read_text",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )


async def file_write_artifact(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Write content to an artifact file.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    start_time = time.time()

    artifacts: list = []

    try:
        # Validate input
        input_data = FileWriteInput(**parameters)

        # Determine target path (must be in artifacts directory)
        artifacts_dir = _get_artifacts_dir()
        target_path = artifacts_dir / input_data.filename

        # Resolve and check path
        resolved_path = target_path.resolve()

        # Ensure path is within artifacts directory
        if not str(resolved_path).startswith(str(artifacts_dir.resolve())):
            return ToolOutput(
                tool_name="file_write_artifact",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error="Path must be within artifacts directory",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Check path is allowed for writing
        if not is_path_allowed(str(resolved_path), for_write=True):
            return ToolOutput(
                tool_name="file_write_artifact",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error="Path not allowed for writing",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Ensure parent directory exists
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        resolved_path.write_text(input_data.content, encoding=input_data.encoding)

        artifacts.append(str(resolved_path))
        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="file_write_artifact",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={
                "path": str(resolved_path),
                "size": len(input_data.content),
                "encoding": input_data.encoding,
            },
            duration_ms=duration_ms,
            artifacts=artifacts,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="file_write_artifact",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
            artifacts=artifacts,
        )


async def file_list_dir(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """List directory contents.

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
        input_data = FileListInput(**parameters)

        # Check path is allowed
        if not is_path_allowed(input_data.path, for_write=False):
            return ToolOutput(
                tool_name="file_list_dir",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error="Path not allowed for listing",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        path = Path(input_data.path)
        if not path.exists():
            return ToolOutput(
                tool_name="file_list_dir",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error=f"Path not found: {input_data.path}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        if not path.is_dir():
            return ToolOutput(
                tool_name="file_list_dir",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error=f"Path is not a directory: {input_data.path}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # List contents
        if input_data.recursive:
            entries = []
            for item in path.rglob(input_data.pattern or "*"):
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )
        else:
            entries = []
            for item in path.iterdir():
                if input_data.pattern and not item.match(input_data.pattern):
                    continue
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )

        # Sort entries
        entries.sort(key=lambda x: (x["type"] != "directory", x["name"]))

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="file_list_dir",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={
                "path": str(path.resolve()),
                "entries": entries,
                "count": len(entries),
            },
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="file_list_dir",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )
