"""Tests for data models."""

import pytest
from datetime import datetime

from tinybrain.models.memory import Memory, MemoryCreateRequest, MemoryUpdateRequest
from tinybrain.models.session import Session, SessionCreateRequest
from tinybrain.models.relationship import Relationship, RelationshipCreateRequest, RelationshipType
from tinybrain.models.context_snapshot import ContextSnapshot, ContextSnapshotCreateRequest
from tinybrain.models.task_progress import TaskProgress, TaskProgressCreateRequest


class TestMemory:
    """Tests for Memory model."""
    
    def test_memory_creation(self):
        """Test creating a memory."""
        memory = Memory(
            id="test-id",
            session_id="session-1",
            title="Test Memory",
            content="Test content",
            category="note",
        )
        assert memory.id == "test-id"
        assert memory.title == "Test Memory"
        assert memory.category == "note"
        assert memory.priority == 5  # Default
        assert memory.confidence == 0.5  # Default
    
    def test_memory_create_request(self):
        """Test MemoryCreateRequest."""
        request = MemoryCreateRequest(
            session_id="session-1",
            title="Test",
            content="Content",
            category="vulnerability",
            priority=8,
            confidence=0.9,
        )
        assert request.session_id == "session-1"
        assert request.priority == 8
        assert request.confidence == 0.9


class TestSession:
    """Tests for Session model."""
    
    def test_session_creation(self):
        """Test creating a session."""
        session = Session(
            id="session-1",
            name="Test Session",
            task_type="security_review",
        )
        assert session.id == "session-1"
        assert session.name == "Test Session"
        assert session.task_type == "security_review"
        assert session.status == "active"  # Default


class TestRelationship:
    """Tests for Relationship model."""
    
    def test_relationship_creation(self):
        """Test creating a relationship."""
        relationship = Relationship(
            id="rel-1",
            source_id="mem-1",
            target_id="mem-2",
            type=RelationshipType.EXPLOITS,
            strength=0.8,
        )
        assert relationship.id == "rel-1"
        assert relationship.type == RelationshipType.EXPLOITS
        assert relationship.strength == 0.8


class TestContextSnapshot:
    """Tests for ContextSnapshot model."""
    
    def test_context_snapshot_creation(self):
        """Test creating a context snapshot."""
        snapshot = ContextSnapshot(
            id="snapshot-1",
            session_id="session-1",
            name="Test Snapshot",
            context_data={"key": "value"},
        )
        assert snapshot.id == "snapshot-1"
        assert snapshot.context_data == {"key": "value"}


class TestTaskProgress:
    """Tests for TaskProgress model."""
    
    def test_task_progress_creation(self):
        """Test creating a task progress entry."""
        task = TaskProgress(
            id="task-1",
            session_id="session-1",
            task_name="Test Task",
            stage="analysis",
            status="in_progress",
            progress_percentage=50.0,
        )
        assert task.id == "task-1"
        assert task.status == "in_progress"
        assert task.progress_percentage == 50.0

