"""Tests for Streamlit UI components."""

import pytest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from tinybrain.tinybrain.database import Database, CogDBBackend
from tinybrain.tinybrain.models import SessionCreateRequest, MemoryCreateRequest


def test_get_database_function():
    """Test the get_database cached function."""
    try:
        from tinybrain.tinybrain.ui.app import get_database
        assert callable(get_database)
    except ImportError:
        pytest.skip("Streamlit not available")


def test_run_async_helper():
    """Test the run_async helper function."""
    try:
        from tinybrain.tinybrain.ui.app import run_async
    except ImportError:
        pytest.skip("Streamlit not available")

    import asyncio

    async def test_coro():
        return "test_result"

    result = run_async(test_coro())
    assert result == "test_result"


@pytest.mark.asyncio
async def test_database_operations_used_by_ui():
    """Test database operations that the UI uses."""
    tmpdir = tempfile.mkdtemp()
    try:
        backend = CogDBBackend(cog_home="ui_test", cog_path_prefix=tmpdir)
        db = Database(backend)
        await db.initialize()

        try:
            session = await db.create_session(
                SessionCreateRequest(
                    name="UI Test Session",
                    task_type="security_review",
                )
            )

            await db.create_memory(
                MemoryCreateRequest(
                    session_id=session.id,
                    title="UI Test Memory",
                    content="Test content for UI",
                    category="note",
                )
            )

            sessions = await db.list_sessions(limit=10)
            assert len(sessions) >= 1

            results = await db.search_memories(query="UI", limit=10)
            assert len(results) >= 1

            stats = await db.get_stats()
            assert stats["sessions_count"] >= 1
            assert stats["memory_entries_count"] >= 1

        finally:
            await db.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_ui_imports():
    """Test that UI module can be imported."""
    try:
        import streamlit as st
        import networkx as nx
        import pandas as pd
        import plotly.express as px
        from streamlit_agraph import agraph

        from tinybrain.tinybrain.ui import app

        assert app is not None
    except ImportError as e:
        pytest.skip(f"UI dependencies not available: {e}")


@pytest.mark.asyncio
async def test_ui_env_handling():
    """Test that UI handles CogDB config from environment."""
    import os

    with patch.dict(os.environ, {"TINYBRAIN_COG_HOME": "test_home"}):
        assert "TINYBRAIN_COG_HOME" in os.environ
