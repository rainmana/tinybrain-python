"""Tests for database layer."""

import pytest
import tempfile
from pathlib import Path

from tinybrain.database import Database, SQLiteBackend
from tinybrain.models.memory import MemoryCreateRequest
from tinybrain.models.session import SessionCreateRequest
from tinybrain.models.relationship import RelationshipCreateRequest, RelationshipType


@pytest.fixture
async def db():
    """Create a test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    backend = SQLiteBackend(db_path)
    db = Database(backend)
    await db.initialize()
    
    yield db
    
    await db.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_create_session(db):
    """Test creating a session."""
    request = SessionCreateRequest(
        name="Test Session",
        task_type="security_review",
        description="Test description",
    )
    
    session = await db.create_session(request)
    assert session.id is not None
    assert session.name == "Test Session"
    assert session.task_type == "security_review"


@pytest.mark.asyncio
async def test_get_session(db):
    """Test getting a session."""
    request = SessionCreateRequest(
        name="Test Session",
        task_type="security_review",
    )
    
    created = await db.create_session(request)
    retrieved = await db.get_session(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == "Test Session"


@pytest.mark.asyncio
async def test_create_memory(db):
    """Test creating a memory."""
    # Create session first
    session_request = SessionCreateRequest(
        name="Test Session",
        task_type="security_review",
    )
    session = await db.create_session(session_request)
    
    # Create memory
    memory_request = MemoryCreateRequest(
        session_id=session.id,
        title="Test Memory",
        content="Test content",
        category="note",
        priority=5,
        confidence=0.8,
    )
    
    memory = await db.create_memory(memory_request)
    assert memory.id is not None
    assert memory.title == "Test Memory"
    assert memory.category == "note"


@pytest.mark.asyncio
async def test_search_memories(db):
    """Test searching memories."""
    # Create session and memories
    session_request = SessionCreateRequest(
        name="Test Session",
        task_type="security_review",
    )
    session = await db.create_session(session_request)
    
    memory_request = MemoryCreateRequest(
        session_id=session.id,
        title="SQL Injection",
        content="Found SQL injection vulnerability",
        category="vulnerability",
        priority=8,
    )
    await db.create_memory(memory_request)
    
    # Search
    results = await db.search_memories(
        query="SQL injection",
        session_id=session.id,
        limit=10,
    )
    
    assert len(results) > 0
    assert any("SQL" in m.title for m in results)


@pytest.mark.asyncio
async def test_create_relationship(db):
    """Test creating a relationship."""
    # Create session
    session_request = SessionCreateRequest(
        name="Test Session",
        task_type="security_review",
    )
    session = await db.create_session(session_request)
    
    # Create two memories
    mem1_request = MemoryCreateRequest(
        session_id=session.id,
        title="Vulnerability",
        content="SQL injection",
        category="vulnerability",
    )
    mem1 = await db.create_memory(mem1_request)
    
    mem2_request = MemoryCreateRequest(
        session_id=session.id,
        title="Exploit",
        content="Exploit code",
        category="exploit",
    )
    mem2 = await db.create_memory(mem2_request)
    
    # Create relationship
    rel_request = RelationshipCreateRequest(
        source_id=mem1.id,
        target_id=mem2.id,
        type=RelationshipType.EXPLOITS,
        strength=0.9,
    )
    
    relationship = await db.create_relationship(rel_request)
    assert relationship.id is not None
    assert relationship.type == RelationshipType.EXPLOITS


@pytest.mark.asyncio
async def test_get_related_memories(db):
    """Test getting related memories."""
    # Create session
    session_request = SessionCreateRequest(
        name="Test Session",
        task_type="security_review",
    )
    session = await db.create_session(session_request)
    
    # Create memories
    mem1_request = MemoryCreateRequest(
        session_id=session.id,
        title="Memory 1",
        content="Content 1",
        category="note",
    )
    mem1 = await db.create_memory(mem1_request)
    
    mem2_request = MemoryCreateRequest(
        session_id=session.id,
        title="Memory 2",
        content="Content 2",
        category="note",
    )
    mem2 = await db.create_memory(mem2_request)
    
    # Create relationship
    rel_request = RelationshipCreateRequest(
        source_id=mem1.id,
        target_id=mem2.id,
        type=RelationshipType.RELATED_TO,
    )
    await db.create_relationship(rel_request)
    
    # Get related memories
    related = await db.get_related_memories(mem1.id)
    assert len(related) > 0
    assert any(m.id == mem2.id for m in related)


@pytest.mark.asyncio
async def test_get_stats(db):
    """Test getting database statistics."""
    stats = await db.get_stats()
    assert "sessions_count" in stats
    assert "memory_entries_count" in stats
    assert "relationships_count" in stats

