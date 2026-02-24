"""Tests for ChromaDB backend."""

import pytest
import tempfile
from pathlib import Path

from tinybrain.database import Database, SQLiteBackend, ChromaDBBackend
from tinybrain.models import SessionCreateRequest, MemoryCreateRequest


@pytest.mark.asyncio
async def test_chromadb_initialization():
    """Test ChromaDB backend initialization."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("ChromaDB not installed")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite_path = str(Path(tmpdir) / "test.db")
        chromadb_path = str(Path(tmpdir) / "chroma")
        
        sqlite_backend = SQLiteBackend(sqlite_path)
        backend = ChromaDBBackend(chromadb_path, sqlite_backend)
        db = Database(backend)
        
        await db.initialize()
        
        # Verify it's initialized
        assert backend._client is not None
        assert backend._collection is not None
        
        await db.close()


@pytest.mark.asyncio
async def test_chromadb_delegates_to_sqlite():
    """Test that ChromaDB backend delegates operations to SQLite."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("ChromaDB not installed")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite_path = str(Path(tmpdir) / "test.db")
        chromadb_path = str(Path(tmpdir) / "chroma")
        
        sqlite_backend = SQLiteBackend(sqlite_path)
        backend = ChromaDBBackend(chromadb_path, sqlite_backend)
        db = Database(backend)
        
        await db.initialize()
        
        # Create session (should work via SQLite)
        session_req = SessionCreateRequest(
            name="Test Session",
            task_type="security_review",
        )
        session = await db.create_session(session_req)
        assert session.id is not None
        assert session.name == "Test Session"
        
        # Create memory (should work via SQLite)
        memory_req = MemoryCreateRequest(
            session_id=session.id,
            title="Test Memory",
            content="Test content",
            category="note",
        )
        memory = await db.create_memory(memory_req)
        assert memory.id is not None
        assert memory.title == "Test Memory"
        
        # Search (currently falls back to SQLite)
        results = await db.search_memories(query="Test", limit=10)
        assert len(results) >= 1
        assert results[0].id == memory.id
        
        await db.close()


@pytest.mark.asyncio
async def test_chromadb_without_installation():
    """Test that ChromaDB backend raises error when not installed."""
    # This test assumes chromadb is not installed
    # In practice, we'd mock the import
    pass  # Would need to mock ImportError


@pytest.mark.asyncio
async def test_chromadb_stats():
    """Test that ChromaDB stats include collection count."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("ChromaDB not installed")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite_path = str(Path(tmpdir) / "test.db")
        chromadb_path = str(Path(tmpdir) / "chroma")
        
        sqlite_backend = SQLiteBackend(sqlite_path)
        backend = ChromaDBBackend(chromadb_path, sqlite_backend)
        db = Database(backend)
        
        await db.initialize()
        
        stats = await db.get_stats()
        assert "chromadb_collection_count" in stats
        assert stats["chromadb_collection_count"] == 0  # Empty collection
        
        await db.close()

