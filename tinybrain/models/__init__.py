"""Pydantic models for TinyBrain."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Security task types."""

    SECURITY_REVIEW = "security_review"
    PENETRATION_TEST = "penetration_test"
    EXPLOIT_DEV = "exploit_dev"
    VULNERABILITY_ANALYSIS = "vulnerability_analysis"
    THREAT_MODELING = "threat_modeling"
    INCIDENT_RESPONSE = "incident_response"
    GENERAL = "general"


class SessionStatus(str, Enum):
    """Session status values."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Session(BaseModel):
    """Security assessment session."""

    id: str
    name: str
    description: Optional[str] = None
    task_type: TaskType
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[dict] = None


class MemoryCategory(str, Enum):
    """Memory categories."""

    FINDING = "finding"
    VULNERABILITY = "vulnerability"
    EXPLOIT = "exploit"
    PAYLOAD = "payload"
    TECHNIQUE = "technique"
    TOOL = "tool"
    REFERENCE = "reference"
    CONTEXT = "context"
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    RECOMMENDATION = "recommendation"
    NOTE = "note"


class ContentType(str, Enum):
    """Content types."""

    TEXT = "text"
    CODE = "code"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    BINARY_REF = "binary_ref"


class Memory(BaseModel):
    """Memory entry."""

    id: str
    session_id: str
    title: str
    content: str
    content_type: ContentType = ContentType.TEXT
    category: MemoryCategory
    priority: int = Field(ge=0, le=10, default=5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    tags: list[str] = Field(default_factory=list)
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0


class RelationshipType(str, Enum):
    """Relationship types."""

    DEPENDS_ON = "depends_on"
    CAUSES = "causes"
    MITIGATES = "mitigates"
    EXPLOITS = "exploits"
    REFERENCES = "references"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    RELATED_TO = "related_to"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"


class Relationship(BaseModel):
    """Memory relationship."""

    id: str
    source_entry_id: str
    target_entry_id: str
    relationship_type: RelationshipType
    strength: float = Field(ge=0.0, le=1.0, default=0.5)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskStatus(str, Enum):
    """Task status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskProgress(BaseModel):
    """Task progress tracking."""

    id: str
    session_id: str
    task_name: str
    stage: str
    status: TaskStatus = TaskStatus.PENDING
    progress_percentage: int = Field(ge=0, le=100, default=0)
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContextSnapshot(BaseModel):
    """Context snapshot."""

    id: str
    session_id: str
    name: str
    description: Optional[str] = None
    context_data: dict
    memory_summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationType(str, Enum):
    """Notification types."""

    MEMORY_CREATED = "memory_created"
    HIGH_PRIORITY = "high_priority"
    DUPLICATE_DETECTED = "duplicate_detected"
    CLEANUP = "cleanup"
    SYSTEM = "system"


class Notification(BaseModel):
    """Notification entry."""

    id: str
    session_id: Optional[str] = None
    notification_type: NotificationType
    priority: int = Field(ge=0, le=10, default=5)
    message: str
    metadata: Optional[dict] = None
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
