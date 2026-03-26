"""R-KG Node and Edge Schema Definitions."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime


@dataclass
class Identity:
    """A person within the graph."""

    uid: str
    email: str
    name: Optional[str] = None
    role: Optional[str] = None
    linkedin_url: Optional[str] = None
    intent_score: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Entity:
    """An organization/company within the graph."""

    uid: str
    domain: str
    name: str
    industry: Optional[str] = None
    icp_score: float = 0.0
    status: str = "PROSPECT"  # PROSPECT, LEAD, CUSTOMER, CHURNED
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Signal:
    """A timestamped event or intent indicator."""

    uid: str
    type: str  # FUNDING, HIRING, WEB_VISIT, CONTENT_CONSUMPTION
    source: str
    confidence: float
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relationship:
    """An edge connecting nodes (e.g., Identity -> Entity)."""

    uid: str
    from_uid: str
    to_uid: str
    type: str  # WORKS_AT, INFLUENCER_OF, DECISION_MAKER_FOR
    strength: float = 1.0
    first_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
