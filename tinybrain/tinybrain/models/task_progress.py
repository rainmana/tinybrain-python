"""Task progress model definitions."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskProgress(BaseModel):
    """Represents the progress of a specific task within a session."""

    id: str
    session_id: str
    task_name: str
    stage: str = Field(..., description="Current stage of the task")
    status: str = Field(
        default="pending",
        description="Task status",
        pattern="^(pending|in_progress|completed|failed|blocked)$",
    )
    progress_percentage: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Progress percentage 0.0-100.0"
    )
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskProgressCreateRequest(BaseModel):
    """Request structure for creating a new task progress entry."""

    session_id: str
    task_name: str
    stage: str
    status: str = Field(
        default="pending",
        pattern="^(pending|in_progress|completed|failed|blocked)$",
    )
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: Optional[str] = None


class TaskProgressUpdateRequest(BaseModel):
    """Request structure for updating an existing task progress entry."""

    stage: Optional[str] = None
    status: Optional[str] = Field(
        None, pattern="^(pending|in_progress|completed|failed|blocked)$"
    )
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    notes: Optional[str] = None


class TaskProgressListRequest(BaseModel):
    """Request structure for listing task progress entries."""

    session_id: Optional[str] = None
    task_name: Optional[str] = None
    status: Optional[str] = Field(
        None, pattern="^(pending|in_progress|completed|failed|blocked)$"
    )
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

