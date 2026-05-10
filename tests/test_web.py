"""Tests for web interface."""
import pytest
import asyncio
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from tinybrain.database import Database
from tinybrain.models import Session, Memory, Relationship


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with sample data and return a pre-connected db."""
    db_path = tmp_path / "web_test"

    async def setup():
        db = Database(db_path)
        await db.initialize()

        session = Session(
            id="sess_test123",
            name="Test Security Review",
            description="Test session",
            task_type="security_review",
        )
        await db.create_session(session)

        mem1 = Memory(
            id="mem_test1",
            session_id=session.id,
            title="SQL Injection",
            content="Found SQL injection in login",
            category="vulnerability",
            priority=9,
            confidence=0.95,
            tags=["sql-injection", "auth"],
        )
        await db.create_memory(mem1)

        mem2 = Memory(
            id="mem_test2",
            session_id=session.id,
            title="XSS Found",
            content="Cross-site scripting",
            category="vulnerability",
            priority=7,
            confidence=0.85,
            tags=["xss", "auth"],
        )
        await db.create_memory(mem2)

        rel = Relationship(
            id="rel_test1",
            source_entry_id=mem1.id,
            target_entry_id=mem2.id,
            relationship_type="related_to",
            strength=0.7,
        )
        await db.create_relationship(rel)

        return db

    db = asyncio.run(setup())
    yield db
    asyncio.run(db.close())
    shutil.rmtree(tmp_path, ignore_errors=True)


def _setup_web_client(test_db):
    """Inject the test DB directly into the web module."""
    import tinybrain.web

    tinybrain.web._db = test_db

    from tinybrain.web import app

    return TestClient(app)


@pytest.mark.asyncio
async def test_web_stats(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] >= 1
    assert data["memories"] >= 2


@pytest.mark.asyncio
async def test_web_sessions(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/sessions")
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) >= 1


@pytest.mark.asyncio
async def test_web_session_detail(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/sessions/sess_test123")
    assert response.status_code == 200
    session = response.json()
    assert session["name"] == "Test Security Review"


@pytest.mark.asyncio
async def test_web_session_memories(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/sessions/sess_test123/memories")
    assert response.status_code == 200
    memories = response.json()
    assert len(memories) >= 2


@pytest.mark.asyncio
async def test_web_graph_session(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/graph/session/sess_test123")
    assert response.status_code == 200
    graph = response.json()
    assert len(graph["nodes"]) >= 2


@pytest.mark.asyncio
async def test_web_graph_tags(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/graph/tags")
    assert response.status_code == 200
    graph = response.json()
    assert len(graph["nodes"]) >= 2


@pytest.mark.asyncio
async def test_web_export_session(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/export/session/sess_test123")
    assert response.status_code == 200
    export = response.json()
    assert "session" in export
    assert "memories" in export


@pytest.mark.asyncio
async def test_web_search(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/api/search?q=SQL")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert any("SQL" in r["title"] for r in results)


@pytest.mark.asyncio
async def test_web_index_page(test_db):
    client = _setup_web_client(test_db)
    response = client.get("/")
    assert response.status_code == 200
    assert b"TinyBrain" in response.content
