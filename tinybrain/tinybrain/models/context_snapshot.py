"""Context snapshot model definitions."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContextSnapshot(BaseModel):
    """Represents a snapshot of the LLM's context at a specific point in time."""

    id: str
    session_id: str
    name: str
    context_data: dict[str, Any] = Field(..., description="The actual context data")
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContextSnapshotCreateRequest(BaseModel):
    """Request structure for creating a new context snapshot."""

    session_id: str
    name: str
    context_data: dict[str, Any]
    description: Optional[str] = None


class ContextSnapshotUpdateRequest(BaseModel):
    """Request structure for updating an existing context snapshot."""

    name: Optional[str] = None
    context_data: Optional[dict[str, Any]] = None
    description: Optional[str] = None


class ContextSnapshotListRequest(BaseModel):
    """Request structure for listing context snapshots."""

    session_id: Optional[str] = None
    query: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

