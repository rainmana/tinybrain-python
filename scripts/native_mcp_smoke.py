"""Run a repeatable TinyBrain MCP smoke test against an isolated CogDB store.

This exercises the FastMCP tool boundary with `mcp.call_tool`, while avoiding
the user's configured TinyBrain database.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any

import tinybrain.mcp as tinybrain_mcp
from tinybrain.database import Database

EXPECTED_TOOLS = {
    "batch_create_memories",
    "batch_delete_memories",
    "calculate_similarity",
    "check_duplicates",
    "check_high_priority_memories",
    "cleanup_low_priority_memories",
    "cleanup_orphan_relationships",
    "cleanup_old_memories",
    "cleanup_unused_memories",
    "create_relationship",
    "create_session",
    "delete_session",
    "export_session_data",
    "find_similar_memories",
    "get_notifications",
    "get_system_diagnostics",
    "mark_notification_read",
    "search_memories",
    "semantic_search",
}


async def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    result = await tinybrain_mcp.mcp.call_tool(name, arguments or {})
    return result.structured_content


def unwrap_result(value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"result"}:
        return value["result"]
    return value


async def main() -> None:
    tool_names = {tool.name for tool in await tinybrain_mcp.mcp.list_tools()}
    missing = sorted(EXPECTED_TOOLS - tool_names)
    if missing:
        raise AssertionError(f"Missing expected MCP tools: {missing}")

    tmp = Path(tempfile.mkdtemp(prefix="tinybrain-mcp-smoke-"))
    old_db = tinybrain_mcp.db
    database = Database(tmp / "smoke")
    await database.initialize()
    tinybrain_mcp.db = database

    try:
        session = await call_tool(
            "create_session",
            {"name": "TinyBrain MCP Smoke", "task_type": "general"},
        )
        session_id = session["id"]

        created = await call_tool(
            "batch_create_memories",
            {
                "session_id": session_id,
                "memories": [
                    {
                        "title": "Smoke SQL Injection",
                        "content": "Login form has SQL injection through username parameter",
                        "category": "vulnerability",
                        "priority": 9,
                        "confidence": 0.95,
                        "tags": ["smoke", "sql-injection", "auth"],
                    },
                    {
                        "title": "Smoke SQL Injection Variant",
                        "content": "Authentication login SQL injection via username input",
                        "category": "vulnerability",
                        "priority": 8,
                        "confidence": 0.9,
                        "tags": ["smoke", "sql-injection", "auth"],
                    },
                ],
            },
        )
        assert created["created_count"] == 2
        first_id = created["created"][0]["id"]
        second_id = created["created"][1]["id"]

        search = await call_tool(
            "search_memories",
            {"session_id": session_id, "query": "SQL injection username"},
        )
        search = unwrap_result(search)
        assert len(search) == 2

        notifications = unwrap_result(await call_tool("get_notifications", {"session_id": session_id}))
        assert len(notifications) == 2
        marked = await call_tool(
            "mark_notification_read",
            {"notification_id": notifications[0]["id"], "read": True},
        )
        assert marked["success"] is True

        relationship = await call_tool(
            "create_relationship",
            {
                "source_memory_id": first_id,
                "target_memory_id": second_id,
                "relationship_type": "related_to",
            },
        )
        assert relationship["status"] == "created"

        similar = await call_tool(
            "find_similar_memories",
            {"memory_id": first_id, "session_id": session_id, "threshold": 0.2},
        )
        assert similar["count"] >= 1

        duplicates = await call_tool(
            "check_duplicates",
            {"session_id": session_id, "threshold": 0.5},
        )
        assert duplicates["count"] >= 1

        cleanup = await call_tool(
            "cleanup_low_priority_memories",
            {"session_id": session_id, "max_priority": 2},
        )
        assert cleanup["dry_run"] is True

        exported = await call_tool("export_session_data", {"session_id": session_id})
        assert len(exported["relationships"]) == 1

        deleted = await call_tool("delete_session", {"session_id": session_id})
        assert deleted["success"] is True

        diagnostics = await call_tool("get_system_diagnostics")
        assert diagnostics["counts"] == {
            "sessions": 0,
            "memories": 0,
            "relationships": 0,
            "notifications": 0,
        }

        print(f"TinyBrain MCP smoke passed with {len(tool_names)} registered tools")
    finally:
        tinybrain_mcp.db = old_db
        await database.close()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
