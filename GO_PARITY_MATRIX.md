# TinyBrain Go Documentation Parity Matrix

This matrix tracks the Python implementation against the published TinyBrain Go
documentation at <https://rainmana.github.io/tinybrain/>. It is intentionally
feature-oriented rather than a one-to-one code map because several Go pages
describe product capabilities, workflows, or framework integrations rather than
individual MCP tool names.

## Sources Reviewed

- Home and architecture: <https://rainmana.github.io/tinybrain/>
- Core features: <https://rainmana.github.io/tinybrain/core-features/>
- Advanced features: <https://rainmana.github.io/tinybrain/advanced-features/>
- Intelligence and reconnaissance: <https://rainmana.github.io/tinybrain/intelligence/>
- Reverse engineering: <https://rainmana.github.io/tinybrain/reverse-engineering/>
- Security patterns: <https://rainmana.github.io/tinybrain/security-patterns/>
- API reference: <https://rainmana.github.io/tinybrain/api-reference/>

## Status Legend

- **Covered**: Python exposes tested functionality through MCP, CLI, web, or storage.
- **Partial**: Python has a usable foundation, but not the full documented surface.
- **Backlog**: Not implemented yet or only represented as a design direction.

## MCP And Core Memory Surface

| Go-doc capability | Python status | Evidence / next step |
|---|---|---|
| 40+ MCP tools | Covered | FastMCP registers 43 tools, including CRUD, lifecycle cleanup, analysis, diagnostics, templates, and import/export. |
| Memory create/search/update/delete | Covered | `store_memory`, `search_memories`, `update_memory`, `delete_memory`; tests cover non-contiguous search and cascaded deletes. |
| Session create/list/status/archive lifecycle | Partial | `create_session`, `get_session`, `list_sessions`, `delete_session` exist. Session status updates and archive-specific tools are still backlog. |
| Relationship search and graph mapping | Covered | `create_relationship`, `get_related_memories`, export/import relationship preservation, orphan cleanup. |
| Priority and confidence tracking | Covered | Pydantic models and MCP inputs support bounded priority/confidence. |
| Notifications and alerts | Covered | High-priority notifications, notification listing, read/unread updates. |
| Age, low-priority, and unused cleanup | Covered | `cleanup_old_memories`, `cleanup_low_priority_memories`, and `cleanup_unused_memories` default to dry-run and support scoped deletion. |
| Import/export portability | Covered | `export_session_data` and `import_session_data` preserve sessions, memories, and relationships. |

## Search And Analysis

| Go-doc capability | Python status | Evidence / next step |
|---|---|---|
| Full-text search | Covered | Token/substring query matching with category, session, and priority filters. |
| Semantic search | Partial | Deterministic local token-vector ranking exists; provider-backed neural embeddings are backlog. |
| Fuzzy matching | Partial | Current token matching handles non-contiguous terms, but typo-tolerant edit-distance search is backlog. |
| Boolean and wildcard queries | Backlog | Add an explicit query parser before exposing this in MCP. |
| Saved searches and search history | Backlog | Requires persisted saved-search/search-event models. |
| Duplicate detection | Covered | `check_duplicates` and `check_duplicate_memories` use local similarity. |
| Context summaries | Covered | `get_context_summary` and `get_detailed_memory_info` support LLM context retrieval. |

## Security Frameworks And Templates

| Go-doc capability | Python status | Evidence / next step |
|---|---|---|
| OWASP/CWE/security templates | Partial | Built-in templates cover web vulnerability and CVE/CWE mapping; richer CWE/OWASP catalogs belong in a dataset sidecar. |
| MITRE ATT&CK tactics and techniques | Partial | MITRE technique template and tagging conventions exist; ATT&CK dataset import/query tooling remains backlog. |
| CVE/NVD mapping | Partial | Template support exists; persistent CVE/NVD querying should be implemented with a DuckDB analytical sidecar. |
| Atomic Red Team alignment | Backlog | Add dataset import, mapping fields, and test/invocation references. |
| Custom in-house frameworks | Partial | Tags/metadata can represent custom frameworks today; formal schema/import/query tools are backlog. |

## Intelligence, Reverse Engineering, And Workflows

| Go-doc capability | Python status | Evidence / next step |
|---|---|---|
| Intelligence collection categories | Partial | Categories/tags can store OSINT/HUMINT/etc.; dedicated intelligence finding models are backlog. |
| Threat actor, campaign, IOC, and TTP tracking | Partial | Representable as memories and relationships; formal object schemas and query tools are backlog. |
| Reverse-engineering workflows | Partial | Findings/artifacts can be stored; integrations with IDA, Ghidra, YARA, sandboxes, and debuggers are backlog. |
| Task progress tracking | Partial | Models and inner backend support exist; active outer MCP tools are not exposed yet. |
| Context snapshots | Partial | Models and inner backend support exist; active outer MCP tools are not exposed yet. |
| Collaboration/team sharing | Backlog | Requires auth, multi-user storage semantics, and possibly remote transport. |

## Storage And Distribution

| Go-doc capability | Python status | Evidence / next step |
|---|---|---|
| PocketBase single-binary distribution | Not applicable | Python uses FastMCP/CogDB rather than Go/PocketBase. |
| Local graph persistence | Covered | CogDB stores sessions, memories, relationships, and notifications. |
| REST/Web API | Partial | FastAPI web UI exists; documented REST parity is not the current priority. |
| DuckDB analytical sidecar | Backlog | Recommended for CVE/NVD, CWE, ATT&CK, Atomic Red Team, and custom framework datasets. |

## Recommended Next Backlog Order

1. Expose task-progress MCP tools for the active outer server.
2. Expose context snapshot MCP tools for the active outer server.
3. Add persisted saved searches and search history.
4. Prototype DuckDB sidecar ingestion/query for CWE, CVE/NVD, MITRE ATT&CK, Atomic Red Team, and custom frameworks.
5. Design the librarian agent around immutable raw observations plus derived links, mappings, and confidence annotations.
