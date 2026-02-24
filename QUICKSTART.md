# Quick Start Guide

This guide will help you get TinyBrain up and running in minutes.

## Prerequisites

- Python 3.11 or higher
- [UV](https://github.com/astral-sh/uv) package manager
- [mise](https://mise.jdx.dev/) (optional, for Python version management)

## Installation

### 1. Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/tinybrain-python.git
cd tinybrain-python

# Install Python version with mise (optional)
mise install

# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
uv pip install -e .
```

### 3. Initialize Database

```bash
tinybrain init
```

This creates the SQLite database at `~/.tinybrain/memory.db` with all necessary tables and indexes.

### 4. Start the Server

```bash
tinybrain serve
```

The MCP server will start and listen on stdin/stdout for MCP protocol messages.

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` to customize:

```bash
TINYBRAIN_DB_PATH=~/.tinybrain/memory.db
TINYBRAIN_LOG_LEVEL=INFO
TINYBRAIN_LOG_FILE=~/.tinybrain/logs/tinybrain.log
```

### MCP Client Configuration

#### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tinybrain": {
      "command": "tinybrain",
      "args": ["serve"],
      "env": {
        "TINYBRAIN_DB_PATH": "~/.tinybrain/memory.db",
        "TINYBRAIN_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Using UV

If you want to use UV to run the server:

```json
{
  "mcpServers": {
    "tinybrain": {
      "command": "uv",
      "args": ["run", "tinybrain", "serve"],
      "cwd": "/path/to/tinybrain-python",
      "env": {
        "TINYBRAIN_DB_PATH": "~/.tinybrain/memory.db"
      }
    }
  }
}
```

## Basic Usage

### CLI Commands

```bash
# Initialize database
tinybrain init

# Start MCP server
tinybrain serve

# Show statistics
tinybrain stats

# Clean up old memories (dry run)
tinybrain cleanup --max-age 30 --dry-run

# Clean up old memories (actual deletion)
tinybrain cleanup --max-age 30

# Use custom database path
tinybrain serve --db-path /path/to/custom.db

# Set log level
tinybrain serve --log-level DEBUG
```

### MCP Tools

Once connected to an MCP client (like Claude Desktop), you can use these tools:

#### Store a Memory

```json
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

#### Search Memories

```json
{
  "name": "search_memories",
  "arguments": {
    "query": "SQL injection",
    "session_id": "sess_abc123",
    "min_priority": 7,
    "limit": 20
  }
}
```

#### Create a Session

```json
{
  "name": "create_session",
  "arguments": {
    "name": "Web App Security Review",
    "task_type": "security_review",
    "description": "Comprehensive security review of web application"
  }
}
```

## Development

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tinybrain --cov-report=html

# Run specific test file
pytest tests/test_database.py
```

### Code Quality

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy tinybrain
```

## Troubleshooting

### Database Issues

If you encounter database errors:

```bash
# Reinitialize database
rm ~/.tinybrain/memory.db
tinybrain init
```

### Import Errors

Make sure you've activated the virtual environment:

```bash
source .venv/bin/activate
```

### UV Issues

If UV commands fail, try:

```bash
# Update UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clear cache
rm -rf .uv
uv sync
```

## Next Steps

- Read the [README.md](README.md) for detailed documentation
- Explore the [examples](examples/) directory
- Check out the [tests](tests/) for usage examples
- Review the [database schema](tinybrain/database/schema.py)

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/tinybrain-python/issues
- Documentation: See README.md

---

**Happy hacking! 🧠🔒**
