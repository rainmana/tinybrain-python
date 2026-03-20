"""End-to-end MCP server test via FastMCP Client protocol."""

import asyncio
import importlib
import json
import os
import shutil
import tempfile

tmpdir = tempfile.mkdtemp()
os.environ["TINYBRAIN_COG_PATH_PREFIX"] = tmpdir
os.environ["TINYBRAIN_COG_HOME"] = "test_mcp"

import tinybrain.config

importlib.reload(tinybrain.config)
import tinybrain.mcp as mcp_module

mcp_module.db = None

from fastmcp import Client


async def test_mcp():
    print("=" * 60)
    print("MCP END-TO-END TEST (via FastMCP Client)")
    print("=" * 60)
    errors = []

    async with Client(mcp_module.mcp) as client:

        def call(name, args=None):
            return client.call_tool(name, args or {})

        def d(result):
            return result.data if result.data is not None else json.loads(result.content[0].text)

        # 1. health_check
        print("\n--- health_check ---")
        r = d(await call("health_check"))
        print(f"  {r}")
        assert r["status"] == "healthy", "health_check not healthy"

        # 2. create_session
        print("\n--- create_session ---")
        r = d(
            await call(
                "create_session",
                {
                    "name": "Pentest Demo",
                    "task_type": "penetration_test",
                    "description": "Testing CogDB via MCP",
                },
            )
        )
        print(f"  {r}")
        assert "error" not in r, f"create_session error: {r}"
        session_id = r["id"]

        # 3. get_session
        print("\n--- get_session ---")
        r = d(await call("get_session", {"session_id": session_id}))
        print(f"  name={r['name']}, task_type={r['task_type']}, status={r['status']}")
        assert r["name"] == "Pentest Demo"

        # 4. list_sessions
        print("\n--- list_sessions ---")
        r = d(await call("list_sessions"))
        print(f"  count={len(r)}")
        assert len(r) >= 1, "list_sessions empty"

        # 5. store_memory (x3)
        print("\n--- store_memory (x3) ---")
        mem_ids = []
        memories = [
            {
                "title": "SQL Injection in login",
                "content": "Found blind SQLi in /login via username param",
                "category": "vulnerability",
                "priority": 9,
                "confidence": 0.95,
                "tags": ["sqli", "auth", "critical"],
            },
            {
                "title": "XSS in search bar",
                "content": "Reflected XSS via search parameter",
                "category": "vulnerability",
                "priority": 7,
                "confidence": 0.8,
                "tags": ["xss", "input-validation"],
            },
            {
                "title": "Nmap scan results",
                "content": "Port 22, 80, 443 open on 10.0.0.1",
                "category": "finding",
                "priority": 3,
                "confidence": 1.0,
                "tags": ["recon", "nmap"],
            },
        ]
        for md in memories:
            r = d(await call("store_memory", {"session_id": session_id, **md}))
            print(f"  Created: id={r.get('id')}")
            assert "error" not in r, f"store_memory error: {r}"
            mem_ids.append(r["id"])

        # 6. get_memory
        print("\n--- get_memory ---")
        r = d(await call("get_memory", {"memory_id": mem_ids[0]}))
        print(f"  title={r['title']}, priority={r['priority']}, tags={r['tags']}")
        assert r["title"] == "SQL Injection in login"

        # 7. search_memories
        print("\n--- search_memories ---")
        r = d(await call("search_memories", {"query": "sqli"}))
        print(f"  query='sqli' -> {len(r)} results")
        assert len(r) >= 1, "search for sqli found nothing"

        r = d(await call("search_memories", {"category": "vulnerability"}))
        print(f"  category='vulnerability' -> {len(r)} results")
        assert len(r) == 2, f"expected 2 vulnerabilities, got {len(r)}"

        r = d(await call("search_memories", {"min_priority": 8}))
        print(f"  min_priority=8 -> {len(r)} results")
        assert len(r) == 1, f"expected 1 high-pri, got {len(r)}"

        # 8. update_memory
        print("\n--- update_memory ---")
        r = d(
            await call(
                "update_memory",
                {"memory_id": mem_ids[1], "title": "XSS CONFIRMED", "priority": 8},
            )
        )
        print(f"  success={r.get('success')}")
        assert r.get("success"), "update_memory failed"

        r = d(await call("get_memory", {"memory_id": mem_ids[1]}))
        print(f"  verified: title={r['title']}, priority={r['priority']}")
        assert "CONFIRMED" in r["title"], "update did not persist"

        # 9. create_relationship
        print("\n--- create_relationship ---")
        r = d(
            await call(
                "create_relationship",
                {
                    "source_memory_id": mem_ids[0],
                    "target_memory_id": mem_ids[1],
                    "relationship_type": "related_to",
                    "strength": 0.8,
                    "description": "Both are web vulns",
                },
            )
        )
        print(f"  {r}")
        assert "error" not in r, f"create_relationship error: {r}"

        # 10. get_related_memories
        print("\n--- get_related_memories ---")
        r = d(await call("get_related_memories", {"memory_id": mem_ids[0]}))
        print(f"  related count={len(r)}")
        assert len(r) >= 1, "get_related_memories empty"

        # 11. get_notifications
        print("\n--- get_notifications ---")
        r = d(await call("get_notifications", {"session_id": session_id}))
        print(f"  notifications={len(r)}")
        assert len(r) >= 1, "no notification for high-priority memory"

        # 12. get_popular_tags
        print("\n--- get_popular_tags ---")
        r = d(await call("get_popular_tags", {"session_id": session_id}))
        print(f"  unique_tags={r['total_unique_tags']}, top={r['tags'][:3]}")
        assert r["total_unique_tags"] >= 1, "no tags found"

        # 13. find_memories_by_tags
        print("\n--- find_memories_by_tags ---")
        r = d(await call("find_memories_by_tags", {"tags": ["sqli", "xss"]}))
        print(f"  any(sqli,xss) -> {len(r)} matches")
        assert len(r) >= 2, f"expected >=2, got {len(r)}"

        r = d(
            await call(
                "find_memories_by_tags",
                {"tags": ["sqli", "auth"], "match_all": True},
            )
        )
        print(f"  all(sqli,auth) -> {len(r)} matches")
        assert len(r) == 1, f"expected 1, got {len(r)}"

        # 14. suggest_related_by_tags
        print("\n--- suggest_related_by_tags ---")
        r = d(await call("suggest_related_by_tags", {"memory_id": mem_ids[0]}))
        print(
            f"  total_found={r['total_found']}, source_tags={r['source_tags']}"
        )

        # 15. get_memory_stats
        print("\n--- get_memory_stats ---")
        r = d(await call("get_memory_stats", {"session_id": session_id}))
        print(f"  total={r['total_memories']}, by_category={r['by_category']}")
        print(
            f"  high_pri={r['high_priority_count']}, avg_conf={r['average_confidence']}"
        )
        assert r["total_memories"] == 3, f"expected 3, got {r['total_memories']}"

        # 16. delete_memory
        print("\n--- delete_memory ---")
        r = d(await call("delete_memory", {"memory_id": mem_ids[2]}))
        print(f"  success={r.get('success')}")
        assert r.get("success"), "delete failed"

        r_raw = await call("get_memory", {"memory_id": mem_ids[2]})
        is_gone = (r_raw.data is None) or (not r_raw.content)
        assert is_gone, "deleted memory still exists"
        print("  verified: memory deleted")

        # 17-20. Discovery tools
        print("\n--- list_memory_categories ---")
        r = d(await call("list_memory_categories"))
        print(f"  {len(r['categories'])} categories")

        print("\n--- list_task_types ---")
        r = d(await call("list_task_types"))
        print(f"  {len(r['task_types'])} task types")

        print("\n--- list_relationship_types ---")
        r = d(await call("list_relationship_types"))
        print(f"  {len(r['relationship_types'])} relationship types")

        print("\n--- get_tinybrain_help ---")
        r = d(await call("get_tinybrain_help"))
        print(f"  version={r['version']}")

    return errors


try:
    errors = asyncio.run(test_mcp())
    print("\n" + "=" * 60)
    if errors:
        print(f"FAILURES ({len(errors)}):")
        for e in errors:
            print(f"  X {e}")
    else:
        print("ALL 20 MCP TOOLS PASSED - FULL E2E VIA MCP PROTOCOL")
    print("=" * 60)
except AssertionError as e:
    print(f"\n{'=' * 60}")
    print(f"ASSERTION FAILED: {e}")
    print("=" * 60)
except Exception as e:
    print(f"\n{'=' * 60}")
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
    print("=" * 60)
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
