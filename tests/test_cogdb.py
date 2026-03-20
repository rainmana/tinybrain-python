"""Comprehensive tests for CogDB database backend.

Tests both the inner CogDBBackend (via tinybrain.tinybrain.database) and
the outer Database class (via tinybrain.database).
"""

import pytest
import shutil
import tempfile
from pathlib import Path

from tinybrain.tinybrain.database.cogdb_backend import CogDBBackend
from tinybrain.tinybrain.database.base import Database as InnerDatabase
from tinybrain.tinybrain.models.memory import MemoryCreateRequest, MemoryUpdateRequest
from tinybrain.tinybrain.models.session import SessionCreateRequest, SessionUpdateRequest
from tinybrain.tinybrain.models.relationship import (
    RelationshipCreateRequest,
    RelationshipType,
)
from tinybrain.tinybrain.models.context_snapshot import ContextSnapshotCreateRequest
from tinybrain.tinybrain.models.task_progress import (
    TaskProgressCreateRequest,
    TaskProgressUpdateRequest,
)


@pytest.fixture
async def db():
    """Create a test CogDB database."""
    tmpdir = tempfile.mkdtemp()
    backend = CogDBBackend(cog_home="test_cog", cog_path_prefix=tmpdir)
    database = InnerDatabase(backend)
    await database.initialize()
    yield database
    await database.close()
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
async def db_with_session(db):
    """DB with a pre-created session."""
    session = await db.create_session(
        SessionCreateRequest(name="Test Session", task_type="security_review")
    )
    return db, session


# ── Session Tests ────────────────────────────────────────────────────


class TestSessions:
    @pytest.mark.asyncio
    async def test_create(self, db):
        session = await db.create_session(
            SessionCreateRequest(
                name="Test Session",
                task_type="security_review",
                description="Test desc",
            )
        )
        assert session.id is not None
        assert session.name == "Test Session"
        assert session.task_type == "security_review"
        assert session.status == "active"

    @pytest.mark.asyncio
    async def test_get(self, db):
        created = await db.create_session(
            SessionCreateRequest(name="Test", task_type="general")
        )
        retrieved = await db.get_session(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, db):
        assert await db.get_session("nope") is None

    @pytest.mark.asyncio
    async def test_list(self, db):
        for i in range(3):
            await db.create_session(
                SessionCreateRequest(name=f"S{i}", task_type="general")
            )
        sessions = await db.list_sessions()
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_list_filter_status(self, db):
        s1 = await db.create_session(
            SessionCreateRequest(name="Active", task_type="general")
        )
        await db.update_session(
            s1.id, SessionUpdateRequest(status="completed")
        )
        await db.create_session(
            SessionCreateRequest(name="Still Active", task_type="general")
        )
        active = await db.list_sessions(status="active")
        assert len(active) == 1
        assert active[0].name == "Still Active"

    @pytest.mark.asyncio
    async def test_list_filter_task_type(self, db):
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
    async def test_list_pagination(self, db):
        for i in range(5):
            await db.create_session(
                SessionCreateRequest(name=f"S{i}", task_type="general")
            )
        page = await db.list_sessions(limit=2, offset=1)
        assert len(page) == 2

    @pytest.mark.asyncio
    async def test_update(self, db):
        session = await db.create_session(
            SessionCreateRequest(name="Original", task_type="general")
        )
        updated = await db.update_session(
            session.id,
            SessionUpdateRequest(name="Updated", status="completed"),
        )
        assert updated.name == "Updated"
        assert updated.status == "completed"

        retrieved = await db.get_session(session.id)
        assert retrieved.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete(self, db):
        session = await db.create_session(
            SessionCreateRequest(name="Del", task_type="general")
        )
        assert await db.delete_session(session.id) is True
        assert await db.get_session(session.id) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db):
        assert await db.delete_session("nope") is False


# ── Memory Tests ─────────────────────────────────────────────────────


class TestMemories:
    @pytest.mark.asyncio
    async def test_create(self, db_with_session):
        db, session = db_with_session
        mem = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="SQL Injection",
                content="Found SQLi in login",
                category="vulnerability",
                priority=8,
                confidence=0.95,
                tags=["sqli", "auth"],
            )
        )
        assert mem.id is not None
        assert mem.title == "SQL Injection"
        assert mem.priority == 8

    @pytest.mark.asyncio
    async def test_get(self, db_with_session):
        db, session = db_with_session
        created = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Test",
                content="Content",
                category="note",
            )
        )
        retrieved = await db.get_memory(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.access_count >= 1

    @pytest.mark.asyncio
    async def test_update(self, db_with_session):
        db, session = db_with_session
        mem = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Old",
                content="Old content",
                category="note",
                priority=3,
            )
        )
        updated = await db.update_memory(
            mem.id,
            MemoryUpdateRequest(title="New", priority=9, tags=["new-tag"]),
        )
        assert updated.title == "New"
        assert updated.priority == 9
        assert "new-tag" in updated.tags

    @pytest.mark.asyncio
    async def test_delete(self, db_with_session):
        db, session = db_with_session
        mem = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Del",
                content="C",
                category="note",
            )
        )
        assert await db.delete_memory(mem.id) is True
        assert await db.get_memory(mem.id) is None

    @pytest.mark.asyncio
    async def test_search_by_session(self, db_with_session):
        db, session = db_with_session
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="A", content="A", category="note"
            )
        )
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="B",
                content="B",
                category="vulnerability",
            )
        )
        results = await db.search_memories(session_id=session.id)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_by_category(self, db_with_session):
        db, session = db_with_session
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Vuln",
                content="V",
                category="vulnerability",
            )
        )
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Note",
                content="N",
                category="note",
            )
        )
        results = await db.search_memories(category="vulnerability")
        assert len(results) == 1
        assert results[0].category == "vulnerability"

    @pytest.mark.asyncio
    async def test_search_by_query(self, db_with_session):
        db, session = db_with_session
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="SQL Injection",
                content="Found SQL injection",
                category="vulnerability",
            )
        )
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="XSS",
                content="Cross-site scripting",
                category="vulnerability",
            )
        )
        results = await db.search_memories(query="SQL injection")
        assert len(results) >= 1
        assert any("SQL" in m.title for m in results)

    @pytest.mark.asyncio
    async def test_search_by_priority(self, db_with_session):
        db, session = db_with_session
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Low",
                content="L",
                category="note",
                priority=2,
            )
        )
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="High",
                content="H",
                category="note",
                priority=9,
            )
        )
        results = await db.search_memories(min_priority=7)
        assert len(results) == 1
        assert results[0].priority >= 7

    @pytest.mark.asyncio
    async def test_search_by_tags(self, db_with_session):
        db, session = db_with_session
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Tagged",
                content="T",
                category="note",
                tags=["important", "auth"],
            )
        )
        await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Other",
                content="O",
                category="note",
                tags=["other"],
            )
        )
        results = await db.search_memories(tags=["important"])
        assert len(results) == 1
        assert results[0].title == "Tagged"


# ── Relationship Tests ───────────────────────────────────────────────


class TestRelationships:
    @pytest.mark.asyncio
    async def test_create(self, db_with_session):
        db, session = db_with_session
        mem1 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Vuln",
                content="SQLi",
                category="vulnerability",
            )
        )
        mem2 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="Exploit",
                content="Code",
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
    async def test_get(self, db_with_session):
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
    async def test_get_related_memories(self, db_with_session):
        db, session = db_with_session
        mem1 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="M1",
                content="C1",
                category="note",
            )
        )
        mem2 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id,
                title="M2",
                content="C2",
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
    async def test_get_related_by_type(self, db_with_session):
        db, session = db_with_session
        m1 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="A", content="A", category="note"
            )
        )
        m2 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="B", content="B", category="note"
            )
        )
        m3 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="C", content="C", category="note"
            )
        )
        await db.create_relationship(
            RelationshipCreateRequest(
                source_id=m1.id,
                target_id=m2.id,
                type=RelationshipType.EXPLOITS,
            )
        )
        await db.create_relationship(
            RelationshipCreateRequest(
                source_id=m1.id,
                target_id=m3.id,
                type=RelationshipType.REFERENCES,
            )
        )
        exploits = await db.get_related_memories(
            m1.id, relationship_type="exploits"
        )
        assert len(exploits) == 1
        assert exploits[0].id == m2.id

    @pytest.mark.asyncio
    async def test_delete(self, db_with_session):
        db, session = db_with_session
        m1 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="A", content="A", category="note"
            )
        )
        m2 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="B", content="B", category="note"
            )
        )
        rel = await db.create_relationship(
            RelationshipCreateRequest(
                source_id=m1.id,
                target_id=m2.id,
                type=RelationshipType.RELATED_TO,
            )
        )
        assert await db.delete_relationship(rel.id) is True
        assert await db.get_relationship(rel.id) is None


# ── Context Snapshot Tests ───────────────────────────────────────────


class TestSnapshots:
    @pytest.mark.asyncio
    async def test_create(self, db_with_session):
        db, session = db_with_session
        snap = await db.create_context_snapshot(
            ContextSnapshotCreateRequest(
                session_id=session.id,
                name="Snap 1",
                context_data={"key": "value", "nested": {"a": 1}},
            )
        )
        assert snap.id is not None
        assert snap.context_data["key"] == "value"

    @pytest.mark.asyncio
    async def test_get(self, db_with_session):
        db, session = db_with_session
        created = await db.create_context_snapshot(
            ContextSnapshotCreateRequest(
                session_id=session.id,
                name="S",
                context_data={"x": True},
            )
        )
        retrieved = await db.get_context_snapshot(created.id)
        assert retrieved is not None
        assert retrieved.context_data == {"x": True}

    @pytest.mark.asyncio
    async def test_list(self, db_with_session):
        db, session = db_with_session
        for i in range(3):
            await db.create_context_snapshot(
                ContextSnapshotCreateRequest(
                    session_id=session.id,
                    name=f"S{i}",
                    context_data={"i": i},
                )
            )
        snaps = await db.list_context_snapshots(session_id=session.id)
        assert len(snaps) == 3


# ── Task Progress Tests ──────────────────────────────────────────────


class TestTasks:
    @pytest.mark.asyncio
    async def test_create(self, db_with_session):
        db, session = db_with_session
        task = await db.create_task_progress(
            TaskProgressCreateRequest(
                session_id=session.id,
                task_name="Scan",
                stage="recon",
                status="in_progress",
                progress_percentage=25.0,
            )
        )
        assert task.id is not None
        assert task.task_name == "Scan"

    @pytest.mark.asyncio
    async def test_get(self, db_with_session):
        db, session = db_with_session
        created = await db.create_task_progress(
            TaskProgressCreateRequest(
                session_id=session.id,
                task_name="T",
                stage="init",
            )
        )
        retrieved = await db.get_task_progress(created.id)
        assert retrieved is not None
        assert retrieved.task_name == "T"

    @pytest.mark.asyncio
    async def test_update(self, db_with_session):
        db, session = db_with_session
        task = await db.create_task_progress(
            TaskProgressCreateRequest(
                session_id=session.id,
                task_name="T",
                stage="init",
                status="pending",
            )
        )
        updated = await db.update_task_progress(
            task.id,
            TaskProgressUpdateRequest(
                status="completed",
                progress_percentage=100.0,
                stage="done",
            ),
        )
        assert updated.status == "completed"
        assert updated.progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_list(self, db_with_session):
        db, session = db_with_session
        await db.create_task_progress(
            TaskProgressCreateRequest(
                session_id=session.id, task_name="T1", stage="init"
            )
        )
        await db.create_task_progress(
            TaskProgressCreateRequest(
                session_id=session.id, task_name="T2", stage="init"
            )
        )
        tasks = await db.list_task_progress(session_id=session.id)
        assert len(tasks) == 2


# ── Stats ────────────────────────────────────────────────────────────


class TestStats:
    @pytest.mark.asyncio
    async def test_get_stats(self, db_with_session):
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
        assert stats["sessions_count"] >= 1
        assert stats["memory_entries_count"] >= 1


# ── Cascade Deletes ──────────────────────────────────────────────────


class TestCascadeDeletes:
    @pytest.mark.asyncio
    async def test_delete_session_cascades_memories(self, db):
        session = await db.create_session(
            SessionCreateRequest(name="Cascade", task_type="general")
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
    async def test_delete_memory_cascades_relationships(self, db_with_session):
        db, session = db_with_session
        m1 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="A", content="A", category="note"
            )
        )
        m2 = await db.create_memory(
            MemoryCreateRequest(
                session_id=session.id, title="B", content="B", category="note"
            )
        )
        rel = await db.create_relationship(
            RelationshipCreateRequest(
                source_id=m1.id,
                target_id=m2.id,
                type=RelationshipType.RELATED_TO,
            )
        )
        await db.delete_memory(m1.id)
        assert await db.get_relationship(rel.id) is None


# ── Full Integration Test ────────────────────────────────────────────


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow(self, db):
        session = await db.create_session(
            SessionCreateRequest(
                name="Full Workflow",
                task_type="security_review",
                description="End-to-end test",
            )
        )

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

        results = await db.search_memories(
            query="SQL injection", session_id=session.id
        )
        assert len(results) >= 2

        related = await db.get_related_memories(mem1.id)
        assert any(m.id == mem2.id for m in related)

        stats = await db.get_stats()
        assert stats["sessions_count"] >= 1
        assert stats["memory_entries_count"] >= 2
        assert stats["relationships_count"] >= 1
