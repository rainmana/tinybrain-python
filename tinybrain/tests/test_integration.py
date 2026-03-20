"""Integration tests for TinyBrain with CogDB backend."""

import pytest
import shutil
import tempfile

from tinybrain.database import Database, CogDBBackend
from tinybrain.models.memory import MemoryCreateRequest
from tinybrain.models.session import SessionCreateRequest
from tinybrain.models.relationship import RelationshipCreateRequest, RelationshipType


@pytest.fixture
async def db():
    """Create a test database."""
    tmpdir = tempfile.mkdtemp()
    backend = CogDBBackend(cog_home="integration_test", cog_path_prefix=tmpdir)
    database = Database(backend)
    await database.initialize()

    yield database

    await database.close()
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_full_workflow(db):
    """Test a complete workflow: session -> memories -> relationships."""
    session_req = SessionCreateRequest(
        name="Integration Test Session",
        task_type="security_review",
        description="Testing full workflow",
    )
    session = await db.create_session(session_req)
    assert session.id is not None

    mem1 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="SQL Injection Vulnerability",
            content="Found SQL injection in login form",
            category="vulnerability",
            priority=9,
            confidence=0.95,
            tags=["sql-injection", "authentication", "critical"],
        )
    )

    mem2 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Exploit Code",
            content="Exploit code for SQL injection",
            category="exploit",
            priority=8,
            confidence=0.9,
            tags=["exploit", "sql-injection"],
        )
    )

    rel = await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem2.id,
            type=RelationshipType.EXPLOITS,
            strength=0.95,
            description="Exploit targets the vulnerability",
        )
    )
    assert rel.id is not None

    results = await db.search_memories(
        query="SQL injection",
        session_id=session.id,
        limit=10,
    )
    assert len(results) >= 2

    related = await db.get_related_memories(mem1.id)
    assert len(related) > 0
    assert any(m.id == mem2.id for m in related)

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

    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="XSS Vulnerability",
            content="Cross-site scripting found",
            category="vulnerability",
            priority=7,
            tags=["xss", "web"],
        )
    )

    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="CSRF Protection",
            content="Implemented CSRF tokens",
            category="recommendation",
            priority=5,
            tags=["csrf", "security"],
        )
    )

    vulns = await db.search_memories(
        category="vulnerability",
        session_id=session.id,
    )
    assert len(vulns) >= 1
    assert all(m.category == "vulnerability" for m in vulns)

    xss_memories = await db.search_memories(
        tags=["xss"],
        session_id=session.id,
    )
    assert len(xss_memories) >= 1

    high_priority = await db.search_memories(
        min_priority=7,
        session_id=session.id,
    )
    assert len(high_priority) >= 1
    assert all(m.priority >= 7 for m in high_priority)
