"""Tool Policies.

Policy gate for enforcing safety rules on tool execution.
All write actions and shell commands must pass policy evaluation.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tools.schemas import PolicyCheck, PolicyDecision

# Blocked shell command patterns (security critical)
BLOCKED_SHELL_PATTERNS: List[str] = [
    # Destructive commands
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+/\.",
    r">\s*/\S+",  # Overwriting system files
    r"dd\s+if=.*of=/dev/",
    r":\(\)\s*\{\s*:\|:\&\s*\};:",  # Fork bomb
    r"mkfs\.",
    r"fdisk\s+/dev/",
    r"format\s+/",
    # Remote code execution risks
    r"curl\s+.*\|\s*sh",
    r"curl\s+.*\|\s*bash",
    r"wget\s+.*\|\s*sh",
    r"wget\s+.*\|\s*bash",
    r"eval\s*\$",
    r"eval\s*\`",
    # Privilege escalation
    r"sudo\s+",
    r"su\s+-",
    r"chmod\s+.*777",
    r"chmod\s+.*u\+s",
    # Network attacks
    r"nc\s+-e",
    r"ncat\s+-e",
    r"netcat\s+-e",
    # Data exfiltration risks
    r"scp\s+.*@",
    r"rsync\s+.*@",
    # Shell escapes
    r"bash\s+-c",
    r"sh\s+-c",
    r"zsh\s+-c",
]

# Allowed binaries for shell execution (allow-list approach)
ALLOWED_BINARIES: Set[str] = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "awk",
    "sed",
    "find",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "echo",
    "pwd",
    "date",
    "whoami",
    "uname",
    "hostname",
    "ps",
    "top",
    "df",
    "du",
    "file",
    "which",
    "git",
    "python3",
    "python",
    "pip",
    "pytest",
    "black",
    "flake8",
    "mypy",
    "pylint",
    "bandit",
    "docker",
    "docker-compose",
    "kubectl",
    "curl",
    "wget",
    "ping",
    "nslookup",
    "dig",
}

# Allowed write directories (must be under these roots)
ALLOWED_WRITE_ROOTS: List[Path] = [
    Path("/home/coe/.openclaw/workspace/colony-os-app/engine/coe-kernel/artifacts"),
    Path("/tmp/coe-artifacts"),
    Path("./artifacts"),
]

# Allowed browser domains (empty = allow all, populate for restrictions)
ALLOWED_BROWSER_DOMAINS: List[str] = []

# Blocked browser domains
BLOCKED_BROWSER_DOMAINS: List[str] = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
]

# Blocked file paths (system critical)
BLOCKED_FILE_PATHS: List[str] = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hosts",
    "/etc/ssh",
    "/root",
    "/var/log",
    "/proc",
    "/sys",
    "/dev",
]

# Read-only SQL keywords (must be SELECT)
READONLY_SQL_KEYWORDS: List[str] = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "EXEC",
]


def evaluate_policy(
    tool_name: str, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None
) -> PolicyCheck:
    """Evaluate tool execution against security policies.

    Args:
        tool_name: Name of the tool to execute
        parameters: Tool parameters
        context: Additional context for policy evaluation

    Returns:
        PolicyCheck with decision and reason
    """
    context = context or {}

    # Route to specific policy evaluator
    if tool_name.startswith("browser_"):
        return _evaluate_browser_policy(tool_name, parameters)
    elif tool_name.startswith("db_"):
        return _evaluate_db_policy(tool_name, parameters)
    elif tool_name.startswith("file_"):
        return _evaluate_file_policy(tool_name, parameters)
    elif tool_name.startswith("shell_"):
        return _evaluate_shell_policy(tool_name, parameters)
    elif tool_name.startswith("api_"):
        return _evaluate_api_policy(tool_name, parameters)
    elif tool_name in ("vector_search", "kg_query"):
        return _evaluate_readonly_policy(tool_name, parameters)
    else:
        return PolicyCheck(
            decision=PolicyDecision.BLOCK,
            reason=f"Unknown tool: {tool_name}",
            risk_score=100,
        )


def _evaluate_browser_policy(tool_name: str, parameters: Dict[str, Any]) -> PolicyCheck:
    """Evaluate browser tool policies."""
    url = parameters.get("url", "")

    # Check blocked domains
    for blocked in BLOCKED_BROWSER_DOMAINS:
        if blocked in url:
            return PolicyCheck(
                decision=PolicyDecision.BLOCK,
                reason=f"Blocked domain: {blocked}",
                blocked_patterns=[blocked],
                risk_score=90,
            )

    # Check allowed domains if restricted
    if ALLOWED_BROWSER_DOMAINS:
        allowed = any(domain in url for domain in ALLOWED_BROWSER_DOMAINS)
        if not allowed:
            return PolicyCheck(
                decision=PolicyDecision.BLOCK,
                reason="Domain not in allow-list",
                risk_score=70,
            )

    return PolicyCheck(
        decision=PolicyDecision.ALLOW, reason="Browser action permitted", risk_score=10
    )


def _evaluate_db_policy(tool_name: str, parameters: Dict[str, Any]) -> PolicyCheck:
    """Evaluate database tool policies."""
    query = parameters.get("query", "").upper()

    # Check for write operations in read-only tools
    if tool_name == "db_query_readonly":
        for keyword in READONLY_SQL_KEYWORDS:
            if keyword in query:
                return PolicyCheck(
                    decision=PolicyDecision.BLOCK,
                    reason=f"Write operation detected: {keyword}",
                    blocked_patterns=[keyword],
                    risk_score=80,
                )

    return PolicyCheck(
        decision=PolicyDecision.ALLOW, reason="Read-only query permitted", risk_score=5
    )


def _evaluate_file_policy(tool_name: str, parameters: Dict[str, Any]) -> PolicyCheck:
    """Evaluate file tool policies."""
    path_str = parameters.get("path") or parameters.get("filename", "")

    if not path_str:
        return PolicyCheck(
            decision=PolicyDecision.BLOCK, reason="No path specified", risk_score=50
        )

    path = Path(path_str).resolve()

    # Check blocked paths
    for blocked in BLOCKED_FILE_PATHS:
        if str(path).startswith(blocked):
            return PolicyCheck(
                decision=PolicyDecision.BLOCK,
                reason=f"Access to system path blocked: {blocked}",
                blocked_patterns=[blocked],
                risk_score=95,
            )

    # Write operations must be in allowed roots
    if tool_name == "file_write_artifact":
        in_allowed_root = any(
            str(path).startswith(str(root.resolve())) for root in ALLOWED_WRITE_ROOTS
        )
        if not in_allowed_root:
            return PolicyCheck(
                decision=PolicyDecision.BLOCK,
                reason=f"Write outside allowed directories: {path}",
                risk_score=75,
            )

    return PolicyCheck(
        decision=PolicyDecision.ALLOW, reason="File operation permitted", risk_score=15
    )


def _evaluate_shell_policy(tool_name: str, parameters: Dict[str, Any]) -> PolicyCheck:
    """Evaluate shell tool policies."""
    command = parameters.get("command", [])

    if not command:
        return PolicyCheck(
            decision=PolicyDecision.BLOCK, reason="Empty command", risk_score=50
        )

    binary = command[0]
    command_str = " ".join(command)

    # Check binary allow-list
    if binary not in ALLOWED_BINARIES:
        return PolicyCheck(
            decision=PolicyDecision.BLOCK,
            reason=f"Binary not in allow-list: {binary}",
            risk_score=70,
        )

    # Check blocked patterns
    matched_patterns = []
    for pattern in BLOCKED_SHELL_PATTERNS:
        if re.search(pattern, command_str, re.IGNORECASE):
            matched_patterns.append(pattern)

    if matched_patterns:
        return PolicyCheck(
            decision=PolicyDecision.BLOCK,
            reason="Blocked shell pattern detected",
            blocked_patterns=matched_patterns,
            risk_score=95,
        )

    # Risk assessment based on command complexity
    risk_score = 30
    if "|" in command_str:
        risk_score += 10
    if ";" in command_str:
        risk_score += 10
    if "$(" in command_str or "`" in command_str:
        risk_score += 20

    return PolicyCheck(
        decision=PolicyDecision.ALLOW,
        reason="Shell command permitted",
        risk_score=min(risk_score, 100),
    )


def _evaluate_api_policy(tool_name: str, parameters: Dict[str, Any]) -> PolicyCheck:
    """Evaluate API tool policies."""
    url = parameters.get("url", "")

    # Block internal addresses
    internal_patterns = [
        r"^http://127\.",
        r"^http://192\.168\.",
        r"^http://10\.",
        r"^http://172\.(1[6-9]|2[0-9]|3[01])\.",
        r"^http://localhost",
        r"^http://\[::1\]",
    ]

    for pattern in internal_patterns:
        if re.match(pattern, url, re.IGNORECASE):
            return PolicyCheck(
                decision=PolicyDecision.BLOCK,
                reason="Internal address access blocked",
                blocked_patterns=[pattern],
                risk_score=85,
            )

    return PolicyCheck(
        decision=PolicyDecision.ALLOW, reason="API call permitted", risk_score=20
    )


def _evaluate_readonly_policy(
    tool_name: str, parameters: Dict[str, Any]
) -> PolicyCheck:
    """Evaluate read-only tool policies."""
    return PolicyCheck(
        decision=PolicyDecision.ALLOW,
        reason="Read-only operation permitted",
        risk_score=5,
    )


def add_allowed_binary(binary: str) -> None:
    """Add a binary to the allow-list."""
    ALLOWED_BINARIES.add(binary)


def add_allowed_write_root(path: str) -> None:
    """Add a directory to allowed write roots."""
    ALLOWED_WRITE_ROOTS.append(Path(path))


def is_path_allowed(path: str, for_write: bool = False) -> bool:
    """Check if a path is allowed for access.

    Args:
        path: Path to check
        for_write: Whether this is a write operation

    Returns:
        True if path is allowed
    """
    resolved = Path(path).resolve()

    # Check blocked paths
    for blocked in BLOCKED_FILE_PATHS:
        if str(resolved).startswith(blocked):
            return False

    # Write operations must be in allowed roots
    if for_write:
        return any(
            str(resolved).startswith(str(root.resolve()))
            for root in ALLOWED_WRITE_ROOTS
        )

    return True
