"""Session model definitions."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Session(BaseModel):
    """Represents a security assessment session."""

    id: str
    name: str
    task_type: str = Field(
        ...,
        description="Type of task",
        pattern="^(security_review|penetration_test|exploit_dev|vulnerability_analysis|threat_modeling|incident_response|general)$",
    )
    status: str = Field(
        default="active",
        description="Session status",
        pattern="^(active|paused|completed|archived)$",
    )
    description: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionCreateRequest(BaseModel):
    """Request structure for creating a new session."""

    name: str
    task_type: str = Field(
        ...,
        pattern="^(security_review|penetration_test|exploit_dev|vulnerability_analysis|threat_modeling|incident_response|general)$",
    )
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class SessionUpdateRequest(BaseModel):
    """Request structure for updating a session."""

    name: Optional[str] = None
    status: Optional[str] = Field(
        None, pattern="^(active|paused|completed|archived)$"
    )
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class SessionListRequest(BaseModel):
    """Request structure for listing sessions."""

    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    status: Optional[str] = Field(None, pattern="^(active|paused|completed|archived)$")
    task_type: Optional[str] = Field(
        None,
        pattern="^(security_review|penetration_test|exploit_dev|vulnerability_analysis|threat_modeling|incident_response|general)$",
    )

