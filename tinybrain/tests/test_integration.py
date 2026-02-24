"""Integration tests for TinyBrain."""

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
async def test_full_workflow(db):
    """Test a complete workflow: session -> memories -> relationships."""
    # Create session
    session_req = SessionCreateRequest(
        name="Integration Test Session",
        task_type="security_review",
        description="Testing full workflow",
    )
    session = await db.create_session(session_req)
    assert session.id is not None
    
    # Create multiple memories
    mem1 = await db.create_memory(MemoryCreateRequest(
        session_id=session.id,
        title="SQL Injection Vulnerability",
        content="Found SQL injection in login form",
        category="vulnerability",
        priority=9,
        confidence=0.95,
        tags=["sql-injection", "authentication", "critical"],
    ))
    
    mem2 = await db.create_memory(MemoryCreateRequest(
        session_id=session.id,
        title="Exploit Code",
        content="Exploit code for SQL injection",
        category="exploit",
        priority=8,
        confidence=0.9,
        tags=["exploit", "sql-injection"],
    ))
    
    # Create relationship
    rel = await db.create_relationship(RelationshipCreateRequest(
        source_id=mem1.id,
        target_id=mem2.id,
        type=RelationshipType.EXPLOITS,
        strength=0.95,
        description="Exploit targets the vulnerability",
    ))
    assert rel.id is not None
    
    # Search for memories
    results = await db.search_memories(
        query="SQL injection",
        session_id=session.id,
        limit=10,
    )
    assert len(results) >= 2
    
    # Get related memories
    related = await db.get_related_memories(mem1.id)
    assert len(related) > 0
    assert any(m.id == mem2.id for m in related)
    
    # Get stats
    stats = await db.get_stats()
    assert stats["sessions_count"] >= 1
    assert stats["memory_entries_count"] >= 2
    assert stats["relationships_count"] >= 1


@pytest.mark.asyncio
async def test_search_functionality(db):
    """Test various search types."""
    session_req = SessionCreateRequest(
        name="Search Test",
        task_type="security_review",
    )
    session = await db.create_session(session_req)
    
    # Create memories with different categories
    await db.create_memory(MemoryCreateRequest(
        session_id=session.id,
        title="XSS Vulnerability",
        content="Cross-site scripting found",
        category="vulnerability",
        priority=7,
        tags=["xss", "web"],
    ))
    
    await db.create_memory(MemoryCreateRequest(
        session_id=session.id,
        title="CSRF Protection",
        content="Implemented CSRF tokens",
        category="recommendation",
        priority=5,
        tags=["csrf", "security"],
    ))
    
    # Test category search
    vulns = await db.search_memories(
        category="vulnerability",
        session_id=session.id,
    )
    assert len(vulns) >= 1
    assert all(m.category == "vulnerability" for m in vulns)
    
    # Test tag search
    xss_memories = await db.search_memories(
        tags=["xss"],
        session_id=session.id,
    )
    assert len(xss_memories) >= 1
    
    # Test priority filter
    high_priority = await db.search_memories(
        min_priority=7,
        session_id=session.id,
    )
    assert len(high_priority) >= 1
    assert all(m.priority >= 7 for m in high_priority)

