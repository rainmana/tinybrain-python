"""Tests for TinyBrain database."""

import pytest
from pathlib import Path
import tempfile

from tinybrain.database import Database
from tinybrain.models import Memory, MemoryCategory, Session, SessionStatus, TaskType


@pytest.fixture
async def db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        database = Database(db_path)
        await database.initialize()
        yield database
        await database.close()


@pytest.mark.asyncio
async def test_create_session(db):
    """Test session creation."""
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    result = await db.create_session(session)
    assert result.id == "test_session"

    # Retrieve and verify
    retrieved = await db.get_session("test_session")
    assert retrieved is not None
    assert retrieved.name == "Test Session"


@pytest.mark.asyncio
async def test_create_memory(db):
    """Test memory creation."""
    # Create session first
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    await db.create_session(session)

    # Create memory
    memory = Memory(
        id="test_memory",
        session_id="test_session",
        title="Test Memory",
        content="Test content",
        category=MemoryCategory.VULNERABILITY,
        priority=8,
        confidence=0.9,
        tags=["test"],
    )
    result = await db.create_memory(memory)
    assert result.id == "test_memory"

    # Retrieve and verify
    retrieved = await db.get_memory("test_memory")
    assert retrieved is not None
    assert retrieved.title == "Test Memory"
    assert retrieved.priority == 8


@pytest.mark.asyncio
async def test_search_memories(db):
    """Test memory search."""
    # Create session
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    await db.create_session(session)

    # Create memories
    for i in range(5):
        memory = Memory(
            id=f"test_memory_{i}",
            session_id="test_session",
            title=f"Test Memory {i}",
            content=f"Test content {i}",
            category=MemoryCategory.VULNERABILITY,
            priority=i + 5,
            confidence=0.9,
            tags=["test"],
        )
        await db.create_memory(memory)

    # Search by session
    results = await db.search_memories(session_id="test_session")
    assert len(results) == 5

    # Search by priority
    results = await db.search_memories(session_id="test_session", min_priority=8)
    assert len(results) == 2
