"""Tests for TinyBrain models."""

from datetime import datetime

from tinybrain.models import (
    Memory,
    MemoryCategory,
    Session,
    SessionStatus,
    TaskType,
)


def test_session_creation():
    """Test session model creation."""
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    assert session.id == "test_session"
    assert session.name == "Test Session"
    assert session.task_type == TaskType.SECURITY_REVIEW


def test_memory_creation():
    """Test memory model creation."""
    memory = Memory(
        id="test_memory",
        session_id="test_session",
        title="Test Memory",
        content="Test content",
        category=MemoryCategory.VULNERABILITY,
        priority=8,
        confidence=0.9,
        tags=["test", "vulnerability"],
    )
    assert memory.id == "test_memory"
    assert memory.title == "Test Memory"
    assert memory.priority == 8
    assert memory.confidence == 0.9
    assert "test" in memory.tags
