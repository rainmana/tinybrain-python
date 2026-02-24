"""Relationship model definitions."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """Types of relationships between memories."""

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
    """Represents a relationship between two memories."""

    id: str
    source_id: str
    target_id: str
    type: RelationshipType
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Relationship strength 0.0-1.0")
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RelationshipCreateRequest(BaseModel):
    """Request structure for creating a new relationship."""

    source_id: str
    target_id: str
    type: RelationshipType
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    description: Optional[str] = None


class RelationshipUpdateRequest(BaseModel):
    """Request structure for updating an existing relationship."""

    type: Optional[RelationshipType] = None
    strength: Optional[float] = Field(None, ge=0.0, le=1.0)
    description: Optional[str] = None


class RelationshipListRequest(BaseModel):
    """Request structure for listing relationships."""

    source_id: Optional[str] = None
    target_id: Optional[str] = None
    type: Optional[RelationshipType] = None
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

