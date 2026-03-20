"""Tests for CogDB database backend (inner layer)."""

import pytest
import tempfile
import shutil
from pathlib import Path

from tinybrain.database import Database, CogDBBackend
from tinybrain.models.memory import MemoryCreateRequest, MemoryUpdateRequest
from tinybrain.models.session import SessionCreateRequest, SessionUpdateRequest
from tinybrain.models.relationship import RelationshipCreateRequest, RelationshipType
from tinybrain.models.context_snapshot import ContextSnapshotCreateRequest
from tinybrain.models.task_progress import (
    TaskProgressCreateRequest,
    TaskProgressUpdateRequest,
)


@pytest.fixture
async def db():
    """Create a test database backed by CogDB."""
    tmpdir = tempfile.mkdtemp()

    backend = CogDBBackend(
        cog_home="test_cog",
        cog_path_prefix=tmpdir,
    )
    database = Database(backend)
    await database.initialize()

    yield database

    await database.close()
    shutil.rmtree(tmpdir, ignore_errors=True)


# ── Session Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session(db):
    request = SessionCreateRequest(
        name="Test Session",
        task_type="security_review",
        description="Test description",
    )
    session = await db.create_session(request)
    assert session.id is not None
    assert session.name == "Test Session"
    assert session.task_type == "security_review"
    assert session.status == "active"


@pytest.mark.asyncio
async def test_get_session(db):
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
async def test_get_nonexistent_session(db):
    result = await db.get_session("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_list_sessions(db):
    for i in range(3):
        await db.create_session(
            SessionCreateRequest(name=f"Session {i}", task_type="security_review")
        )
    sessions = await db.list_sessions()
    assert len(sessions) == 3


@pytest.mark.asyncio
async def test_list_sessions_filter_status(db):
    s1 = await db.create_session(
        SessionCreateRequest(name="Active", task_type="security_review")
    )
    await db.update_session(s1.id, SessionUpdateRequest(status="completed"))
    await db.create_session(
        SessionCreateRequest(name="Still Active", task_type="general")
    )

    active = await db.list_sessions(status="active")
    assert len(active) == 1
    assert active[0].name == "Still Active"


@pytest.mark.asyncio
async def test_list_sessions_filter_task_type(db):
    await db.create_session(
        SessionCreateRequest(name="Review", task_type="security_review")
    )
    await db.create_session(
        SessionCreateRequest(name="General", task_type="general")
    )
    results = await db.list_sessions(task_type="general")
    assert len(results) == 1
    assert results[0].name == "General"


@pytest.mark.asyncio
async def test_list_sessions_pagination(db):
    for i in range(5):
        await db.create_session(
            SessionCreateRequest(name=f"Session {i}", task_type="general")
        )
    page = await db.list_sessions(limit=2, offset=1)
    assert len(page) == 2


@pytest.mark.asyncio
async def test_update_session(db):
    session = await db.create_session(
        SessionCreateRequest(name="Original", task_type="security_review")
    )
    updated = await db.update_session(
        session.id, SessionUpdateRequest(name="Updated", status="completed")
    )
    assert updated.name == "Updated"
    assert updated.status == "completed"

    retrieved = await db.get_session(session.id)
    assert retrieved.name == "Updated"
    assert retrieved.status == "completed"


@pytest.mark.asyncio
async def test_delete_session(db):
    session = await db.create_session(
        SessionCreateRequest(name="To Delete", task_type="general")
    )
    result = await db.delete_session(session.id)
    assert result is True

    retrieved = await db.get_session(session.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_nonexistent_session(db):
    result = await db.delete_session("nonexistent")
    assert result is False


# ── Memory Tests ─────────────────────────────────────────────────────


@pytest.fixture
async def db_with_session(db):
    """DB with a pre-created session."""
    session = await db.create_session(
        SessionCreateRequest(name="Test Session", task_type="security_review")
    )
    return db, session


@pytest.mark.asyncio
async def test_create_memory(db_with_session):
    db, session = db_with_session
    memory = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="SQL Injection",
            content="Found SQL injection in login form",
            category="vulnerability",
            priority=8,
            confidence=0.95,
            tags=["sqli", "auth"],
        )
    )
    assert memory.id is not None
    assert memory.title == "SQL Injection"
    assert memory.category == "vulnerability"
    assert memory.priority == 8


@pytest.mark.asyncio
async def test_get_memory(db_with_session):
    db, session = db_with_session
    created = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Test Memory",
            content="Content",
            category="note",
        )
    )
    retrieved = await db.get_memory(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == "Test Memory"
    assert retrieved.access_count >= 1  # get_memory increments access


@pytest.mark.asyncio
async def test_update_memory(db_with_session):
    db, session = db_with_session
    memory = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Original",
            content="Original content",
            category="note",
            priority=3,
        )
    )
    updated = await db.update_memory(
        memory.id,
        MemoryUpdateRequest(title="Updated", priority=9, tags=["new-tag"]),
    )
    assert updated.title == "Updated"
    assert updated.priority == 9
    assert "new-tag" in updated.tags


@pytest.mark.asyncio
async def test_delete_memory(db_with_session):
    db, session = db_with_session
    memory = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="To Delete",
            content="Content",
            category="note",
        )
    )
    result = await db.delete_memory(memory.id)
    assert result is True
    assert await db.get_memory(memory.id) is None


@pytest.mark.asyncio
async def test_search_memories_by_session(db_with_session):
    db, session = db_with_session
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Memory A",
            content="Content A",
            category="note",
        )
    )
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Memory B",
            content="Content B",
            category="vulnerability",
        )
    )
    results = await db.search_memories(session_id=session.id)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_memories_by_category(db_with_session):
    db, session = db_with_session
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Vuln",
            content="A vulnerability",
            category="vulnerability",
        )
    )
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Note",
            content="A note",
            category="note",
        )
    )
    results = await db.search_memories(category="vulnerability")
    assert len(results) == 1
    assert results[0].category == "vulnerability"


@pytest.mark.asyncio
async def test_search_memories_by_query(db_with_session):
    db, session = db_with_session
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="SQL Injection",
            content="Found SQL injection vulnerability",
            category="vulnerability",
        )
    )
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="XSS Issue",
            content="Cross-site scripting found",
            category="vulnerability",
        )
    )
    results = await db.search_memories(query="SQL injection")
    assert len(results) >= 1
    assert any("SQL" in m.title for m in results)


@pytest.mark.asyncio
async def test_search_memories_by_priority(db_with_session):
    db, session = db_with_session
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Low",
            content="Low priority",
            category="note",
            priority=2,
        )
    )
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="High",
            content="High priority",
            category="note",
            priority=9,
        )
    )
    results = await db.search_memories(min_priority=7)
    assert len(results) == 1
    assert results[0].priority >= 7


@pytest.mark.asyncio
async def test_search_memories_by_tags(db_with_session):
    db, session = db_with_session
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Tagged",
            content="Has tags",
            category="note",
            tags=["important", "auth"],
        )
    )
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Untagged",
            content="No matching tags",
            category="note",
            tags=["other"],
        )
    )
    results = await db.search_memories(tags=["important"])
    assert len(results) == 1
    assert results[0].title == "Tagged"


# ── Relationship Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_relationship(db_with_session):
    db, session = db_with_session
    mem1 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Vulnerability",
            content="SQL injection",
            category="vulnerability",
        )
    )
    mem2 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Exploit",
            content="Exploit code",
            category="exploit",
        )
    )
    rel = await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem2.id,
            type=RelationshipType.EXPLOITS,
            strength=0.9,
        )
    )
    assert rel.id is not None
    assert rel.type == RelationshipType.EXPLOITS


@pytest.mark.asyncio
async def test_get_relationship(db_with_session):
    db, session = db_with_session
    mem1 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="A",
            content="A",
            category="note",
        )
    )
    mem2 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="B",
            content="B",
            category="note",
        )
    )
    created = await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem2.id,
            type=RelationshipType.RELATED_TO,
        )
    )
    retrieved = await db.get_relationship(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id


@pytest.mark.asyncio
async def test_get_related_memories(db_with_session):
    db, session = db_with_session
    mem1 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Memory 1",
            content="Content 1",
            category="note",
        )
    )
    mem2 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Memory 2",
            content="Content 2",
            category="note",
        )
    )
    await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem2.id,
            type=RelationshipType.RELATED_TO,
        )
    )
    related = await db.get_related_memories(mem1.id)
    assert len(related) > 0
    assert any(m.id == mem2.id for m in related)


@pytest.mark.asyncio
async def test_get_related_memories_by_type(db_with_session):
    db, session = db_with_session
    mem1 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id, title="A", content="A", category="note"
        )
    )
    mem2 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id, title="B", content="B", category="note"
        )
    )
    mem3 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id, title="C", content="C", category="note"
        )
    )
    await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem2.id,
            type=RelationshipType.EXPLOITS,
        )
    )
    await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem3.id,
            type=RelationshipType.REFERENCES,
        )
    )
    exploits = await db.get_related_memories(mem1.id, relationship_type="exploits")
    assert len(exploits) == 1
    assert exploits[0].id == mem2.id


@pytest.mark.asyncio
async def test_delete_relationship(db_with_session):
    db, session = db_with_session
    mem1 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id, title="A", content="A", category="note"
        )
    )
    mem2 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id, title="B", content="B", category="note"
        )
    )
    rel = await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem2.id,
            type=RelationshipType.RELATED_TO,
        )
    )
    result = await db.delete_relationship(rel.id)
    assert result is True

    retrieved = await db.get_relationship(rel.id)
    assert retrieved is None


# ── Context Snapshot Tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_context_snapshot(db_with_session):
    db, session = db_with_session
    snapshot = await db.create_context_snapshot(
        ContextSnapshotCreateRequest(
            session_id=session.id,
            name="Snapshot 1",
            context_data={"key": "value", "nested": {"a": 1}},
            description="Test snapshot",
        )
    )
    assert snapshot.id is not None
    assert snapshot.name == "Snapshot 1"
    assert snapshot.context_data["key"] == "value"


@pytest.mark.asyncio
async def test_get_context_snapshot(db_with_session):
    db, session = db_with_session
    created = await db.create_context_snapshot(
        ContextSnapshotCreateRequest(
            session_id=session.id,
            name="Snapshot",
            context_data={"data": True},
        )
    )
    retrieved = await db.get_context_snapshot(created.id)
    assert retrieved is not None
    assert retrieved.context_data == {"data": True}


@pytest.mark.asyncio
async def test_list_context_snapshots(db_with_session):
    db, session = db_with_session
    for i in range(3):
        await db.create_context_snapshot(
            ContextSnapshotCreateRequest(
                session_id=session.id,
                name=f"Snapshot {i}",
                context_data={"index": i},
            )
        )
    snapshots = await db.list_context_snapshots(session_id=session.id)
    assert len(snapshots) == 3


# ── Task Progress Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_task_progress(db_with_session):
    db, session = db_with_session
    task = await db.create_task_progress(
        TaskProgressCreateRequest(
            session_id=session.id,
            task_name="Scan ports",
            stage="reconnaissance",
            status="in_progress",
            progress_percentage=25.0,
        )
    )
    assert task.id is not None
    assert task.task_name == "Scan ports"
    assert task.status == "in_progress"


@pytest.mark.asyncio
async def test_get_task_progress(db_with_session):
    db, session = db_with_session
    created = await db.create_task_progress(
        TaskProgressCreateRequest(
            session_id=session.id,
            task_name="Test",
            stage="init",
        )
    )
    retrieved = await db.get_task_progress(created.id)
    assert retrieved is not None
    assert retrieved.task_name == "Test"


@pytest.mark.asyncio
async def test_update_task_progress(db_with_session):
    db, session = db_with_session
    task = await db.create_task_progress(
        TaskProgressCreateRequest(
            session_id=session.id,
            task_name="Test",
            stage="init",
            status="pending",
        )
    )
    updated = await db.update_task_progress(
        task.id,
        TaskProgressUpdateRequest(
            status="completed", progress_percentage=100.0, stage="done"
        ),
    )
    assert updated.status == "completed"
    assert updated.progress_percentage == 100.0


@pytest.mark.asyncio
async def test_list_task_progress(db_with_session):
    db, session = db_with_session
    await db.create_task_progress(
        TaskProgressCreateRequest(
            session_id=session.id, task_name="Task 1", stage="init"
        )
    )
    await db.create_task_progress(
        TaskProgressCreateRequest(
            session_id=session.id, task_name="Task 2", stage="init"
        )
    )
    tasks = await db.list_task_progress(session_id=session.id)
    assert len(tasks) == 2


# ── Stats Tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_stats(db_with_session):
    db, session = db_with_session
    await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Test",
            content="Test",
            category="note",
        )
    )
    stats = await db.get_stats()
    assert "sessions_count" in stats
    assert "memory_entries_count" in stats
    assert stats["sessions_count"] >= 1
    assert stats["memory_entries_count"] >= 1


# ── Cascade Delete Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_session_cascades_memories(db):
    session = await db.create_session(
        SessionCreateRequest(name="Cascade Test", task_type="general")
    )
    mem = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id,
            title="Orphan",
            content="Should be deleted",
            category="note",
        )
    )
    await db.delete_session(session.id)

    assert await db.get_session(session.id) is None
    assert await db.get_memory(mem.id) is None


@pytest.mark.asyncio
async def test_delete_memory_cascades_relationships(db_with_session):
    db, session = db_with_session
    mem1 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id, title="A", content="A", category="note"
        )
    )
    mem2 = await db.create_memory(
        MemoryCreateRequest(
            session_id=session.id, title="B", content="B", category="note"
        )
    )
    rel = await db.create_relationship(
        RelationshipCreateRequest(
            source_id=mem1.id,
            target_id=mem2.id,
            type=RelationshipType.RELATED_TO,
        )
    )
    await db.delete_memory(mem1.id)

    assert await db.get_relationship(rel.id) is None


# ── Integration / Full Workflow Tests ────────────────────────────────


@pytest.mark.asyncio
async def test_full_workflow(db):
    """End-to-end: session -> memories -> relationships -> search -> stats."""
    session = await db.create_session(
        SessionCreateRequest(
            name="Full Workflow",
            task_type="security_review",
            description="Integration test",
        )
    )
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
        query="SQL injection", session_id=session.id, limit=10
    )
    assert len(results) >= 2

    related = await db.get_related_memories(mem1.id)
    assert len(related) > 0
    assert any(m.id == mem2.id for m in related)

    stats = await db.get_stats()
    assert stats["sessions_count"] >= 1
    assert stats["memory_entries_count"] >= 2
    assert stats["relationships_count"] >= 1
