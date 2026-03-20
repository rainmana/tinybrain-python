"""FastAPI web interface for TinyBrain."""
import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tinybrain.config import settings
from tinybrain.database import Database

app = FastAPI(title="TinyBrain Web UI", version="2.0.0")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

_db: Optional[Database] = None


async def get_db() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database(Path(settings.cog_path_prefix) / settings.cog_home)
        await _db.initialize()
    return _db


@app.get("/")
async def root():
    return FileResponse(static_dir / "index.html")


@app.get("/api/stats")
async def get_stats():
    db = await get_db()
    memories = await db.search_memories(limit=10000)
    sessions_list = []
    # Collect sessions by scanning memories' session IDs
    session_ids: set[str] = set()
    for m in memories:
        session_ids.add(m.session_id)

    all_tags: set[str] = set()
    by_category: dict[str, int] = {}
    for m in memories:
        for t in (m.tags or []):
            all_tags.add(t)
        cat = m.category if hasattr(m.category, "value") else str(m.category)
        by_category[cat] = by_category.get(cat, 0) + 1

    # Count relationships via the graph's _list_ids_by_type
    rel_count = 0
    if hasattr(db, "_graph") and db._graph:
        def _count_rels():
            result = db._graph.v().has("_type", "relationship").all()
            if result and result.get("result"):
                return len(result["result"])
            return 0
        rel_count = await asyncio.to_thread(_count_rels)

    return {
        "sessions": len(session_ids),
        "memories": len(memories),
        "relationships": rel_count,
        "unique_tags": len(all_tags),
        "by_category": by_category,
    }


@app.get("/api/sessions")
async def list_sessions(limit: int = 50):
    db = await get_db()
    # Get all sessions by listing type
    if hasattr(db, "_graph") and db._graph:
        def _list():
            ids = db._list_ids_by_type("session")
            return db._fetch_entities(ids)
        all_data = await asyncio.to_thread(_list)
        all_data.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        return all_data[:limit]
    return []


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    db = await get_db()
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump(mode="json")


@app.get("/api/sessions/{session_id}/memories")
async def get_session_memories(session_id: str, limit: int = 100):
    db = await get_db()
    memories = await db.search_memories(session_id=session_id, limit=limit)
    return [m.model_dump(mode="json") for m in memories]


@app.get("/api/memories/{memory_id}")
async def get_memory(memory_id: str):
    db = await get_db()
    memory = await db.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory.model_dump(mode="json")


@app.get("/api/memories/{memory_id}/related")
async def get_related(memory_id: str):
    db = await get_db()
    related = await db.get_related_memories(memory_id)
    return [m.model_dump(mode="json") for m in related]


@app.get("/api/graph/session/{session_id}")
async def get_session_graph(session_id: str):
    db = await get_db()
    memories = await db.search_memories(session_id=session_id, limit=1000)
    if not memories:
        return {"nodes": [], "edges": []}

    nodes = [
        {
            "data": {
                "id": m.id,
                "label": m.title,
                "category": m.category if isinstance(m.category, str) else m.category.value,
                "priority": m.priority,
                "confidence": m.confidence,
            }
        }
        for m in memories
    ]

    # Get relationships between these memories
    edges = []
    if hasattr(db, "_graph") and db._graph:
        memory_ids = {m.id for m in memories}

        def _get_rels():
            result = db._list_ids_by_type("relationship")
            rels = db._fetch_entities(result)
            session_rels = []
            for r in rels:
                src = r.get("source_entry_id", "")
                tgt = r.get("target_entry_id", "")
                if src in memory_ids or tgt in memory_ids:
                    session_rels.append(r)
            return session_rels

        rel_data = await asyncio.to_thread(_get_rels)
        for r in rel_data:
            edges.append(
                {
                    "data": {
                        "id": r.get("id", ""),
                        "source": r.get("source_entry_id", ""),
                        "target": r.get("target_entry_id", ""),
                        "type": r.get("relationship_type", ""),
                        "strength": r.get("strength", 0.5),
                    }
                }
            )

    return {"nodes": nodes, "edges": edges}


@app.get("/api/graph/tags")
async def get_tag_graph(limit: int = 50):
    db = await get_db()
    memories = await db.search_memories(limit=10000)

    tag_pairs: dict[tuple, int] = {}
    tag_counts: dict[str, int] = {}

    for m in memories:
        tags = m.tags or []
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        for i, tag1 in enumerate(tags):
            for tag2 in tags[i + 1 :]:
                pair = tuple(sorted([tag1, tag2]))
                tag_pairs[pair] = tag_pairs.get(pair, 0) + 1

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    top_tag_names = {tag for tag, _ in top_tags}

    nodes = [
        {"data": {"id": tag, "label": tag, "count": count}} for tag, count in top_tags
    ]
    edges = [
        {"data": {"source": t1, "target": t2, "weight": count}}
        for (t1, t2), count in tag_pairs.items()
        if t1 in top_tag_names and t2 in top_tag_names
    ]

    return {"nodes": nodes, "edges": edges}


@app.get("/api/export/session/{session_id}")
async def export_session(session_id: str):
    db = await get_db()
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memories = await db.search_memories(session_id=session_id, limit=10000)

    return {
        "session": session.model_dump(mode="json"),
        "memories": [m.model_dump(mode="json") for m in memories],
    }


@app.get("/api/search")
async def search_memories(
    q: str, session_id: Optional[str] = None, limit: int = 20
):
    db = await get_db()
    results = await db.search_memories(q, session_id=session_id, limit=limit)
    return [m.model_dump(mode="json") for m in results]
