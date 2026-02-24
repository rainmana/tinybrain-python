# Security Dataset Integration Design

## Overview

Integrate OWASP, MITRE ATT&CK, NVD/CVE, and CWE datasets to enrich security findings with standardized references and context.

## Architecture

### Separate Reference Databases
Keep security datasets in separate tables to avoid polluting user memories:

```sql
-- MITRE ATT&CK
CREATE TABLE mitre_techniques (
    id TEXT PRIMARY KEY,              -- T1059
    name TEXT NOT NULL,               -- Command and Scripting Interpreter
    description TEXT,
    tactic TEXT,                      -- execution, persistence, etc.
    platform TEXT,                    -- windows, linux, macos
    data_sources TEXT,                -- JSON array
    mitigations TEXT,                 -- JSON array
    detection TEXT,
    url TEXT
);

-- CVE/NVD
CREATE TABLE cve_entries (
    cve_id TEXT PRIMARY KEY,          -- CVE-2024-1234
    description TEXT,
    severity TEXT,                     -- CRITICAL, HIGH, MEDIUM, LOW
    cvss_score REAL,
    published_date TEXT,
    modified_date TEXT,
    cwe_ids TEXT,                      -- JSON array
    references TEXT,                   -- JSON array of URLs
    affected_products TEXT             -- JSON array
);

-- CWE
CREATE TABLE cwe_entries (
    cwe_id TEXT PRIMARY KEY,          -- CWE-79
    name TEXT NOT NULL,                -- Cross-site Scripting
    description TEXT,
    extended_description TEXT,
    likelihood TEXT,
    consequences TEXT,                 -- JSON array
    mitigations TEXT,                  -- JSON array
    examples TEXT                      -- JSON array
);

-- OWASP Top 10
CREATE TABLE owasp_categories (
    id TEXT PRIMARY KEY,               -- A01:2021
    name TEXT NOT NULL,                -- Broken Access Control
    description TEXT,
    risk_factors TEXT,
    prevention TEXT,                   -- JSON array
    example_scenarios TEXT,            -- JSON array
    references TEXT                    -- JSON array
);

-- Cross-reference table
CREATE TABLE memory_references (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    reference_type TEXT NOT NULL,      -- mitre, cve, cwe, owasp
    reference_id TEXT NOT NULL,        -- T1059, CVE-2024-1234, etc.
    relevance_score REAL,              -- 0.0-1.0
    notes TEXT,
    created_at DATETIME,
    FOREIGN KEY (memory_id) REFERENCES memory_entries(id) ON DELETE CASCADE
);

CREATE INDEX idx_memory_refs_memory ON memory_references(memory_id);
CREATE INDEX idx_memory_refs_type ON memory_references(reference_type);
CREATE INDEX idx_memory_refs_ref ON memory_references(reference_id);
```

## MCP Tools

### Discovery Tools
```python
@mcp.tool()
async def search_mitre_techniques(query: str, tactic: Optional[str] = None) -> list[dict]:
    """Search MITRE ATT&CK techniques by name or description."""

@mcp.tool()
async def search_cve(query: str, min_severity: Optional[str] = None) -> list[dict]:
    """Search CVE database by description or product."""

@mcp.tool()
async def search_cwe(query: str) -> list[dict]:
    """Search CWE database by name or description."""

@mcp.tool()
async def search_owasp(query: str) -> list[dict]:
    """Search OWASP Top 10 categories."""
```

### Linking Tools
```python
@mcp.tool()
async def link_memory_to_mitre(
    memory_id: str, 
    technique_id: str, 
    relevance_score: float = 0.8,
    notes: Optional[str] = None
) -> dict:
    """Link a memory to a MITRE ATT&CK technique."""

@mcp.tool()
async def link_memory_to_cve(memory_id: str, cve_id: str, ...) -> dict:
    """Link a memory to a CVE entry."""

@mcp.tool()
async def link_memory_to_cwe(memory_id: str, cwe_id: str, ...) -> dict:
    """Link a memory to a CWE entry."""

@mcp.tool()
async def link_memory_to_owasp(memory_id: str, owasp_id: str, ...) -> dict:
    """Link a memory to an OWASP category."""
```

### Enrichment Tools
```python
@mcp.tool()
async def get_memory_with_references(memory_id: str) -> dict:
    """Get memory with all linked security references."""
    # Returns memory + all MITRE/CVE/CWE/OWASP links

@mcp.tool()
async def suggest_references(memory_id: str, limit: int = 5) -> dict:
    """AI-powered suggestion of relevant security references.
    
    Analyzes memory content and suggests:
    - Relevant MITRE techniques
    - Related CVEs
    - Applicable CWEs
    - OWASP categories
    """

@mcp.tool()
async def get_technique_details(technique_id: str) -> dict:
    """Get full details of a MITRE ATT&CK technique."""

@mcp.tool()
async def get_cve_details(cve_id: str) -> dict:
    """Get full details of a CVE entry."""
```

### Analysis Tools
```python
@mcp.tool()
async def get_attack_coverage(session_id: str) -> dict:
    """Show MITRE ATT&CK coverage for a session.
    
    Returns:
    - Tactics covered
    - Techniques identified
    - Coverage percentage
    - Gaps in coverage
    """

@mcp.tool()
async def get_vulnerability_summary(session_id: str) -> dict:
    """Summarize vulnerabilities by CWE and severity."""
```

## Data Loading

### CLI Commands
```bash
# Download and import datasets
tinybrain import-mitre --file attack.json
tinybrain import-cve --year 2024
tinybrain import-cwe --file cwe.xml
tinybrain import-owasp --file owasp-top10.json

# Update datasets
tinybrain update-datasets --all

# Show dataset stats
tinybrain dataset-stats
```

### Downloader Service
```python
class SecurityDatasetManager:
    async def download_mitre_attack(self) -> Path:
        """Download latest MITRE ATT&CK dataset."""
        
    async def download_nvd_cves(self, year: int) -> Path:
        """Download NVD CVE dataset for a year."""
        
    async def download_cwe_list(self) -> Path:
        """Download CWE list."""
        
    async def import_mitre_to_db(self, file_path: Path):
        """Parse and import MITRE data to database."""
        
    async def import_cve_to_db(self, file_path: Path):
        """Parse and import CVE data to database."""
```

## Usage Workflow

### 1. Initial Setup
```bash
# Download datasets
tinybrain update-datasets --all

# Verify import
tinybrain dataset-stats
```

### 2. During Security Assessment
```python
# Store a finding
store_memory(
    session_id="sess_123",
    title="Command Injection in API",
    content="Found command injection in /api/exec endpoint",
    category="vulnerability",
    tags=["command-injection", "api", "critical"]
)

# Get AI suggestions for references
suggest_references(memory_id="mem_456")
# Returns: [
#   {type: "mitre", id: "T1059", name: "Command and Scripting Interpreter", score: 0.95},
#   {type: "cwe", id: "CWE-78", name: "OS Command Injection", score: 0.98},
#   {type: "owasp", id: "A03:2021", name: "Injection", score: 0.92}
# ]

# Link the relevant ones
link_memory_to_mitre(memory_id="mem_456", technique_id="T1059")
link_memory_to_cwe(memory_id="mem_456", cwe_id="CWE-78")

# Get enriched view
get_memory_with_references(memory_id="mem_456")
# Returns memory + full details of linked MITRE/CWE/OWASP entries
```

### 3. Analysis & Reporting
```python
# See MITRE ATT&CK coverage
get_attack_coverage(session_id="sess_123")
# Returns tactics/techniques covered, gaps

# Vulnerability summary
get_vulnerability_summary(session_id="sess_123")
# Returns CWE breakdown, severity distribution
```

## Benefits

### For AI Agents
1. **Standardized References** - Link findings to industry standards
2. **Context Enrichment** - Get full details of techniques/vulnerabilities
3. **Automatic Suggestions** - AI suggests relevant references
4. **Coverage Analysis** - Understand what's been tested

### For Security Professionals
1. **Compliance** - Map findings to frameworks (MITRE, OWASP, CWE)
2. **Reporting** - Generate reports with standard references
3. **Knowledge Base** - Access security knowledge without leaving tool
4. **Trend Analysis** - See common vulnerabilities across sessions

## Implementation Priority

### Phase 1: Foundation (High Priority)
1. Database schema for reference tables
2. Data downloaders for MITRE/CVE/CWE/OWASP
3. Import CLI commands
4. Basic search tools

### Phase 2: Linking (Medium Priority)
5. Cross-reference table and tools
6. Manual linking tools (link_memory_to_*)
7. Get memory with references

### Phase 3: Intelligence (Low Priority)
8. AI-powered suggestion tool
9. Coverage analysis tools
10. Vulnerability summary tools

## Data Sources

- **MITRE ATT&CK**: https://github.com/mitre/cti (JSON)
- **NVD/CVE**: https://nvd.nist.gov/feeds/json/cve/1.1/ (JSON)
- **CWE**: https://cwe.mitre.org/data/xml/cwec_latest.xml.zip (XML)
- **OWASP Top 10**: Manual curation or scraping

## Storage Considerations

- **MITRE ATT&CK**: ~200 techniques, ~2MB
- **CVE Database**: 300K+ entries, ~500MB (consider yearly subsets)
- **CWE**: ~900 entries, ~10MB
- **OWASP Top 10**: ~10 categories, <1MB

**Recommendation**: Store in same SQLite database but separate tables. Use separate database file if size becomes an issue.

## Next Steps

1. Implement tag-based linking (DONE)
2. Add session listing and stats (DONE)
3. Create reference database schema
4. Build data downloaders
5. Implement search and linking tools
6. Add AI-powered suggestions
