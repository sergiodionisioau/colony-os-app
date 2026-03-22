"""
Colony OS - Task Model
SQLite-based with Postgres migration path.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import uuid


class TaskStatus(Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskComplexity(Enum):
    TRIVIAL = 1
    SIMPLE = 2
    MODERATE = 3
    COMPLEX = 4
    EPIC = 5


class TaskType(Enum):
    CODING = "coding"
    RESEARCH = "research"
    REVIEW = "review"
    PLANNING = "planning"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    MAINTENANCE = "maintenance"


@dataclass
class Task:
    """Task entity - matches Knowledge Graph Schema"""
    
    # Core
    id: str
    title: str
    description: str
    type: TaskType
    status: TaskStatus
    priority: int  # 1-5, 1 = highest
    complexity: TaskComplexity
    
    # Assignment
    created_by: str  # Agent ID
    assigned_to: Optional[str]  # Agent ID
    
    # Model routing
    preferred_model: Optional[str]  # Model enum value
    actual_model: Optional[str]  # What was actually used
    
    # Timing
    estimated_duration_minutes: Optional[int]
    actual_duration_minutes: Optional[int]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    due_date: Optional[datetime]
    
    # Metadata
    tags: List[str]
    dependencies: List[str]  # Task IDs
    project_id: Optional[str]
    roi_score: Optional[float]
    prediction_confidence: Optional[float]
    
    # Execution
    command: Optional[str]  # For sub-agent tasks
    workdir: Optional[str]
    output: Optional[str]
    error: Optional[str]
    
    # Cost tracking
    tokens_input: int
    tokens_output: int
    cost_usd: float
    
    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        created_by: str = "user",
        task_type: TaskType = TaskType.CODING,
        complexity: TaskComplexity = TaskComplexity.SIMPLE,
        priority: int = 3,
        assigned_to: Optional[str] = None,
        preferred_model: Optional[str] = None,
        estimated_duration_minutes: Optional[int] = None,
        due_date: Optional[datetime] = None,
        tags: List[str] = None,
        dependencies: List[str] = None,
        project_id: Optional[str] = None,
        command: Optional[str] = None,
        workdir: Optional[str] = None
    ) -> "Task":
        """Factory method to create a new task"""
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            type=task_type,
            status=TaskStatus.BACKLOG,
            priority=priority,
            complexity=complexity,
            created_by=created_by,
            assigned_to=assigned_to,
            preferred_model=preferred_model,
            actual_model=None,
            estimated_duration_minutes=estimated_duration_minutes,
            actual_duration_minutes=None,
            created_at=datetime.now(),
            started_at=None,
            completed_at=None,
            due_date=due_date,
            tags=tags or [],
            dependencies=dependencies or [],
            project_id=project_id,
            roi_score=None,
            prediction_confidence=None,
            command=command,
            workdir=workdir,
            output=None,
            error=None,
            tokens_input=0,
            tokens_output=0,
            cost_usd=0.0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/DB storage"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "status": self.status.value,
            "priority": self.priority,
            "complexity": self.complexity.value,
            "created_by": self.created_by,
            "assigned_to": self.assigned_to,
            "preferred_model": self.preferred_model,
            "actual_model": self.actual_model,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "actual_duration_minutes": self.actual_duration_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "tags": json.dumps(self.tags),
            "dependencies": json.dumps(self.dependencies),
            "project_id": self.project_id,
            "roi_score": self.roi_score,
            "prediction_confidence": self.prediction_confidence,
            "command": self.command,
            "workdir": self.workdir,
            "output": self.output,
            "error": self.error,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "cost_usd": self.cost_usd
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary (DB result)"""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            type=TaskType(data["type"]),
            status=TaskStatus(data["status"]),
            priority=data["priority"],
            complexity=TaskComplexity(data["complexity"]),
            created_by=data["created_by"],
            assigned_to=data.get("assigned_to"),
            preferred_model=data.get("preferred_model"),
            actual_model=data.get("actual_model"),
            estimated_duration_minutes=data.get("estimated_duration_minutes"),
            actual_duration_minutes=data.get("actual_duration_minutes"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            tags=json.loads(data["tags"]) if data.get("tags") else [],
            dependencies=json.loads(data["dependencies"]) if data.get("dependencies") else [],
            project_id=data.get("project_id"),
            roi_score=data.get("roi_score"),
            prediction_confidence=data.get("prediction_confidence"),
            command=data.get("command"),
            workdir=data.get("workdir"),
            output=data.get("output"),
            error=data.get("error"),
            tokens_input=data.get("tokens_input", 0),
            tokens_output=data.get("tokens_output", 0),
            cost_usd=data.get("cost_usd", 0.0)
        )
    
    def start(self, agent_id: str, model: str):
        """Mark task as started"""
        self.status = TaskStatus.IN_PROGRESS
        self.assigned_to = agent_id
        self.actual_model = model
        self.started_at = datetime.now()
    
    def complete(self, output: str = None, tokens_in: int = 0, tokens_out: int = 0):
        """Mark task as complete"""
        self.status = TaskStatus.DONE
        self.completed_at = datetime.now()
        self.output = output
        self.tokens_input = tokens_in
        self.tokens_output = tokens_out
        
        # Calculate actual duration
        if self.started_at:
            duration = (self.completed_at - self.started_at).total_seconds() / 60
            self.actual_duration_minutes = int(duration)
    
    def block(self, reason: str):
        """Mark task as blocked"""
        self.status = TaskStatus.BLOCKED
        self.error = reason
    
    def is_ready(self) -> bool:
        """Check if all dependencies are complete"""
        # This would check the DB in practice
        return self.status == TaskStatus.BACKLOG
    
    def can_run(self) -> bool:
        """Check if task can be executed now"""
        return self.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS] and self.is_ready()
    
    def __str__(self) -> str:
        return f"Task({self.id[:8]}): {self.title} [{self.status.value}]"
