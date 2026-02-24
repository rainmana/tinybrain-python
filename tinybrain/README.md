# TinyBrain 🧠

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io/)
[![Security Focused](https://img.shields.io/badge/Security-Focused-red.svg)](https://github.com/rainmana/tinybrain)
[![Version](https://img.shields.io/badge/version-v2.0.0-blue.svg)](https://github.com/rainmana/tinybrain/releases)

**Security-Focused LLM Memory Storage with Intelligence Gathering, Reverse Engineering, and MITRE ATT&CK Integration**

TinyBrain is a comprehensive memory storage system designed specifically for security professionals, penetration testers, and AI assistants working on offensive security tasks. It provides intelligent memory management, pattern recognition, and comprehensive intelligence gathering capabilities through the Model Context Protocol (MCP).

## ✨ Key Features

### 🧠 Intelligence Gathering
- **OSINT**: Open Source Intelligence collection and analysis
- **HUMINT**: Human Intelligence gathering and social engineering assessment
- **SIGINT**: Signals Intelligence and communications analysis
- **GEOINT**: Geospatial Intelligence and location-based analysis
- **MASINT**: Measurement and Signature Intelligence
- **TECHINT**: Technical Intelligence and technology assessment
- **FININT**: Financial Intelligence and cryptocurrency tracking
- **CYBINT**: Cyber Intelligence and threat analysis

### 🔍 Reverse Engineering
- **Malware Analysis**: Static and dynamic malware analysis capabilities
- **Binary Analysis**: PE, ELF, Mach-O file format analysis
- **Vulnerability Research**: Fuzzing, exploit development, and vulnerability analysis
- **Protocol Analysis**: Network and application protocol reverse engineering
- **Code Analysis**: Source code and assembly analysis tools

### 🎯 MITRE ATT&CK Integration
- **Complete Framework**: All 14 Enterprise tactics and 200+ techniques
- **TTP Mapping**: Map findings to specific tactics, techniques, and procedures
- **Attack Chain Analysis**: Complete attack chain mapping and analysis
- **Threat Hunting**: Hunt for specific TTPs and attack patterns
- **Campaign Tracking**: Track attack campaigns and threat actor activities
- **Real-Time Data**: Live MITRE ATT&CK dataset with 823+ techniques and 14 tactics
- **Intelligent Querying**: Semantic search across attack techniques and procedures

### 🛡️ Security Patterns & Standards
- **CWE Integration**: Common Weakness Enumeration patterns and classifications
- **OWASP Compliance**: OWASP Top 10 2021 and testing guide integration
- **Multi-Language Support**: Security patterns for 10+ programming languages
- **Authorization Templates**: RBAC, ABAC, and DAC access control patterns
- **Standards Compliance**: NIST, ISO 27001, PTES, and industry standards
- **NVD Integration**: National Vulnerability Database with 314,835+ CVEs
- **OWASP Testing Guide**: Complete web application security testing procedures

### 📊 Memory Management
- **30+ Memory Categories**: Comprehensive categorization for intelligence, reconnaissance, and analysis data
- **Intelligence Objects**: Threat actors, attack campaigns, IOCs, TTPs, patterns, and correlations
- **Context-Aware Storage**: Automatically categorizes and prioritizes information
- **Advanced Search**: Semantic, exact, fuzzy, tag-based, and relationship-based search
- **Access Tracking**: Monitors which memories are most relevant and frequently accessed
- **Context Summaries**: Provides relevant memory summaries for current tasks

### 🎨 Visualization & UI
- **Streamlit Dashboard**: Interactive web UI for data visualization and management
- **NetworkX Graph Analysis**: Visualize relationships between memories, vulnerabilities, and exploits
- **Interactive Graphs**: Explore memory relationships with interactive network graphs
- **Data Management**: Add, edit, and manage custom datasets through the UI

### High Performance & Reliability
- **SQLite Backend**: Fast, reliable embedded database with full-text search
- **ChromaDB Support**: Optional vector database for advanced semantic search
- **MCP Endpoint**: Custom MCP protocol endpoint
- **Real-time Updates**: Live memory updates and notifications
- **Optimized Queries**: Indexed searches and efficient relationship traversal
- **Transaction Safety**: ACID compliance for data integrity
- **Concurrent Access**: Thread-safe operations for multiple LLM interactions
- **Zero Configuration**: Works out of the box with minimal setup

## 🚀 Quick Start

### Installation

#### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/rainmana/tinybrain.git
cd tinybrain

# Install dependencies
uv sync

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
uv pip install -e .

# Optional: Install with ChromaDB support for semantic search
uv pip install -e ".[chromadb]"
```

#### Using pip

```bash
pip install tinybrain
```

### Basic Usage

```bash
# Start the MCP server
tinybrain serve

# Start with custom database path
tinybrain serve --db-path ~/.tinybrain/data.db

# Start the Streamlit UI
streamlit run tinybrain/ui/app.py

# Or use the CLI command
tinybrain ui
```

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop):

**Basic Configuration (SQLite only):**
```json
{
  "mcpServers": {
    "tinybrain": {
      "command": "tinybrain",
      "args": ["serve"],
      "env": {
        "TINYBRAIN_DB_PATH": "~/.tinybrain/data.db"
      }
    }
  }
}
```

**With ChromaDB (for semantic search):**
```json
{
  "mcpServers": {
    "tinybrain": {
      "command": "tinybrain",
      "args": ["serve", "--chromadb"],
      "env": {
        "TINYBRAIN_DB_PATH": "~/.tinybrain/data.db"
      }
    }
  }
}
```

**Note:** For ChromaDB support, install the optional dependency:
```bash
uv pip install -e ".[chromadb]"
```

## 📚 Documentation

For complete documentation, API reference, and detailed guides, visit our comprehensive documentation site.

## 🏗️ Architecture

TinyBrain is built with:
- **Python 3.10+** - Modern Python with type hints
- **FastMCP** - MCP protocol server framework
- **aiosqlite** - Async SQLite database driver
- **SQLite** - Embedded database with full-text search (FTS5)
- **ChromaDB** - Optional vector database for semantic search
- **NetworkX** - Graph analysis and visualization
- **Streamlit** - Interactive web UI
- **Pydantic** - Data validation and settings management
- **httpx** - Async HTTP client for security data downloads

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tinybrain --cov-report=html

# Run specific test file
pytest tests/test_memory.py
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**TinyBrain** - Making LLM memory storage intelligent, fast, and security-focused. 🧠🔒
