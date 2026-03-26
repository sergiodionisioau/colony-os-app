"""Playwright Browser Client.

Managed browser session for automation.
Provides context manager for safe resource cleanup.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


@dataclass
class BrowserSessionConfig:
    """Configuration for browser session."""

    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: Optional[str] = None
    timeout_ms: int = 30000
    download_dir: Optional[str] = None


class PlaywrightSession:
    """Managed Playwright browser session.

    Usage:
        async with PlaywrightSession() as session:
            page = await session.new_page()
            await session.goto("https://example.com")
            text = await session.extract_text()
    """

    def __init__(self, config: Optional[BrowserSessionConfig] = None):
        """Initialize browser session.

        Args:
            config: Browser configuration
        """
        self.config = config or BrowserSessionConfig()
        self._playwright: Optional[Any] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._downloads: list = []

    async def start(self) -> "PlaywrightSession":
        """Start the browser session.

        Returns:
            Self for chaining
        """
        self._playwright = await async_playwright().start()

        # Launch browser
        self._browser = await self._playwright.chromium.launch(
            headless=self.config.headless
        )

        # Create context with viewport
        context_options: Dict[str, Any] = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            }
        }

        if self.config.user_agent:
            context_options["user_agent"] = self.config.user_agent

        if self.config.download_dir:
            context_options["accept_downloads"] = True
            Path(self.config.download_dir).mkdir(parents=True, exist_ok=True)

        self._context = await self._browser.new_context(**context_options)

        # Set default timeout
        self._context.set_default_timeout(self.config.timeout_ms)

        # Create initial page
        self._page = await self._context.new_page()

        return self

    async def close(self) -> None:
        """Close the browser session and cleanup resources."""
        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        self._page = None

    async def __aenter__(self) -> "PlaywrightSession":
        """Async context manager entry."""
        return await self.start()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    @property
    def page(self) -> Page:
        """Get current page.

        Returns:
            Current page object

        Raises:
            RuntimeError: If session not started
        """
        if not self._page:
            raise RuntimeError(
                "Browser session not started. Use 'async with' or call start()"
            )
        return self._page

    async def new_page(self) -> Page:
        """Create a new page in the browser context.

        Returns:
            New page object
        """
        if not self._context:
            raise RuntimeError("Browser session not started")

        self._page = await self._context.new_page()
        return self._page

    async def goto(
        self, url: str, wait_until: str = "load", timeout_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Navigate to URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
            timeout_ms: Navigation timeout

        Returns:
            Navigation result with url, title, status
        """
        page = self.page

        timeout = timeout_ms or self.config.timeout_ms

        response = await page.goto(
            url, wait_until=wait_until, timeout=timeout  # type: ignore
        )

        return {
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None,
        }

    async def extract_text(
        self, selector: Optional[str] = None, include_html: bool = False
    ) -> Dict[str, Any]:
        """Extract text from page.

        Args:
            selector: CSS selector to extract from (None = full page)
            include_html: Include HTML in output

        Returns:
            Extracted text and metadata
        """
        page = self.page

        if selector:
            element = await page.query_selector(selector)
            if not element:
                return {
                    "text": "",
                    "html": "" if include_html else None,
                    "selector": selector,
                    "found": False,
                }

            text = await element.inner_text()
            html = await element.inner_html() if include_html else None
        else:
            text = await page.inner_text("body")
            html = await page.content() if include_html else None

        return {
            "text": text,
            "html": html,
            "selector": selector,
            "found": True,
            "length": len(text),
        }

    async def click(
        self, selector: str, timeout_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Click an element.

        Args:
            selector: CSS selector of element to click
            timeout_ms: Timeout for click operation

        Returns:
            Click result
        """
        page = self.page
        timeout = timeout_ms or 5000

        await page.click(selector, timeout=timeout)

        return {"clicked": True, "selector": selector, "current_url": page.url}

    async def type_text(
        self, selector: str, text: str, submit: bool = False, delay_ms: int = 0
    ) -> Dict[str, Any]:
        """Type text into an input element.

        Args:
            selector: CSS selector of input element
            text: Text to type
            submit: Press Enter after typing
            delay_ms: Delay between keystrokes

        Returns:
            Type result
        """
        page = self.page

        delay = delay_ms if delay_ms > 0 else None

        await page.fill(selector, "")
        await page.type(selector, text, delay=delay)

        if submit:
            await page.press(selector, "Enter")

        return {
            "typed": True,
            "selector": selector,
            "text_length": len(text),
            "submitted": submit,
        }

    async def screenshot(
        self, path: str, full_page: bool = False, selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Take a screenshot.

        Args:
            path: Path to save screenshot
            full_page: Capture full page
            selector: Element selector to screenshot

        Returns:
            Screenshot result
        """
        page = self.page

        if selector:
            element = await page.query_selector(selector)
            if element:
                await element.screenshot(path=path)
            else:
                raise ValueError(f"Element not found: {selector}")
        else:
            await page.screenshot(path=path, full_page=full_page)

        return {"path": path, "full_page": full_page, "selector": selector}

    async def download(self, url: str, path: str) -> Dict[str, Any]:
        """Download a file.

        Args:
            url: URL to download
            path: Path to save file

        Returns:
            Download result
        """
        page = self.page

        # Start waiting for download
        async with page.expect_download() as download_info:
            await page.evaluate(f"window.location.href = '{url}'")

        download = await download_info.value
        await download.save_as(path)

        return {
            "path": path,
            "url": url,
            "filename": download.suggested_filename,
            "size": Path(path).stat().st_size if Path(path).exists() else 0,
        }

    def get_cookies(self) -> list:
        """Get current cookies.

        Returns:
            List of cookies
        """
        if not self._context:
            return []

        # This is async but cookies are usually synced
        # Return empty for now, can be made async if needed
        return []
