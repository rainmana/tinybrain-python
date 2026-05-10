# TinyBrain Python Implementation - Project Summary

## Overview

TinyBrain Python is a security-focused LLM memory MCP server for security review, penetration testing, exploit development, vulnerability analysis, and related research workflows. It uses FastMCP for the MCP surface, CogDB for local graph storage, Pydantic for runtime validation, Typer for the CLI, and FastAPI for the web UI.

The current active MCP module exposes 38 tools and has been tested through both pytest and live FastMCP `call_tool` smoke checks.

## Technology Stack

- **FastMCP** - MCP protocol server framework
- **CogDB** - Local graph storage for sessions, memories, relationships, and notifications
- **FastAPI** - Web interface
- **Pydantic** - Type-safe models and settings
- **Typer** - CLI commands
- **Loguru** - Structured logging
- **UV** - Dependency and environment workflow
- **pytest / ruff** - Tests and linting

## Project Structure

```text
tinybrain-python/
├── tinybrain/
│   ├── cli.py                # Typer CLI commands
│   ├── config.py             # Pydantic settings
│   ├── log_config.py         # Loguru configuration
│   ├── database/__init__.py  # CogDB-backed storage
│   ├── mcp/__init__.py       # Active FastMCP server and tools
│   ├── models/__init__.py    # Pydantic models
│   ├── services/__init__.py  # Security data downloaders
│   └── web/__init__.py       # FastAPI web interface
├── tests/
├── FEATURE_COMPARISON.md
├── GO_VS_PYTHON.md
├── QUICKSTART.md
└── README.md
```

There is also a nested reference package under `tinybrain/tinybrain/` that contains an inner backend/server implementation used by some tests. The active CLI imports the outer `tinybrain.mcp` module.

## MCP Tool Surface

### Core Memory And Session Tools

- `store_memory`
- `get_memory`
- `search_memories`
- `update_memory`
- `delete_memory`
- `create_session`
- `get_session`
- `list_sessions`

### Relationships, Tags, And Notifications

- `create_relationship`
- `get_related_memories`
- `get_popular_tags`
- `find_memories_by_tags`
- `suggest_related_by_tags`
- `get_notifications`
- `mark_notification_read`

### Analysis And Parity Tools

- `calculate_similarity`
- `generate_embedding`
- `find_similar_memories`
- `semantic_search`
- `check_duplicates`
- `check_duplicate_memories`
- `check_high_priority_memories`
- `get_memory_stats`
- `get_system_diagnostics`

Similarity and embedding-shaped features are deterministic and local. They are intended for offline, repeatable security workflows and can be replaced or augmented later with provider-backed neural embeddings.

### Batch, Templates, And Portability

- `batch_create_memories`
- `batch_update_memories`
- `batch_delete_memories`
- `export_session_data`
- `import_session_data`
- `get_context_summary`
- `get_detailed_memory_info`
- `get_security_templates`
- `create_memory_from_template`

### Discovery

- `get_tinybrain_help`
- `list_memory_categories`
- `list_task_types`
- `list_relationship_types`

## Storage Guidance

CogDB should remain the primary memory graph store for now because relationships, traversal, and graph-style retrieval are central to the product. DuckDB is a strong candidate as a sidecar for analytical security datasets such as CVE/NVD, CWE, MITRE ATT&CK, Atomic Red Team, and custom internal frameworks.

The experimental mempalace files were removed from the repo. Mempalace-style entity memory remains a future evaluation candidate once there is a cleaner design to compare against CogDB and DuckDB.

## Testing

```bash
uv run pytest
uv run ruff check --select F,I,ARG tinybrain/database/__init__.py tinybrain/mcp/__init__.py tests/test_mcp_parity_tools.py
```

The current feature pass also includes a live FastMCP smoke test that checks tool registration and calls the new tools through `mcp.call_tool` against an isolated temporary CogDB database.
