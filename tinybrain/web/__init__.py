"""FastAPI web interface for TinyBrain."""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from typing import Optional
import json

from tinybrain.database import Database
from tinybrain.config import settings

app = FastAPI(title="TinyBrain Web UI", version="2.0.0")

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global database instance
_db: Optional[Database] = None

async def get_db() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database(settings.db_path)
        await _db.initialize()
    return _db

@app.get("/")
async def root():
    """Serve the main page."""
    return FileResponse(static_dir / "index.html")

@app.get("/api/stats")
async def get_stats():
    """Get global statistics."""
    db = await get_db()
    
    # Total counts
    cursor = await db._conn.execute("SELECT COUNT(*) as count FROM sessions")
    session_count = (await cursor.fetchone())["count"]
    
    cursor = await db._conn.execute("SELECT COUNT(*) as count FROM memory_entries")
    memory_count = (await cursor.fetchone())["count"]
    
    cursor = await db._conn.execute("SELECT COUNT(*) as count FROM relationships")
    relationship_count = (await cursor.fetchone())["count"]
    
    # Unique tags
    cursor = await db._conn.execute("SELECT tags FROM memory_entries WHERE tags IS NOT NULL")
    rows = await cursor.fetchall()
    all_tags = set()
    for row in rows:
        if row["tags"]:
            tags = json.loads(row["tags"])
            if tags:  # Check if tags is not None
                all_tags.update(tags)
    
    # By category
    cursor = await db._conn.execute(
        "SELECT category, COUNT(*) as count FROM memory_entries GROUP BY category"
    )
    by_category = {row["category"]: row["count"] for row in await cursor.fetchall()}
    
    return {
        "sessions": session_count,
        "memories": memory_count,
        "relationships": relationship_count,
        "unique_tags": len(all_tags),
        "by_category": by_category
    }

@app.get("/api/sessions")
async def list_sessions(limit: int = 50):
    """List all sessions."""
    db = await get_db()
    cursor = await db._conn.execute(
        "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    db = await get_db()
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump(mode="json")

@app.get("/api/sessions/{session_id}/memories")
async def get_session_memories(session_id: str, limit: int = 100):
    """Get memories for a session."""
    db = await get_db()
    cursor = await db._conn.execute(
        "SELECT * FROM memory_entries WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit)
    )
    rows = await cursor.fetchall()
    memories = [db._row_to_memory(row) for row in rows]
    return [m.model_dump(mode="json") for m in memories]

@app.get("/api/memories/{memory_id}")
async def get_memory(memory_id: str):
    """Get memory details."""
    db = await get_db()
    memory = await db.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory.model_dump(mode="json")

@app.get("/api/memories/{memory_id}/related")
async def get_related(memory_id: str):
    """Get related memories."""
    db = await get_db()
    related = await db.get_related_memories(memory_id)
    return [m.model_dump(mode="json") for m in related]

@app.get("/api/graph/session/{session_id}")
async def get_session_graph(session_id: str):
    """Get graph data for a session (Cytoscape.js format)."""
    db = await get_db()
    
    # Get memories
    cursor = await db._conn.execute(
        "SELECT * FROM memory_entries WHERE session_id = ?",
        (session_id,)
    )
    memories = await cursor.fetchall()
    
    # Get relationships
    memory_ids = [m["id"] for m in memories]
    if not memory_ids:
        return {"nodes": [], "edges": []}
    
    placeholders = ",".join("?" * len(memory_ids))
    cursor = await db._conn.execute(
        f"SELECT * FROM relationships WHERE source_memory_id IN ({placeholders}) OR target_memory_id IN ({placeholders})",
        (*memory_ids, *memory_ids)
    )
    relationships = await cursor.fetchall()
    
    # Build Cytoscape.js format
    nodes = []
    for m in memories:
        nodes.append({
            "data": {
                "id": m["id"],
                "label": m["title"],
                "category": m["category"],
                "priority": m["priority"],
                "confidence": m["confidence"]
            }
        })
    
    edges = []
    for r in relationships:
        edges.append({
            "data": {
                "id": r["id"],
                "source": r["source_memory_id"],
                "target": r["target_memory_id"],
                "type": r["relationship_type"],
                "strength": r["strength"]
            }
        })
    
    return {"nodes": nodes, "edges": edges}

@app.get("/api/graph/tags")
async def get_tag_graph(limit: int = 50):
    """Get tag co-occurrence graph."""
    db = await get_db()
    
    cursor = await db._conn.execute("SELECT tags FROM memory_entries WHERE tags IS NOT NULL")
    rows = await cursor.fetchall()
    
    # Build co-occurrence matrix
    tag_pairs = {}
    tag_counts = {}
    
    for row in rows:
        if row["tags"]:
            tags = json.loads(row["tags"])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Count co-occurrences
            for i, tag1 in enumerate(tags):
                for tag2 in tags[i+1:]:
                    pair = tuple(sorted([tag1, tag2]))
                    tag_pairs[pair] = tag_pairs.get(pair, 0) + 1
    
    # Get top tags
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    top_tag_names = {tag for tag, _ in top_tags}
    
    # Build graph
    nodes = [{"data": {"id": tag, "label": tag, "count": count}} for tag, count in top_tags]
    edges = []
    
    for (tag1, tag2), count in tag_pairs.items():
        if tag1 in top_tag_names and tag2 in top_tag_names:
            edges.append({
                "data": {
                    "source": tag1,
                    "target": tag2,
                    "weight": count
                }
            })
    
    return {"nodes": nodes, "edges": edges}

@app.get("/api/export/session/{session_id}")
async def export_session(session_id: str):
    """Export session data as JSON."""
    db = await get_db()
    
    # Get session
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get memories
    cursor = await db._conn.execute(
        "SELECT * FROM memory_entries WHERE session_id = ?",
        (session_id,)
    )
    memories = [db._row_to_memory(row) for row in await cursor.fetchall()]
    
    # Get relationships
    memory_ids = [m.id for m in memories]
    if memory_ids:
        placeholders = ",".join("?" * len(memory_ids))
        cursor = await db._conn.execute(
            f"SELECT * FROM relationships WHERE source_memory_id IN ({placeholders}) OR target_memory_id IN ({placeholders})",
            (*memory_ids, *memory_ids)
        )
        relationships = await cursor.fetchall()
    else:
        relationships = []
    
    return {
        "session": session.model_dump(mode="json"),
        "memories": [m.model_dump(mode="json") for m in memories],
        "relationships": [dict(r) for r in relationships]
    }

@app.get("/api/search")
async def search_memories(q: str, session_id: Optional[str] = None, limit: int = 20):
    """Search memories."""
    db = await get_db()
    results = await db.search_memories(q, session_id=session_id, limit=limit)
    return [m.model_dump(mode="json") for m in results]
