# TinyBrain Python Implementation

## Current Implementation

TinyBrain Python is implemented as a FastMCP server backed by local CogDB graph storage. The active CLI entrypoint imports `tinybrain.mcp`, which currently exposes 38 tools for memory management, security assessment context, local similarity analysis, batch operations, import/export, notifications, templates, and diagnostics.

## Core Components

1. **Models**
   - Pydantic models define sessions, memories, relationships, notifications, task status enums, content types, and security categories.

2. **Storage**
   - The active outer `tinybrain.database.Database` class stores entities in CogDB.
   - Memories, sessions, relationships, and notifications are persisted as graph entities.
   - Relationship listing and notification read-state updates are implemented for export/import and notification workflows.

3. **MCP Server**
   - `tinybrain.mcp` owns the active FastMCP server.
   - Tool registration has been smoke-tested through `mcp.list_tools()`.
   - Tool execution has been smoke-tested through `mcp.call_tool()` against an isolated temporary CogDB database.

4. **Similarity And Search**
   - `calculate_similarity` uses deterministic token cosine similarity.
   - `generate_embedding` returns deterministic hashed token vectors for offline matching and test stability.
   - `semantic_search`, `find_similar_memories`, and duplicate checks use those local signals without calling external model providers.

5. **Portability And Context**
   - `export_session_data` and `import_session_data` move session data, memories, and relationships between stores.
   - `get_context_summary` produces compact, high-signal context packets for LLM coding and security agents.
   - `get_detailed_memory_info` returns a memory with related and similar entries.

6. **Security Templates**
   - Built-in templates cover common web vulnerability, MITRE technique, CVE/CWE mapping, and hypothesis workflows.
   - Templates preserve the raw memory entry while providing consistent structure for downstream retrieval.

## Validation

Run the full test suite:

```bash
uv run pytest
```

Run scoped lint checks for the touched parity code:

```bash
uv run ruff check --select F,I,ARG tinybrain/database/__init__.py tinybrain/mcp/__init__.py tests/test_mcp_parity_tools.py
```

The current pass was verified with:

- Full pytest suite: 54 tests passing
- Scoped Ruff checks: passing
- Live FastMCP registration and `call_tool` smoke test: passing

## Storage Roadmap

CogDB remains the right primary store for the memory graph. DuckDB should be evaluated as a sidecar for large analytical security datasets:

- CVE/NVD
- CWE
- MITRE ATT&CK
- Atomic Red Team
- OWASP
- Custom in-house frameworks

The removed mempalace experiment should be revisited later as a possible entity-memory technology once it can be tested cleanly for accuracy, data hygiene, and agent ergonomics.

## Librarian Agent Direction

The proposed librarian agent should keep raw observations immutable and store any derived links, tags, confidence adjustments, or framework mappings separately. That keeps evidence clean while still letting the agent catalog, connect, and summarize assessment context.
