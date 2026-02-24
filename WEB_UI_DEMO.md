# TinyBrain Web UI Demo

## Quick Start

```bash
# Start the web interface
tinybrain web

# Open in browser
open http://localhost:8080
```

## Features

### 1. Dashboard
- **Statistics Cards**: Sessions, memories, relationships, unique tags
- **Category Breakdown**: Visual bar chart of memories by category
- **Recent Sessions**: Quick access to latest sessions

### 2. Sessions View
- Browse all sessions
- Click any session to view details
- See task type and creation date

### 3. Session Detail
- View all memories in a session
- **Search**: Real-time search across memory content
- **Memory Cards**: Color-coded by priority
  - Red border: High priority (8-10)
  - Amber border: Medium priority (5-7)
  - Green border: Low priority (0-4)
- **Export**: Download session as JSON

### 4. Relationship Graph
- Select a session from dropdown
- Interactive graph visualization with Cytoscape.js
- **Node Colors**:
  - 🔴 Red: Vulnerability
  - 🟠 Amber: Exploit
  - 🔵 Blue: Finding
  - 🟣 Violet: Technique
  - 🔵 Cyan: Tool
  - ⚫ Gray: Other categories
- **Node Size**: Based on priority (higher priority = larger node)
- **Edge Labels**: Show relationship type (exploits, depends_on, etc.)
- **Interactive**: Click nodes to see details in console

### 5. Tag Co-occurrence Graph
- Visualize which tags appear together
- **Node Size**: Based on tag frequency
- **Edge Width**: Based on co-occurrence count
- Helps discover patterns in your security work

## Example Workflow

### 1. Create Test Data (via MCP)
```python
# In your AI assistant with TinyBrain MCP
create_session(name="API Security Review", task_type="security_review")

store_memory(
    session_id="sess_xxx",
    title="SQL Injection in Login",
    content="Found SQL injection in username parameter",
    category="vulnerability",
    priority=9,
    tags=["sql-injection", "authentication", "critical"]
)

store_memory(
    session_id="sess_xxx",
    title="Auth Bypass Technique",
    content="Can bypass auth using SQL injection",
    category="technique",
    priority=8,
    tags=["sql-injection", "authentication", "bypass"]
)

create_relationship(
    source_memory_id="mem_xxx",
    target_memory_id="mem_yyy",
    relationship_type="exploits"
)
```

### 2. View in Web UI
1. Open http://localhost:8080
2. Click "Sessions" tab
3. Click on "API Security Review"
4. See both memories listed
5. Click "Graph" tab
6. Select "API Security Review" from dropdown
7. See the relationship visualized!

### 3. Explore Tags
1. Click "Tags" tab
2. See "sql-injection" and "authentication" connected
3. Node size shows how often each tag is used
4. Edge shows they appear together

### 4. Export Data
1. Go to session detail
2. Click "Export JSON" button
3. Get complete session data including:
   - Session metadata
   - All memories
   - All relationships

## Keyboard Shortcuts

- **Graph Navigation**:
  - Scroll: Zoom in/out
  - Click + Drag: Pan around
  - Click node: Log details to console

## API Endpoints

All endpoints available at http://localhost:8080/api/

- `GET /api/stats` - Global statistics
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}` - Session details
- `GET /api/sessions/{id}/memories` - Memories in session
- `GET /api/memories/{id}` - Memory details
- `GET /api/memories/{id}/related` - Related memories
- `GET /api/graph/session/{id}` - Graph data (Cytoscape.js format)
- `GET /api/graph/tags` - Tag co-occurrence graph
- `GET /api/export/session/{id}` - Export session as JSON
- `GET /api/search?q=query&session_id=xxx` - Search memories

## Tips

1. **Use Tags Liberally**: They power the tag graph and help discover connections
2. **Set Priorities**: Higher priority memories appear larger in graphs
3. **Create Relationships**: They make the graph view much more useful
4. **Export Regularly**: Back up your security findings
5. **Search is Fast**: FTS5 full-text search is very responsive

## Customization

### Change Port
```bash
tinybrain web --port 3000
```

### Custom Database
```bash
tinybrain web --db-path ~/my-security-work/findings.db
```

## Troubleshooting

### Port Already in Use
```bash
# Use a different port
tinybrain web --port 8081
```

### No Data Showing
```bash
# Check database has data
tinybrain stats

# If empty, create a session via MCP first
```

### Graph Not Loading
- Make sure you selected a session from dropdown
- Check browser console for errors (F12)
- Verify session has memories and relationships

## Next Steps

- Add more memories via MCP
- Create relationships between findings
- Use tags to categorize your work
- Export sessions for reporting
- Explore the tag graph to find patterns

---

**TinyBrain Web UI** - Making security findings visual and accessible! 🧠🎨
