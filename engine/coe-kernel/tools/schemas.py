"""Tool Execution Schemas.

Pydantic schemas for strict tool input/output validation.
All tool calls must conform to these schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ToolStatus(str, Enum):
    """Tool execution status values."""

    PENDING = "pending"
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class PolicyDecision(str, Enum):
    """Policy gate decisions."""

    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"


class ToolInput(BaseModel):
    """Standard tool input envelope.

    All tool calls must include this envelope for routing
    and policy evaluation.
    """

    tool_name: str = Field(
        ..., description="Name of the tool to execute", min_length=1, max_length=100
    )
    action_id: str = Field(
        ...,
        description="Unique action ID for idempotency",
        min_length=1,
        max_length=100,
    )
    task_id: str = Field(
        ..., description="Parent task ID for correlation", min_length=1, max_length=100
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool-specific parameters"
    )
    timeout_ms: int = Field(
        default=30000, ge=1000, le=300000, description="Timeout in milliseconds"
    )

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Tool name must be alphanumeric with underscores/hyphens only"
            )
        return v.lower()


class ToolOutput(BaseModel):
    """Standard tool output envelope.

    All tool responses must conform to this schema.
    """

    tool_name: str = Field(..., description="Name of the executed tool")
    action_id: str = Field(..., description="Action ID from input")
    task_id: str = Field(..., description="Parent task ID")
    status: ToolStatus = Field(..., description="Execution status")
    result: Optional[Any] = Field(default=None, description="Tool result data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    duration_ms: int = Field(
        ..., ge=0, description="Execution duration in milliseconds"
    )
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    receipt_path: Optional[str] = Field(
        default=None, description="Path to receipt file"
    )
    artifacts: List[str] = Field(
        default_factory=list, description="List of artifact paths"
    )

    @field_validator("error")
    @classmethod
    def validate_error(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Ensure error is set when status is error."""
        values = info.data
        if values.get("status") == ToolStatus.ERROR and not v:
            raise ValueError("Error message required when status is 'error'")
        return v


class PolicyCheck(BaseModel):
    """Policy evaluation result."""

    decision: PolicyDecision = Field(..., description="Policy decision")
    reason: str = Field(..., description="Reason for decision")
    blocked_patterns: List[str] = Field(
        default_factory=list, description="Matched blocked patterns"
    )
    risk_score: int = Field(default=0, ge=0, le=100, description="Risk score 0-100")


class BrowserGotoInput(BaseModel):
    """Input for browser_goto tool."""

    url: str = Field(..., description="URL to navigate to", min_length=1)
    wait_until: Literal["load", "domcontentloaded", "networkidle"] = Field(
        default="load", description="When to consider navigation complete"
    )
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)


class BrowserExtractTextInput(BaseModel):
    """Input for browser_extract_text tool."""

    selector: Optional[str] = Field(
        default=None, description="CSS selector to extract from"
    )
    include_html: bool = Field(default=False, description="Include HTML in output")


class BrowserScreenshotInput(BaseModel):
    """Input for browser_screenshot tool."""

    full_page: bool = Field(default=False, description="Capture full page")
    selector: Optional[str] = Field(
        default=None, description="Element selector to screenshot"
    )
    filename: Optional[str] = Field(default=None, description="Custom filename")


class BrowserClickInput(BaseModel):
    """Input for browser_click tool."""

    selector: str = Field(
        ..., description="CSS selector of element to click", min_length=1
    )
    timeout_ms: int = Field(default=5000, ge=1000, le=30000)


class BrowserTypeInput(BaseModel):
    """Input for browser_type tool."""

    selector: str = Field(
        ..., description="CSS selector of input element", min_length=1
    )
    text: str = Field(..., description="Text to type")
    submit: bool = Field(default=False, description="Press Enter after typing")
    delay_ms: int = Field(
        default=0, ge=0, le=1000, description="Delay between keystrokes"
    )


class BrowserDownloadInput(BaseModel):
    """Input for browser_download tool."""

    url: str = Field(..., description="URL to download from", min_length=1)
    filename: Optional[str] = Field(default=None, description="Custom filename")


class DbQueryInput(BaseModel):
    """Input for db_query_readonly tool."""

    query: str = Field(..., description="SQL query to execute", min_length=1)
    parameters: Optional[List[Any]] = Field(
        default=None, description="Query parameters"
    )
    max_rows: int = Field(default=1000, ge=1, le=10000)


class VectorSearchInput(BaseModel):
    """Input for vector_search tool."""

    query: str = Field(..., description="Search query", min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    filter: Optional[Dict[str, Any]] = Field(
        default=None, description="Metadata filter"
    )


class KgQueryInput(BaseModel):
    """Input for kg_query tool."""

    cypher: str = Field(..., description="Cypher query", min_length=1)
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Query parameters"
    )


class FileReadInput(BaseModel):
    """Input for file_read_text tool."""

    path: str = Field(..., description="File path to read", min_length=1)
    encoding: str = Field(default="utf-8", description="File encoding")
    max_bytes: int = Field(
        default=1048576, ge=1, le=10485760, description="Max bytes to read"
    )


class FileWriteInput(BaseModel):
    """Input for file_write_artifact tool."""

    filename: str = Field(..., description="Filename to write", min_length=1)
    content: str = Field(..., description="Content to write")
    encoding: str = Field(default="utf-8", description="File encoding")


class FileListInput(BaseModel):
    """Input for file_list_dir tool."""

    path: str = Field(..., description="Directory path to list", min_length=1)
    recursive: bool = Field(default=False, description="List recursively")
    pattern: Optional[str] = Field(default=None, description="Glob pattern to filter")


class ApiGetInput(BaseModel):
    """Input for api_get tool."""

    url: str = Field(..., description="URL to fetch", min_length=1)
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Request headers"
    )
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)


class ApiPostInput(BaseModel):
    """Input for api_post_json tool."""

    url: str = Field(..., description="URL to post to", min_length=1)
    data: Dict[str, Any] = Field(..., description="JSON data to post")
    headers: Optional[Dict[str, str]] = Field(
        default=None, description="Request headers"
    )
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)


class ShellRunInput(BaseModel):
    """Input for shell_run_safe tool."""

    command: List[str] = Field(
        ..., description="Command as list of arguments", min_length=1
    )
    working_dir: Optional[str] = Field(default=None, description="Working directory")
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)
    max_output_bytes: int = Field(default=1048576, ge=1024, le=10485760)

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: List[str]) -> List[str]:
        """Validate command is not empty."""
        if not v or not v[0]:
            raise ValueError("Command must not be empty")
        return v


class ReceiptData(BaseModel):
    """Receipt data structure."""

    action_id: str
    task_id: str
    tool_name: str
    input_summary: Dict[str, Any]
    output_summary: Dict[str, Any]
    policy_decision: PolicyDecision
    started_at: str
    completed_at: str
    duration_ms: int
    status: ToolStatus
    error: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)
