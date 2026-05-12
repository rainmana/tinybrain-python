"""Tests for Go-parity MCP utility tools."""

import shutil
from datetime import datetime, timedelta

import pytest

import tinybrain.mcp as mcp_tools
from tinybrain.database import Database


@pytest.fixture
async def mcp_db(tmp_path):
    database = Database(tmp_path / "mcp_parity")
    await database.initialize()
    old_db = mcp_tools.db
    mcp_tools.db = database
    yield database
    mcp_tools.db = old_db
    await database.close()
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.mark.asyncio
async def test_similarity_and_embedding_are_deterministic():
    first = await mcp_tools.generate_embedding("SQL injection in login form")
    second = await mcp_tools.generate_embedding("SQL injection in login form")
    assert first["embedding"] == second["embedding"]

    similarity = await mcp_tools.calculate_similarity(
        "SQL injection login bypass",
        "login form SQL injection finding",
    )
    assert similarity["similarity"] > 0.5


@pytest.mark.asyncio
async def test_batch_duplicate_summary_and_export(mcp_db):
    _ = mcp_db
    session = await mcp_tools.create_session(
        name="Parity Session",
        task_type="security_review",
    )
    session_id = session["id"]

    created = await mcp_tools.batch_create_memories(
        session_id=session_id,
        memories=[
            {
                "title": "SQL Injection",
                "content": "Login form has SQL injection via username parameter",
                "category": "vulnerability",
                "priority": 9,
                "confidence": 0.95,
                "tags": ["sql-injection", "auth"],
            },
            {
                "title": "SQL Injection",
                "content": "Authentication login SQL injection through username input",
                "category": "vulnerability",
                "priority": 8,
                "confidence": 0.9,
                "tags": ["sql-injection", "auth"],
            },
        ],
    )
    assert created["created_count"] == 2

    duplicates = await mcp_tools.check_duplicates(session_id=session_id)
    assert duplicates["count"] == 1

    summary = await mcp_tools.get_context_summary(session_id=session_id)
    assert summary["memory_count"] == 2
    assert summary["top_tags"][0]["tag"] in {"sql-injection", "auth"}

    exported = await mcp_tools.export_session_data(session_id=session_id)
    assert exported["session"]["id"] == session_id
    assert len(exported["memories"]) == 2


@pytest.mark.asyncio
async def test_search_matches_non_contiguous_query_tokens(mcp_db):
    _ = mcp_db
    session = await mcp_tools.create_session(
        name="Search Session",
        task_type="security_review",
    )
    await mcp_tools.store_memory(
        session_id=session["id"],
        title="SQL Injection Finding",
        content="Login form has SQL injection through the username parameter",
        category="vulnerability",
        priority=8,
        confidence=0.9,
        tags=["auth"],
    )

    results = await mcp_tools.search_memories(
        query="SQL injection username",
        session_id=session["id"],
    )
    assert len(results) == 1
    assert results[0]["title"] == "SQL Injection Finding"


@pytest.mark.asyncio
async def test_batch_create_high_priority_memories_create_notifications(mcp_db):
    _ = mcp_db
    session = await mcp_tools.create_session(
        name="Batch Notifications",
        task_type="penetration_test",
    )

    created = await mcp_tools.batch_create_memories(
        session_id=session["id"],
        memories=[
            {
                "title": "Critical Auth Finding",
                "content": "Synthetic high-priority finding",
                "category": "vulnerability",
                "priority": 9,
                "confidence": 0.95,
                "tags": ["auth"],
            },
            {
                "title": "Low Priority Note",
                "content": "Synthetic low-priority note",
                "category": "note",
                "priority": 3,
                "confidence": 0.9,
            },
        ],
    )
    assert created["created_count"] == 2

    notifications = await mcp_tools.get_notifications(session_id=session["id"])
    assert len(notifications) == 1
    assert notifications[0]["metadata"]["memory_id"] == created["created"][0]["id"]


@pytest.mark.asyncio
async def test_templates_notifications_and_diagnostics(mcp_db):
    _ = mcp_db
    session = await mcp_tools.create_session(
        name="Template Session",
        task_type="penetration_test",
    )

    templates = await mcp_tools.get_security_templates()
    assert "web_vulnerability" in templates["templates"]

    created = await mcp_tools.create_memory_from_template(
        session_id=session["id"],
        template_name="web_vulnerability",
        title="IDOR Finding",
        values={
            "finding": "IDOR in invoice endpoint",
            "asset": "/api/invoices/{id}",
            "evidence": "User A can read User B invoice",
            "impact": "Cross-tenant data exposure",
            "recommendation": "Enforce object-level authorization",
        },
        priority=9,
        confidence=0.9,
        tags=["idor"],
    )
    assert created["status"] == "created"

    notifications = await mcp_tools.get_notifications(session_id=session["id"])
    assert len(notifications) == 1
    marked = await mcp_tools.mark_notification_read(notifications[0]["id"])
    assert marked["success"] is True

    diagnostics = await mcp_tools.get_system_diagnostics()
    assert diagnostics["counts"]["sessions"] == 1
    assert diagnostics["counts"]["memories"] == 1


@pytest.mark.asyncio
async def test_delete_memory_cascades_relationships_and_notifications(mcp_db):
    _ = mcp_db
    session = await mcp_tools.create_session(
        name="Cascade Session",
        task_type="security_review",
    )
    created = await mcp_tools.batch_create_memories(
        session_id=session["id"],
        memories=[
            {
                "title": "Finding",
                "content": "High priority finding",
                "category": "vulnerability",
                "priority": 9,
                "confidence": 0.95,
            },
            {
                "title": "Recommendation",
                "content": "Mitigation",
                "category": "recommendation",
                "priority": 5,
                "confidence": 0.8,
            },
        ],
    )
    source_id = created["created"][0]["id"]
    target_id = created["created"][1]["id"]
    await mcp_tools.create_relationship(
        source_memory_id=source_id,
        target_memory_id=target_id,
        relationship_type="mitigates",
    )

    before = await mcp_tools.get_system_diagnostics()
    assert before["counts"]["relationships"] == 1
    assert before["counts"]["notifications"] == 1

    deleted = await mcp_tools.delete_memory(source_id)
    assert deleted["success"] is True

    after = await mcp_tools.get_system_diagnostics()
    assert after["counts"]["relationships"] == 0
    assert after["counts"]["notifications"] == 0
    assert await mcp_tools.get_related_memories(memory_id=target_id) == []


@pytest.mark.asyncio
async def test_delete_session_cascades_children(mcp_db):
    _ = mcp_db
    session = await mcp_tools.create_session(
        name="Delete Session",
        task_type="general",
    )
    created = await mcp_tools.batch_create_memories(
        session_id=session["id"],
        memories=[
            {
                "title": "Finding",
                "content": "High priority finding",
                "category": "vulnerability",
                "priority": 9,
                "confidence": 0.95,
            },
            {
                "title": "Recommendation",
                "content": "Mitigation",
                "category": "recommendation",
                "priority": 5,
                "confidence": 0.8,
            },
        ],
    )
    await mcp_tools.create_relationship(
        source_memory_id=created["created"][0]["id"],
        target_memory_id=created["created"][1]["id"],
        relationship_type="mitigates",
    )

    deleted = await mcp_tools.delete_session(session["id"])
    assert deleted["success"] is True

    diagnostics = await mcp_tools.get_system_diagnostics()
    assert diagnostics["counts"] == {
        "sessions": 0,
        "memories": 0,
        "relationships": 0,
        "notifications": 0,
    }


@pytest.mark.asyncio
async def test_cleanup_old_memories_defaults_to_dry_run(mcp_db):
    session = await mcp_tools.create_session(
        name="Cleanup Age",
        task_type="general",
    )
    created = await mcp_tools.store_memory(
        session_id=session["id"],
        title="Old finding",
        content="Legacy observation",
        category="finding",
    )
    old_timestamp = (datetime.utcnow() - timedelta(days=60)).isoformat()
    await mcp_db.update_memory(
        created["id"],
        {"created_at": old_timestamp, "accessed_at": old_timestamp},
    )

    dry_run = await mcp_tools.cleanup_old_memories(
        max_age_days=30,
        session_id=session["id"],
    )
    assert dry_run["dry_run"] is True
    assert dry_run["candidate_count"] == 1
    assert dry_run["deleted_count"] == 0
    assert await mcp_tools.get_memory(created["id"]) is not None

    deleted = await mcp_tools.cleanup_old_memories(
        max_age_days=30,
        session_id=session["id"],
        dry_run=False,
    )
    assert deleted["candidate_count"] == 1
    assert deleted["deleted"] == [created["id"]]
    assert await mcp_tools.get_memory(created["id"]) is None


@pytest.mark.asyncio
async def test_cleanup_low_priority_and_unused_memories(mcp_db):
    session = await mcp_tools.create_session(
        name="Cleanup Priority",
        task_type="general",
    )
    old_timestamp = (datetime.utcnow() - timedelta(days=90)).isoformat()

    low = await mcp_tools.store_memory(
        session_id=session["id"],
        title="Low value note",
        content="Can be removed",
        category="note",
        priority=1,
    )
    unused = await mcp_tools.store_memory(
        session_id=session["id"],
        title="Unused context",
        content="Old context",
        category="context",
        priority=5,
    )
    high = await mcp_tools.store_memory(
        session_id=session["id"],
        title="High priority finding",
        content="Keep this",
        category="vulnerability",
        priority=9,
    )
    for memory_id in (low["id"], unused["id"], high["id"]):
        await mcp_db.update_memory(
            memory_id,
            {"created_at": old_timestamp, "accessed_at": old_timestamp},
        )
    await mcp_db.update_memory(high["id"], {"access_count": 2})

    low_priority = await mcp_tools.cleanup_low_priority_memories(
        max_priority=2,
        min_age_days=30,
        session_id=session["id"],
        dry_run=False,
    )
    assert low_priority["deleted"] == [low["id"]]

    unused_cleanup = await mcp_tools.cleanup_unused_memories(
        max_access_count=0,
        min_age_days=30,
        session_id=session["id"],
        dry_run=False,
    )
    assert unused_cleanup["deleted"] == [unused["id"]]
    assert await mcp_tools.get_memory(high["id"]) is not None
