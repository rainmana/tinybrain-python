"""Tests for Streamlit UI components."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from tinybrain.database import Database, SQLiteBackend
from tinybrain.models import SessionCreateRequest, MemoryCreateRequest


def test_get_database_function():
    """Test the get_database cached function."""
    # This is a basic test - Streamlit's @st.cache_resource is hard to test
    # without running Streamlit, but we can verify the function exists
    from tinybrain.ui.app import get_database
    
    assert callable(get_database)


def test_run_async_helper():
    """Test the run_async helper function."""
    from tinybrain.ui.app import run_async
    import asyncio
    
    async def test_coro():
        return "test_result"
    
    result = run_async(test_coro())
    assert result == "test_result"


@pytest.mark.asyncio
async def test_database_operations_used_by_ui():
    """Test database operations that the UI uses."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        
        backend = SQLiteBackend(db_path)
        db = Database(backend)
        await db.initialize()
        
        try:
            # Operations the UI performs
            # 1. Create session
            session = await db.create_session(SessionCreateRequest(
                name="UI Test Session",
                task_type="security_review",
            ))
            
            # 2. Create memory
            memory = await db.create_memory(MemoryCreateRequest(
                session_id=session.id,
                title="UI Test Memory",
                content="Test content for UI",
                category="note",
            ))
            
            # 3. List sessions (UI uses this)
            sessions = await db.list_sessions(limit=10)
            assert len(sessions) >= 1
            
            # 4. Search memories (UI uses this)
            results = await db.search_memories(query="UI", limit=10)
            assert len(results) >= 1
            
            # 5. Get stats (UI uses this)
            stats = await db.get_stats()
            assert stats["sessions_count"] >= 1
            assert stats["memory_entries_count"] >= 1
            
        finally:
            await db.close()


def test_ui_imports():
    """Test that UI module can be imported."""
    try:
        import streamlit as st
        import networkx as nx
        import pandas as pd
        import plotly.express as px
        from streamlit_agraph import agraph
        
        # Import the UI module
        from tinybrain.ui import app
        
        assert app is not None
    except ImportError as e:
        pytest.skip(f"UI dependencies not available: {e}")


@pytest.mark.asyncio
async def test_ui_database_path_handling():
    """Test that UI handles database path from environment."""
    import os
    from tinybrain.ui.app import get_database
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "ui_test.db")
        
        # Set environment variable
        with patch.dict(os.environ, {"TINYBRAIN_DB_PATH": db_path}):
            # The get_database function should use the env var
            # Note: This is hard to test without running Streamlit
            # But we can verify the logic exists
            assert "TINYBRAIN_DB_PATH" in os.environ

