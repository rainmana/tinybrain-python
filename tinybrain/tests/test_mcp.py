"""Tests for MCP server."""

import pytest
from tinybrain.mcp.server import create_mcp_server, get_database


def test_create_mcp_server():
    """Test creating MCP server."""
    mcp = create_mcp_server()
    assert mcp is not None


def test_get_database():
    """Test getting database instance."""
    db = get_database()
    assert db is not None

