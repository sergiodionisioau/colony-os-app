"""Tool Registry.

Central registry for all available tools.
Tools are registered with their metadata and handler functions.
"""

from typing import Any, Callable, Coroutine, Dict, Type

from tools.schemas import (
    ApiGetInput,
    ApiPostInput,
    BrowserClickInput,
    BrowserDownloadInput,
    BrowserExtractTextInput,
    BrowserGotoInput,
    BrowserScreenshotInput,
    BrowserTypeInput,
    DbQueryInput,
    FileListInput,
    FileReadInput,
    FileWriteInput,
    KgQueryInput,
    ShellRunInput,
    ToolInput,
    ToolOutput,
    VectorSearchInput,
)

# Type alias for tool handler
ToolHandler = Callable[[str, str, Dict[str, Any]], Coroutine[Any, Any, ToolOutput]]


class ToolMetadata:
    """Metadata for a registered tool."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Type,
        handler: ToolHandler,
        category: str,
        requires_policy: bool = True,
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler
        self.category = category
        self.requires_policy = requires_policy


# Global tool registry
TOOL_REGISTRY: Dict[str, ToolMetadata] = {}


def register_tool(
    name: str,
    description: str,
    input_schema: Type,
    handler: ToolHandler,
    category: str,
    requires_policy: bool = True,
) -> None:
    """Register a tool in the registry.

    Args:
        name: Tool name (unique identifier)
        description: Human-readable description
        input_schema: Pydantic model for input validation
        handler: Async function to execute the tool
        category: Tool category (browser, db, file, api, shell)
        requires_policy: Whether policy check is required
    """
    TOOL_REGISTRY[name] = ToolMetadata(
        name=name,
        description=description,
        input_schema=input_schema,
        handler=handler,
        category=category,
        requires_policy=requires_policy,
    )


def get_tool(name: str) -> ToolMetadata:
    """Get tool metadata by name.

    Args:
        name: Tool name

    Returns:
        Tool metadata

    Raises:
        KeyError: If tool not found
    """
    if name not in TOOL_REGISTRY:
        raise KeyError(f"Tool not found: {name}")
    return TOOL_REGISTRY[name]


def list_tools(category: str = None) -> Dict[str, Dict[str, Any]]:
    """List all registered tools.

    Args:
        category: Filter by category

    Returns:
        Dictionary of tool names to metadata
    """
    result = {}
    for name, metadata in TOOL_REGISTRY.items():
        if category and metadata.category != category:
            continue
        result[name] = {
            "name": metadata.name,
            "description": metadata.description,
            "category": metadata.category,
            "requires_policy": metadata.requires_policy,
            "input_schema": metadata.input_schema.__name__,
        }
    return result


def tool_exists(name: str) -> bool:
    """Check if a tool exists in the registry.

    Args:
        name: Tool name

    Returns:
        True if tool exists
    """
    return name in TOOL_REGISTRY


def _register_all_tools() -> None:
    """Register all tools. Called once at module load."""
    # Import browser tools
    from tools.browser.browser_tools import (
        browser_click,
        browser_close,
        browser_download,
        browser_extract_text,
        browser_goto,
        browser_screenshot,
        browser_type,
    )

    register_tool(
        "browser_goto",
        "Navigate browser to a URL",
        BrowserGotoInput,
        browser_goto,
        "browser",
    )

    register_tool(
        "browser_extract_text",
        "Extract text from the current page",
        BrowserExtractTextInput,
        browser_extract_text,
        "browser",
    )

    register_tool(
        "browser_screenshot",
        "Take a screenshot of the current page",
        BrowserScreenshotInput,
        browser_screenshot,
        "browser",
    )

    register_tool(
        "browser_click",
        "Click an element on the page",
        BrowserClickInput,
        browser_click,
        "browser",
    )

    register_tool(
        "browser_type",
        "Type text into an input element",
        BrowserTypeInput,
        browser_type,
        "browser",
    )

    register_tool(
        "browser_download",
        "Download a file from a URL",
        BrowserDownloadInput,
        browser_download,
        "browser",
    )

    register_tool(
        "browser_close",
        "Close the browser session",
        ToolInput,  # No specific input needed
        browser_close,
        "browser",
    )

    # Import database tools
    from tools.db.postgres_tools import db_query_readonly
    from tools.db.vector_tools import vector_search
    from tools.db.kg_tools import kg_query

    register_tool(
        "db_query_readonly",
        "Execute a read-only SQL query",
        DbQueryInput,
        db_query_readonly,
        "db",
    )

    register_tool(
        "vector_search",
        "Search vector store for similar content",
        VectorSearchInput,
        vector_search,
        "db",
    )

    register_tool(
        "kg_query",
        "Query the Knowledge Graph with Cypher",
        KgQueryInput,
        kg_query,
        "db",
    )

    # Import file tools
    from tools.file.file_tools import (
        file_list_dir,
        file_read_text,
        file_write_artifact,
    )

    register_tool(
        "file_read_text",
        "Read text from a file",
        FileReadInput,
        file_read_text,
        "file",
    )

    register_tool(
        "file_write_artifact",
        "Write content to an artifact file",
        FileWriteInput,
        file_write_artifact,
        "file",
    )

    register_tool(
        "file_list_dir",
        "List directory contents",
        FileListInput,
        file_list_dir,
        "file",
    )

    # Import API tools
    from tools.api.http_tools import api_get, api_post_json

    register_tool(
        "api_get",
        "Execute an HTTP GET request",
        ApiGetInput,
        api_get,
        "api",
    )

    register_tool(
        "api_post_json",
        "Execute an HTTP POST request with JSON body",
        ApiPostInput,
        api_post_json,
        "api",
    )

    # Import shell tools
    from tools.shell.shell_tools import shell_run_safe

    register_tool(
        "shell_run_safe",
        "Execute a shell command with safety restrictions",
        ShellRunInput,
        shell_run_safe,
        "shell",
    )


# Register all tools on module load
_register_all_tools()
