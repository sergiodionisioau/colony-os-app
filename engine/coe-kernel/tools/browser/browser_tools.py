"""Browser Tool Implementations.

Tools for browser automation using Playwright.
All tools use the PlaywrightSession for resource management.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from tools.browser.playwright_client import BrowserSessionConfig, PlaywrightSession
from tools.schemas import (
    BrowserClickInput,
    BrowserDownloadInput,
    BrowserExtractTextInput,
    BrowserGotoInput,
    BrowserScreenshotInput,
    BrowserTypeInput,
    ToolOutput,
    ToolStatus,
)

# Artifact storage
ARTIFACTS_DIR = Path(
    os.environ.get(
        "COE_ARTIFACTS_DIR",
        "/home/coe/.openclaw/workspace/colony-os-app/engine/coe-kernel/artifacts",
    )
)


def _ensure_artifacts_dir() -> Path:
    """Ensure artifacts directory exists."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS_DIR


def _generate_filename(prefix: str, extension: str) -> str:
    """Generate a unique filename."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


class BrowserSessionManager:
    """Manages browser sessions for reuse."""

    _instance: Optional["BrowserSessionManager"] = None
    _session: Optional[PlaywrightSession] = None

    def __new__(cls) -> "BrowserSessionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_session(self) -> PlaywrightSession:
        """Get or create a browser session."""
        if self._session is None:
            config = BrowserSessionConfig(
                headless=True, download_dir=str(_ensure_artifacts_dir() / "downloads")
            )
            self._session = await PlaywrightSession(config).start()
        return self._session

    async def close(self) -> None:
        """Close the managed session."""
        if self._session:
            await self._session.close()
            self._session = None


async def browser_goto(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Navigate browser to URL.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    import time

    start_time = time.time()

    try:
        # Validate input
        input_data = BrowserGotoInput(**parameters)

        # Execute
        session_manager = BrowserSessionManager()
        session = await session_manager.get_session()

        result = await session.goto(
            url=input_data.url,
            wait_until=input_data.wait_until,
            timeout_ms=input_data.timeout_ms,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="browser_goto",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="browser_goto",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )


async def browser_extract_text(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Extract text from current page.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    import time

    start_time = time.time()

    try:
        # Validate input
        input_data = BrowserExtractTextInput(**parameters)

        # Execute
        session_manager = BrowserSessionManager()
        session = await session_manager.get_session()

        result = await session.extract_text(
            selector=input_data.selector, include_html=input_data.include_html
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="browser_extract_text",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="browser_extract_text",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )


async def browser_screenshot(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Take a screenshot of the current page.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    import time

    start_time = time.time()

    artifacts: list = []

    try:
        # Validate input
        input_data = BrowserScreenshotInput(**parameters)

        # Generate filename
        filename = input_data.filename or _generate_filename("screenshot", "png")
        path = str(_ensure_artifacts_dir() / filename)

        # Execute
        session_manager = BrowserSessionManager()
        session = await session_manager.get_session()

        result = await session.screenshot(
            path=path, full_page=input_data.full_page, selector=input_data.selector
        )

        artifacts.append(path)
        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="browser_screenshot",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
            artifacts=artifacts,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="browser_screenshot",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
            artifacts=artifacts,
        )


async def browser_click(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Click an element on the page.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    import time

    start_time = time.time()

    try:
        # Validate input
        input_data = BrowserClickInput(**parameters)

        # Execute
        session_manager = BrowserSessionManager()
        session = await session_manager.get_session()

        result = await session.click(
            selector=input_data.selector, timeout_ms=input_data.timeout_ms
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="browser_click",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="browser_click",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )


async def browser_type(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Type text into an input element.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    import time

    start_time = time.time()

    try:
        # Validate input
        input_data = BrowserTypeInput(**parameters)

        # Execute
        session_manager = BrowserSessionManager()
        session = await session_manager.get_session()

        result = await session.type_text(
            selector=input_data.selector,
            text=input_data.text,
            submit=input_data.submit,
            delay_ms=input_data.delay_ms,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="browser_type",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="browser_type",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )


async def browser_download(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Download a file from URL.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters

    Returns:
        Tool output envelope
    """
    import time

    start_time = time.time()

    artifacts: list = []

    try:
        # Validate input
        input_data = BrowserDownloadInput(**parameters)

        # Generate filename
        filename = input_data.filename or _generate_filename("download", "bin")
        path = str(_ensure_artifacts_dir() / "downloads" / filename)

        # Ensure downloads directory exists
        (_ensure_artifacts_dir() / "downloads").mkdir(exist_ok=True)

        # Execute
        session_manager = BrowserSessionManager()
        session = await session_manager.get_session()

        result = await session.download(url=input_data.url, path=path)

        artifacts.append(path)
        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="browser_download",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result=result,
            duration_ms=duration_ms,
            artifacts=artifacts,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="browser_download",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
            artifacts=artifacts,
        )


async def browser_close(
    action_id: str, task_id: str, parameters: Dict[str, Any]
) -> ToolOutput:
    """Close the browser session.

    Args:
        action_id: Unique action ID
        task_id: Parent task ID
        parameters: Tool parameters (unused)

    Returns:
        Tool output envelope
    """
    import time

    start_time = time.time()

    try:
        session_manager = BrowserSessionManager()
        await session_manager.close()

        duration_ms = int((time.time() - start_time) * 1000)

        return ToolOutput(
            tool_name="browser_close",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.SUCCESS,
            result={"closed": True},
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return ToolOutput(
            tool_name="browser_close",
            action_id=action_id,
            task_id=task_id,
            status=ToolStatus.ERROR,
            error=str(e),
            duration_ms=duration_ms,
        )
