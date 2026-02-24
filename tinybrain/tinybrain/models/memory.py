"""Memory model definitions."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Memory(BaseModel):
    """Represents a stored memory entry for security assessments."""

    id: str
    session_id: str
    title: str
    content: str
    category: str = Field(
        ...,
        description="Category of the memory",
        pattern="^(finding|vulnerability|exploit|payload|technique|tool|reference|context|hypothesis|evidence|recommendation|note)$",
    )
    priority: int = Field(default=5, ge=0, le=10, description="Priority level 0-10")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence level 0.0-1.0"
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    source: Optional[str] = Field(default=None, description="Source of the information")
    content_type: str = Field(
        default="text",
        description="Type of content",
        pattern="^(text|code|json|yaml|markdown|binary_ref)$",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0, description="Number of times accessed")

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        """Parse tags from various formats."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [tag.strip() for tag in v.split(",") if tag.strip()]
        return v or []


class MemoryCreateRequest(BaseModel):
    """Request structure for creating a new memory entry."""

    session_id: str
    title: str
    content: str
    category: str = Field(
        ...,
        pattern="^(finding|vulnerability|exploit|payload|technique|tool|reference|context|hypothesis|evidence|recommendation|note)$",
    )
    priority: int = Field(default=5, ge=0, le=10)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    source: Optional[str] = None
    content_type: str = Field(default="text", pattern="^(text|code|json|yaml|markdown|binary_ref)$")


class MemoryUpdateRequest(BaseModel):
    """Request structure for updating an existing memory entry."""

    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = Field(
        None, pattern="^(finding|vulnerability|exploit|payload|technique|tool|reference|context|hypothesis|evidence|recommendation|note)$"
    )
    priority: Optional[int] = Field(None, ge=0, le=10)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[list[str]] = None
    source: Optional[str] = None
    content_type: Optional[str] = Field(
        None, pattern="^(text|code|json|yaml|markdown|binary_ref)$"
    )


class MemorySearchRequest(BaseModel):
    """Request structure for searching memory entries."""

    session_id: Optional[str] = None
    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    source: Optional[str] = None
    min_priority: Optional[int] = Field(None, ge=0, le=10)
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    search_type: str = Field(
        default="semantic",
        pattern="^(semantic|exact|fuzzy|tag|category|relationship)$",
    )
    limit: int = Field(default=20, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

