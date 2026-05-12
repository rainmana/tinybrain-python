# TinyBrain 🧠

**Security-Focused LLM Memory Storage MCP Server**

TinyBrain is a modern Python implementation of a comprehensive memory storage system designed specifically for security-focused tasks like security code review, penetration testing, and exploit development. Built with FastMCP, it provides an LLM with persistent, intelligent memory capabilities through the Model Context Protocol (MCP).

## ✨ Key Features

### 🎯 Security-First Design
- **Specialized Categories**: Vulnerability, exploit, payload, technique, tool, reference, context, hypothesis, evidence, recommendation
- **Priority & Confidence Tracking**: 0-10 priority levels and 0.0-1.0 confidence scores
- **Relationship Mapping**: Track dependencies, causes, mitigations, and exploit chains
- **Task Progress Tracking**: Multi-stage security task management
- **Standards Compliance**: Aligned with OWASP, CWE, NIST, and ISO security standards

### 🚀 Modern Python Stack
- **FastMCP**: Latest MCP protocol server framework
- **FastAPI**: High-performance web interface
- **CogDB**: Local graph storage for memories, relationships, sessions, and notifications
- **Deterministic Local Similarity**: Offline token-vector search, deduplication, and embedding-shaped features
- **Typer CLI**: Modern CLI with rich features
- **Loguru**: Beautiful, structured logging
- **Pydantic**: Type-safe models and settings
- **UV**: Fast Python package manager

### 🎨 Web Interface
- **Dark Mode UI**: Beautiful, modern interface
- **Graph Visualization**: Interactive relationship and tag graphs with Cytoscape.js
- **Session Browser**: Browse and search memories
- **Export**: JSON export for sessions and memories
- **Real-time Stats**: Dashboard with statistics and insights

### 🔍 Intelligence Features
- **Tag-Based Linking**: Discover related memories through shared tags
- **Similarity & Duplicate Detection**: Find likely related or duplicate observations without an external embedding service
- **MITRE/CVE/CWE/OWASP Ready**: Template and tagging conventions support standard security frameworks and custom in-house frameworks
- **Import/Export**: Portable session export/import for moving context between agents, tools, and assessment environments

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [UV](https://github.com/astral-sh/uv) (recommended) or pip
- [mise](https://mise.jdx.dev/) (optional, for environment management)

### Installation with UV (Recommended)

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/tinybrain-python.git
cd tinybrain-python

# Create virtual environment and install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e .
```

### Installation with mise

```bash
# Install mise if you haven't already
curl https://mise.run | sh

# Install Python version
mise install

# Create virtual environment and install
uv sync
source .venv/bin/activate
uv pip install -e .
```

### Basic Usage

```bash
# Initialize the database
tinybrain init

# Start the MCP server
tinybrain serve

# Start with custom CogDB path
tinybrain serve --cog-path ~/.tinybrain/custom

# Start the web interface
tinybrain web

# Start web interface on custom port
tinybrain web --port 3000

# Show statistics
tinybrain stats

# Clean up old memories
tinybrain cleanup --max-age 30 --dry-run
```

## 🔧 Configuration

TinyBrain uses environment variables and `.env` files for configuration:

```bash
# Database
TINYBRAIN_COG_HOME=tinybrain
TINYBRAIN_COG_PATH_PREFIX=~/.tinybrain

# Logging
TINYBRAIN_LOG_LEVEL=INFO
TINYBRAIN_LOG_FILE=~/.tinybrain/logs/tinybrain.log
TINYBRAIN_LOG_ROTATION=100 MB
TINYBRAIN_LOG_RETENTION=10 days

# Server
TINYBRAIN_HOST=127.0.0.1
TINYBRAIN_PORT=8000

# Security data
TINYBRAIN_SECURITY_DATA_DIR=~/.tinybrain/security_data
```

## 🎨 MCP Client Configuration

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "tinybrain": {
      "command": "tinybrain",
      "args": ["serve"],
      "env": {
        "TINYBRAIN_COG_HOME": "tinybrain",
        "TINYBRAIN_COG_PATH_PREFIX": "~/.tinybrain",
        "TINYBRAIN_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Using UV in MCP Configuration

If you're using UV and want to ensure the correct environment:

```json
{
  "mcpServers": {
    "tinybrain": {
      "command": "uv",
      "args": ["run", "tinybrain", "serve"],
      "cwd": "/path/to/tinybrain-python",
      "env": {
        "TINYBRAIN_COG_HOME": "tinybrain",
        "TINYBRAIN_COG_PATH_PREFIX": "~/.tinybrain"
      }
    }
  }
}
```

## 🛠️ MCP Tools (43 Total)

TinyBrain provides comprehensive MCP tools for memory management:

For feature parity tracking against the original Go documentation, see
[GO_PARITY_MATRIX.md](GO_PARITY_MATRIX.md).

### Discovery Tools (4 tools - Start Here!)
- `get_tinybrain_help` - Quick start guide and usage information
- `list_memory_categories` - List all valid memory categories with descriptions
- `list_task_types` - List all valid task types for sessions
- `list_relationship_types` - List all valid relationship types

### Core Memory Operations (5 tools)
- `store_memory` - Store new memory entries (requires session_id)
- `get_memory` - Retrieve memory by ID
- `search_memories` - Advanced search with filters
- `update_memory` - Update existing memories
- `delete_memory` - Delete memory entries

### Session Management (4 tools)
- `create_session` - Create new security assessment sessions
- `get_session` - Retrieve session information
- `list_sessions` - List all sessions with filters
- `delete_session` - Delete a session and cascade associated memories, relationships, and notifications

### Tag-Based Linking (3 tools)
- `get_popular_tags` - See most frequently used tags
- `find_memories_by_tags` - Find memories with specific tags (AND/OR logic)
- `suggest_related_by_tags` - Automatic suggestions based on tag overlap

### Relationship Management (2 tools)
- `create_relationship` - Create memory relationships
- `get_related_memories` - Get related memories

### Statistics (1 tool)
- `get_memory_stats` - Comprehensive statistics by category, priority, confidence

### Notifications (1 tool)
- `get_notifications` - Get notifications and alerts

### System (1 tool)
- `health_check` - Perform system health checks

### Parity & Analysis Tools (22 tools)
- `calculate_similarity` - Calculate deterministic token similarity between text blocks
- `generate_embedding` - Generate stable local feature vectors for offline matching and tests
- `find_similar_memories` - Find memories similar to a source memory
- `semantic_search` - Rank memories by local token-vector similarity
- `check_duplicates` / `check_duplicate_memories` - Detect likely duplicate observations
- `batch_create_memories` - Create multiple memory entries in one call
- `batch_update_memories` - Update multiple memory entries in one call
- `batch_delete_memories` - Delete multiple memory entries in one call
- `export_session_data` - Export a session with memories and relationships
- `import_session_data` - Import exported session data, optionally remapping IDs
- `get_context_summary` - Produce compact high-signal context for LLM agents
- `get_detailed_memory_info` - Return a memory with related and similar entries
- `get_security_templates` - List built-in security templates
- `create_memory_from_template` - Create a memory from a security template
- `mark_notification_read` - Mark notifications read or unread
- `check_high_priority_memories` - Find high-priority, high-confidence memories
- `get_system_diagnostics` - Return storage and tool-surface diagnostics
- `cleanup_orphan_relationships` - Remove relationship records whose source or target memory is missing
- `cleanup_old_memories` - Dry-run or delete memories older than a configurable age
- `cleanup_low_priority_memories` - Dry-run or delete low-priority memories
- `cleanup_unused_memories` - Dry-run or delete old, low-access memories

## 🎯 Quick Start Workflow

```python
# 1. Get help
get_tinybrain_help()

# 2. See valid values
list_memory_categories()
list_task_types()

# 3. Create a session
create_session(name="Security Review", task_type="security_review")
# Returns: {"id": "sess_abc123", "status": "created"}

# 4. Store memories
store_memory(
    session_id="sess_abc123",
    title="SQL Injection Found",
    content="Login form vulnerable to SQL injection",
    category="vulnerability",
    priority=8,
    confidence=0.9
)

# 5. Search and relate
search_memories(query="SQL injection", session_id="sess_abc123")
create_relationship(
    source_memory_id="mem_123",
    target_memory_id="mem_456",
    relationship_type="exploits"
)
```

## 📊 Architecture

### Database Schema

TinyBrain uses CogDB as a local graph store:

- **sessions** - Security assessment sessions
- **memories** - Individual pieces of information
- **relationships** - Links between memory entries
- **notifications** - Real-time alerts

### Key Design Principles

1. **Async-First**: All database operations are async for high performance
2. **Type-Safe**: Pydantic models ensure data integrity
3. **Graph-Style Queries**: Relationship traversal for exploit chains
4. **Offline Similarity**: Deterministic token vectors support deduplication and semantic-ish ranking without sending assessment data to a model provider
5. **Production-Ready**: Structured logging, error handling, and monitoring
6. **Framework-Extensible**: Tags, templates, and session exports support CWE, CVE, MITRE ATT&CK, Atomic Red Team, and custom in-house frameworks

## 🧪 Development

### Setup Development Environment

```bash
# Install with dev dependencies
uv sync --all-extras

# Run tests
pytest

# Run tests with coverage
pytest --cov=tinybrain --cov-report=html

# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy tinybrain
```

### Project Structure

```
tinybrain-python/
├── tinybrain/
│   ├── __init__.py
│   ├── cli.py              # Typer CLI
│   ├── config.py           # Pydantic settings
│   ├── log_config.py       # Loguru configuration
│   ├── models/
│   │   └── __init__.py     # Pydantic models
│   ├── database/
│   │   └── __init__.py     # CogDB backend
│   ├── mcp/
│   │   └── __init__.py     # FastMCP server
│   └── services/
│       └── __init__.py     # Security data downloaders
├── tests/
├── pyproject.toml          # UV configuration
├── .tool-versions          # mise configuration
└── README.md
```

## 🔐 Security Data Integration

TinyBrain includes early download/query services for security datasets. The current MCP surface is optimized for storing, tagging, templating, and retrieving framework-aligned assessment memories; a DuckDB analytical sidecar is a good next step for larger CVE/CWE/MITRE/Atomic/custom-framework datasets.

```python
from tinybrain.services import SecurityDataDownloader

downloader = SecurityDataDownloader()

# Download MITRE ATT&CK
await downloader.download_mitre_attack()

# Download CWE list
await downloader.download_cwe_list()

# Download OWASP Top 10
await downloader.download_owasp_top10()

# Download all datasets
await downloader.download_all()
```

## 🧭 Roadmap Notes

- **DuckDB sidecar**: Keep CogDB as the primary memory/relationship store and add DuckDB for analytical security datasets where columnar scans and local joins are valuable.
- **Mempalace evaluation**: The experimental `mempalace.yaml` and `entities.json` files were removed from the repo for now. Revisit mempalace-style entity memory later as a candidate memory technology once the design is cleaner and can be compared against CogDB/DuckDB on accuracy, portability, and agent ergonomics.
- **Librarian agent**: Add an optional agent that catalogs and links observations while preserving the original entry text and separating derived analysis from raw evidence.

## 📝 Example Usage

### Store a Vulnerability

```python
# Via MCP tool
{
  "name": "store_memory",
  "arguments": {
    "session_id": "sess_abc123",
    "title": "SQL Injection in Login Form",
    "content": "Found SQL injection vulnerability in username parameter",
    "category": "vulnerability",
    "priority": 8,
    "confidence": 0.9,
    "tags": ["sql-injection", "authentication", "critical"],
    "source": "manual-testing"
  }
}
```

### Search Memories

```python
# Via MCP tool
{
  "name": "search_memories",
  "arguments": {
    "query": "SQL injection authentication",
    "session_id": "sess_abc123",
    "min_priority": 7,
    "limit": 20
  }
}
```

### Create Relationships

```python
# Via MCP tool
{
  "name": "create_relationship",
  "arguments": {
    "source_memory_id": "mem_123",
    "target_memory_id": "mem_456",
    "relationship_type": "exploits",
    "strength": 0.8,
    "description": "SQL injection can be used to bypass authentication"
  }
}
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [UV](https://github.com/astral-sh/uv) - Fast Python package manager
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Loguru](https://github.com/Delgan/loguru) - Logging library
- [MITRE ATT&CK](https://attack.mitre.org/) - Threat intelligence framework
- Original [TinyBrain Go implementation](https://github.com/rainmana/tinybrain)

---

**TinyBrain** - Making LLM memory storage intelligent, fast, and security-focused. 🧠🔒
