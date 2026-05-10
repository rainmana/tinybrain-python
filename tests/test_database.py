"""Tests for TinyBrain outer database layer (CogDB)."""

import pytest
import shutil
import tempfile
from pathlib import Path

from tinybrain.database import Database
from tinybrain.models import Memory, MemoryCategory, Session, SessionStatus, TaskType


@pytest.fixture
async def db():
    """Create a temporary CogDB database for testing."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test_outer"
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_create_session(db):
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    result = await db.create_session(session)
    assert result.id == "test_session"

    retrieved = await db.get_session("test_session")
    assert retrieved is not None
    assert retrieved.name == "Test Session"


@pytest.mark.asyncio
async def test_create_memory(db):
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    await db.create_session(session)

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

    retrieved = await db.get_memory("test_memory")
    assert retrieved is not None
    assert retrieved.title == "Test Memory"
    assert retrieved.priority == 8


@pytest.mark.asyncio
async def test_search_memories(db):
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    await db.create_session(session)

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

    results = await db.search_memories(session_id="test_session")
    assert len(results) == 5

    results = await db.search_memories(session_id="test_session", min_priority=8)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_update_memory(db):
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    await db.create_session(session)

    memory = Memory(
        id="test_memory",
        session_id="test_session",
        title="Original",
        content="Original content",
        category=MemoryCategory.NOTE,
        priority=3,
    )
    await db.create_memory(memory)

    result = await db.update_memory("test_memory", {"title": "Updated", "priority": 9})
    assert result is True

    retrieved = await db.get_memory("test_memory")
    assert retrieved.title == "Updated"
    assert retrieved.priority == 9


@pytest.mark.asyncio
async def test_delete_memory(db):
    session = Session(
        id="test_session",
        name="Test Session",
        task_type=TaskType.SECURITY_REVIEW,
        status=SessionStatus.ACTIVE,
    )
    await db.create_session(session)

    memory = Memory(
        id="test_memory",
        session_id="test_session",
        title="To Delete",
        content="Content",
        category=MemoryCategory.NOTE,
    )
    await db.create_memory(memory)

    result = await db.delete_memory("test_memory")
    assert result is True
    assert await db.get_memory("test_memory") is None
