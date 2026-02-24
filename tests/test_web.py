"""Tests for web interface."""
import pytest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from tinybrain.database import Database
from tinybrain.models import Session, Memory, Relationship


@pytest.fixture
def test_db(tmp_path):
    """Create a test database with sample data."""
    async def setup():
        db_path = tmp_path / "test.db"
        db = Database(db_path)
        await db.initialize()
        
        # Create session
        session = Session(
            id="sess_test123",
            name="Test Security Review",
            description="Test session",
            task_type="security_review"
        )
        await db.create_session(session)
        
        # Create memories
        mem1 = Memory(
            id="mem_test1",
            session_id=session.id,
            title="SQL Injection",
            content="Found SQL injection in login",
            category="vulnerability",
            priority=9,
            confidence=0.95,
            tags=["sql-injection", "auth"]
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
            tags=["xss", "auth"]
        )
        await db.create_memory(mem2)
        
        # Create relationship
        rel = Relationship(
            id="rel_test1",
            source_entry_id=mem1.id,
            target_entry_id=mem2.id,
            relationship_type="related_to",
            strength=0.7
        )
        await db.create_relationship(rel)
        
        await db.close()
        return db_path
    
    return asyncio.run(setup())


@pytest.mark.asyncio
async def test_web_stats(test_db, monkeypatch):
    """Test /api/stats endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    # Reset the global db instance
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert data["sessions"] == 1
    assert data["memories"] == 2
    assert data["relationships"] == 1
    assert data["unique_tags"] == 3  # sql-injection, auth, xss
    assert "vulnerability" in data["by_category"]


@pytest.mark.asyncio
async def test_web_sessions(test_db, monkeypatch):
    """Test /api/sessions endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/sessions")
    assert response.status_code == 200
    
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["name"] == "Test Security Review"


@pytest.mark.asyncio
async def test_web_session_detail(test_db, monkeypatch):
    """Test /api/sessions/{id} endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/sessions/sess_test123")
    assert response.status_code == 200
    
    session = response.json()
    assert session["name"] == "Test Security Review"
    assert session["task_type"] == "security_review"


@pytest.mark.asyncio
async def test_web_session_memories(test_db, monkeypatch):
    """Test /api/sessions/{id}/memories endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/sessions/sess_test123/memories")
    assert response.status_code == 200
    
    memories = response.json()
    assert len(memories) == 2
    assert memories[0]["title"] in ["SQL Injection", "XSS Found"]


@pytest.mark.asyncio
async def test_web_graph_session(test_db, monkeypatch):
    """Test /api/graph/session/{id} endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/graph/session/sess_test123")
    assert response.status_code == 200
    
    graph = response.json()
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["nodes"][0]["data"]["category"] == "vulnerability"


@pytest.mark.asyncio
async def test_web_graph_tags(test_db, monkeypatch):
    """Test /api/graph/tags endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/graph/tags")
    assert response.status_code == 200
    
    graph = response.json()
    assert len(graph["nodes"]) >= 2  # At least sql-injection and xss


@pytest.mark.asyncio
async def test_web_export_session(test_db, monkeypatch):
    """Test /api/export/session/{id} endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/export/session/sess_test123")
    assert response.status_code == 200
    
    export = response.json()
    assert "session" in export
    assert "memories" in export
    assert "relationships" in export
    assert len(export["memories"]) == 2
    assert len(export["relationships"]) == 1


@pytest.mark.asyncio
async def test_web_search(test_db, monkeypatch):
    """Test /api/search endpoint."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/api/search?q=SQL")
    assert response.status_code == 200
    
    results = response.json()
    assert len(results) >= 1
    assert any("SQL" in r["title"] for r in results)


@pytest.mark.asyncio
async def test_web_index_page(test_db, monkeypatch):
    """Test that index page loads."""
    monkeypatch.setenv("TINYBRAIN_DB_PATH", str(test_db))
    
    import tinybrain.web
    tinybrain.web._db = None
    
    from tinybrain.web import app
    client = TestClient(app)
    
    response = client.get("/")
    assert response.status_code == 200
    assert b"TinyBrain" in response.content
    assert b"Dashboard" in response.content
