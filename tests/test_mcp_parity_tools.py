"""Tests for Go-parity MCP utility tools."""

import shutil

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
