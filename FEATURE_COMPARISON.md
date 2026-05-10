# TinyBrain Feature Comparison: Go vs Python

## Current Status

- **Original Go version**: Approximately 40 MCP tools in the published feature set.
- **Python version**: 40 MCP tools currently registered by FastMCP.
- **Testing**: Full pytest suite passes, and a live FastMCP `call_tool` smoke test exercises the new MCP parity tools against an isolated temporary CogDB database.

The Python implementation now covers the major day-to-day parity surface: memory CRUD, sessions, relationships, tags, notifications, statistics, duplicate detection, local similarity search, batch operations, session import/export, templates, context summaries, and diagnostics.

## Implemented MCP Tools

### Discovery

| Tool | Python Status |
|------|---------------|
| `get_tinybrain_help` | Implemented |
| `list_memory_categories` | Implemented |
| `list_task_types` | Implemented |
| `list_relationship_types` | Implemented |

### Core Memory Operations

| Tool | Python Status |
|------|---------------|
| `store_memory` | Implemented |
| `get_memory` | Implemented |
| `search_memories` | Implemented |
| `update_memory` | Implemented |
| `delete_memory` | Implemented |
| `find_similar_memories` | Implemented |
| `check_duplicates` | Implemented |
| `get_memory_stats` | Implemented |

### Session, Relationship, And Context

| Tool | Python Status |
|------|---------------|
| `create_session` | Implemented |
| `get_session` | Implemented |
| `list_sessions` | Implemented |
| `delete_session` | Implemented |
| `create_relationship` | Implemented |
| `get_related_memories` | Implemented |
| `get_context_summary` | Implemented |
| `export_session_data` | Implemented |
| `import_session_data` | Implemented |
| `get_detailed_memory_info` | Implemented |

### Tags, Templates, And Batch Operations

| Tool | Python Status |
|------|---------------|
| `get_popular_tags` | Implemented |
| `find_memories_by_tags` | Implemented |
| `suggest_related_by_tags` | Implemented |
| `get_security_templates` | Implemented |
| `create_memory_from_template` | Implemented |
| `batch_create_memories` | Implemented |
| `batch_update_memories` | Implemented |
| `batch_delete_memories` | Implemented |

### Similarity And Search

| Tool | Python Status |
|------|---------------|
| `semantic_search` | Implemented with deterministic local token-vector ranking |
| `generate_embedding` | Implemented as deterministic local hashed token vectors |
| `calculate_similarity` | Implemented with token cosine similarity |

These tools intentionally avoid network calls or external embedding providers, which keeps pentest observations local and makes tests deterministic. A neural embedding provider can be added later behind the same MCP contract if desired.

### Notifications And Diagnostics

| Tool | Python Status |
|------|---------------|
| `get_notifications` | Implemented |
| `mark_notification_read` | Implemented |
| `check_high_priority_memories` | Implemented |
| `check_duplicate_memories` | Implemented as compatibility alias |
| `health_check` | Implemented |
| `get_system_diagnostics` | Implemented |
| `cleanup_orphan_relationships` | Implemented |

## Remaining Gaps

| Area | Notes |
|------|-------|
| Task progress MCP tools | The nested inner backend has task-progress support, but the active outer MCP module does not currently expose task-progress tools. |
| Context snapshot MCP tools | The nested inner backend has snapshot support, but the active outer MCP module exposes context summaries and import/export instead. |
| Age/priority cleanup MCP tools | CLI cleanup exists; age, low-priority, and unused-memory MCP cleanup tools are still useful parity targets. |
| Security dataset persistence/querying | Download/query services exist in early form. Larger CVE/CWE/MITRE/Atomic/custom-framework datasets should likely use a DuckDB analytical sidecar. |
| Neural semantic search | Current similarity tooling is deterministic and offline. Provider-backed embeddings can be added later without changing the public tool names. |

## Storage Recommendation

The Python implementation currently uses CogDB as the primary local graph store. That is a better fit than DuckDB for the core memory graph: memories, sessions, relationships, notifications, and traversal.

DuckDB is still a strong candidate as a sidecar for standards and intelligence datasets:

- CVE/NVD records
- CWE mappings
- MITRE ATT&CK techniques and tactics
- Atomic Red Team tests
- Custom in-house frameworks
- Cross-framework correlation and reporting

## Future Memory Technology Note

The experimental `mempalace.yaml` and `entities.json` files were removed from the repo for now. Mempalace-style entity memory is worth revisiting later as a potential memory technology once it can be evaluated cleanly against CogDB and a DuckDB sidecar for accuracy, portability, and agent ergonomics.
