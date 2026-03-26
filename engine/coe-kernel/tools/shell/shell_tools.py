"""Safe Shell Tools.

Tools for executing shell commands with strict allow-list policies.
"""

import asyncio
import shutil
import time
from typing import Any, Dict

from tools.policies import ALLOWED_BINARIES
from tools.schemas import ShellRunInput, ToolOutput, ToolStatus


async def shell_run_safe(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Execute a shell command with safety restrictions.

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
        input_data = ShellRunInput(**parameters)

        command = input_data.command
        binary = command[0]

        # Verify binary is in allow-list
        if binary not in ALLOWED_BINARIES:
            return ToolOutput(
                tool_name="shell_run_safe",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.BLOCKED,
                error=f"Binary '{binary}' not in allow-list",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Verify binary exists
        binary_path = shutil.which(binary)
        if not binary_path:
            return ToolOutput(
                tool_name="shell_run_safe",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error=f"Binary '{binary}' not found in PATH",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Execute command
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=input_data.working_dir,
            )

            # Wait with timeout
            timeout_sec = input_data.timeout_ms / 1000.0
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_sec
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolOutput(
                    tool_name="shell_run_safe",
                    action_id=action_id,
                    task_id=task_id,
                    status=ToolStatus.TIMEOUT,
                    error=f"Command timed out after {input_data.timeout_ms}ms",
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Truncate if too large
            max_bytes = input_data.max_output_bytes
            if len(stdout_str) > max_bytes:
                stdout_str = stdout_str[:max_bytes] + "\n... [truncated]"
            if len(stderr_str) > max_bytes:
                stderr_str = stderr_str[:max_bytes] + "\n... [truncated]"

            duration_ms = int((time.time() - start_time) * 1000)

            if process.returncode == 0:
                return ToolOutput(
                    tool_name="shell_run_safe",
                    action_id=action_id,
                    task_id=task_id,
                    status=ToolStatus.SUCCESS,
                    result={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "returncode": process.returncode,
                        "command": command,
                    },
                    duration_ms=duration_ms,
                )
            else:
                return ToolOutput(
                    tool_name="shell_run_safe",
                    action_id=action_id,
                    task_id=task_id,
                    status=ToolStatus.ERROR,
                    result={
                        "stdout": stdout_str,
                        "stderr": stderr_str,
                        "returncode": process.returncode,
                        "command": command,
                    },
                    error=f"Command failed with exit code {process.returncode}",
                    duration_ms=duration_ms,
                )

        except Exception as exec_error:
            duration_ms = int((time.time() - start_time) * 1000)
            return ToolOutput(
                tool_name="shell_run_safe",
                action_id=action_id,
                task_id=task_id,
                status=ToolStatus.ERROR,
                error=f"Execution error: {exec_error}",
                duration_ms=duration_ms,
            )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="shell_run_safe",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )
