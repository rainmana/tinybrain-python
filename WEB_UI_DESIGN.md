# TinyBrain Web UI Design

## Overview

Minimal dark-mode web interface for visualizing and exporting TinyBrain data using FastAPI + vanilla JS.

## Tech Stack

- **Backend**: FastAPI (already a dependency)
- **Frontend**: Vanilla JS + Tailwind CSS (via CDN)
- **Graph Viz**: Cytoscape.js (lightweight, powerful)
- **Charts**: Chart.js (simple, clean)
- **No build step**: Pure HTML/CSS/JS served statically

## Architecture

```
tinybrain/
├── web/
│   ├── __init__.py          # FastAPI app
│   ├── static/
│   │   ├── index.html       # Single page app
│   │   ├── app.js           # Main JS logic
│   │   └── style.css        # Custom dark theme
│   └── api.py               # API endpoints
```

## API Endpoints

### Data Retrieval
```python
GET  /api/sessions                    # List all sessions
GET  /api/sessions/{id}               # Session details
GET  /api/sessions/{id}/memories      # Memories in session
GET  /api/memories/{id}               # Memory details
GET  /api/memories/{id}/related       # Related memories
GET  /api/relationships               # All relationships
GET  /api/stats                       # Global statistics
GET  /api/stats/session/{id}          # Session statistics
```

### Graph Data
```python
GET  /api/graph/session/{id}          # Graph data for session
GET  /api/graph/memory/{id}           # Graph centered on memory
GET  /api/graph/tags                  # Tag co-occurrence graph
```

### Export
```python
GET  /api/export/session/{id}?format=json|csv
GET  /api/export/memories?format=json|csv
GET  /api/export/graph/{id}?format=json|graphml
```

## UI Components

### 1. Dashboard (Landing Page)
```
┌─────────────────────────────────────────┐
│  🧠 TinyBrain                    [Dark] │
├─────────────────────────────────────────┤
│  📊 Statistics                          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │
│  │ 42  │ │ 156 │ │ 89  │ │ 23  │      │
│  │Sess │ │Mems │ │Rels │ │Tags │      │
│  └─────┘ └─────┘ └─────┘ └─────┘      │
│                                         │
│  📋 Recent Sessions                     │
│  • Security Review - Project X          │
│  • Pentest - API Gateway                │
│  • Code Review - Auth Module            │
│                                         │
│  🏷️  Popular Tags                       │
│  [sql-injection] [xss] [auth] [api]    │
└─────────────────────────────────────────┘
```

### 2. Session View
```
┌─────────────────────────────────────────┐
│  ← Back    Session: Security Review     │
├─────────────────────────────────────────┤
│  [Memories] [Graph] [Stats] [Export]    │
├─────────────────────────────────────────┤
│  Memories (156)          [Search...]    │
│  ┌───────────────────────────────────┐  │
│  │ 🔴 SQL Injection in Login         │  │
│  │    Priority: 9 | Confidence: 0.95 │  │
│  │    Tags: sql-injection, auth      │  │
│  ├───────────────────────────────────┤  │
│  │ 🟡 XSS in Comment Form            │  │
│  │    Priority: 6 | Confidence: 0.80 │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 3. Graph View
```
┌─────────────────────────────────────────┐
│  Graph View                [Layout ▼]   │
├─────────────────────────────────────────┤
│                                         │
│         ●─────●                         │
│        ╱│╲   ╱│╲                        │
│       ● │ ● ● │ ●                       │
│        ╲│╱   ╲│╱                        │
│         ●─────●                         │
│                                         │
│  Legend:                                │
│  🔴 Vulnerability  🟢 Finding           │
│  🔵 Exploit        🟡 Technique         │
│  ─── depends_on    ─·─ exploits        │
└─────────────────────────────────────────┘
```

### 4. Memory Detail
```
┌─────────────────────────────────────────┐
│  ← Back    Memory Details               │
├─────────────────────────────────────────┤
│  SQL Injection in Login Form            │
│  Category: vulnerability                │
│  Priority: 9 | Confidence: 0.95         │
│  Tags: [sql-injection] [auth] [critical]│
│                                         │
│  Content:                               │
│  Found SQL injection vulnerability...   │
│                                         │
│  Related Memories (3):                  │
│  • Auth Bypass Technique                │
│  • Database Schema Leak                 │
│  • Admin Panel Access                   │
│                                         │
│  [Export] [Edit] [Delete]               │
└─────────────────────────────────────────┘
```

## Implementation

### Minimal FastAPI App
```python
# tinybrain/web/__init__.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="TinyBrain Web UI")

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")

# API routes
from .api import router
app.include_router(router, prefix="/api")
```

### API Implementation
```python
# tinybrain/web/api.py
from fastapi import APIRouter, HTTPException
from tinybrain.database import Database
from typing import Optional

router = APIRouter()
db = Database()

@router.get("/sessions")
async def list_sessions():
    # Return all sessions
    pass

@router.get("/graph/session/{session_id}")
async def get_session_graph(session_id: str):
    # Return Cytoscape.js format:
    # {
    #   "nodes": [{"data": {"id": "mem_1", "label": "...", "category": "..."}}],
    #   "edges": [{"data": {"source": "mem_1", "target": "mem_2", "type": "exploits"}}]
    # }
    pass

@router.get("/export/session/{session_id}")
async def export_session(session_id: str, format: str = "json"):
    # Export session data
    pass
```

### Frontend (Single Page)
```html
<!-- tinybrain/web/static/index.html -->
<!DOCTYPE html>
<html class="dark">
<head>
    <title>TinyBrain</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-gray-900 text-gray-100">
    <div id="app" class="container mx-auto p-4">
        <!-- Dynamic content loaded here -->
    </div>
    <script src="/static/app.js"></script>
</body>
</html>
```

```javascript
// tinybrain/web/static/app.js
class TinyBrainUI {
    async loadDashboard() {
        const stats = await fetch('/api/stats').then(r => r.json());
        // Render dashboard
    }
    
    async loadSessionGraph(sessionId) {
        const data = await fetch(`/api/graph/session/${sessionId}`).then(r => r.json());
        
        const cy = cytoscape({
            container: document.getElementById('graph'),
            elements: data,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#666',
                        'label': 'data(label)'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#ccc',
                        'target-arrow-color': '#ccc',
                        'target-arrow-shape': 'triangle'
                    }
                }
            ],
            layout: { name: 'cose' }
        });
    }
}

const app = new TinyBrainUI();
app.loadDashboard();
```

## CLI Integration

```python
# tinybrain/cli.py
@app.command()
def web(
    host: str = "127.0.0.1",
    port: int = 8080,
    db_path: Optional[str] = None
):
    """Start the web interface."""
    import uvicorn
    from tinybrain.web import app as web_app
    
    if db_path:
        os.environ["TINYBRAIN_DB_PATH"] = db_path
    
    uvicorn.run(web_app, host=host, port=port)
```

## Usage

```bash
# Start web UI
tinybrain web

# Custom port
tinybrain web --port 3000

# Open browser to http://localhost:8080
```

## Features

### Phase 1: Core (Minimal)
- [ ] Dashboard with stats
- [ ] Session list and detail view
- [ ] Memory list with search
- [ ] Basic graph visualization
- [ ] JSON export

### Phase 2: Enhanced
- [ ] Tag co-occurrence graph
- [ ] Memory detail view with relationships
- [ ] CSV export
- [ ] Filter by category/priority
- [ ] Real-time updates (WebSocket)

### Phase 3: Advanced
- [ ] Edit memories via UI
- [ ] Create relationships visually
- [ ] Advanced graph layouts
- [ ] GraphML export
- [ ] Session comparison

## Styling

### Dark Theme Colors
```css
:root {
    --bg-primary: #0f172a;      /* slate-900 */
    --bg-secondary: #1e293b;    /* slate-800 */
    --text-primary: #f1f5f9;    /* slate-100 */
    --text-secondary: #cbd5e1;  /* slate-300 */
    --accent: #3b82f6;          /* blue-500 */
    --danger: #ef4444;          /* red-500 */
    --warning: #f59e0b;         /* amber-500 */
    --success: #10b981;         /* emerald-500 */
}
```

### Category Colors
```javascript
const categoryColors = {
    vulnerability: '#ef4444',  // red
    exploit: '#f59e0b',        // amber
    finding: '#3b82f6',        // blue
    technique: '#8b5cf6',      // violet
    tool: '#06b6d4',           // cyan
    reference: '#6b7280',      // gray
    context: '#10b981',        // emerald
    hypothesis: '#ec4899',     // pink
    evidence: '#14b8a6',       // teal
    recommendation: '#84cc16'  // lime
};
```

## Estimated Effort

- **Backend API**: 2-3 hours (straightforward FastAPI endpoints)
- **Frontend Shell**: 1-2 hours (HTML structure, routing)
- **Graph Visualization**: 2-3 hours (Cytoscape.js integration)
- **Dashboard & Stats**: 1-2 hours (charts, cards)
- **Export Functions**: 1 hour (JSON/CSV generation)

**Total: 7-11 hours for Phase 1**

## Benefits

1. **Visual Discovery**: See relationships and patterns
2. **Easy Export**: Share findings with team
3. **Better UX**: Browse memories without CLI
4. **Graph Analysis**: Understand exploit chains visually
5. **Presentation**: Demo findings to stakeholders

## Next Steps

1. Create `tinybrain/web/` directory structure
2. Implement minimal FastAPI app
3. Create single-page HTML with Tailwind
4. Add Cytoscape.js graph visualization
5. Implement core API endpoints
6. Add export functionality
