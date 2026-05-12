"""FastMCP server with all TinyBrain tools."""

import hashlib
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastmcp import FastMCP

from tinybrain.database import Database
from tinybrain.models import (
    Memory,
    MemoryCategory,
    Notification,
    NotificationType,
    Relationship,
    RelationshipType,
    Session,
    TaskType,
)

mcp = FastMCP("TinyBrain", version="2.0.0")

db: Optional[Database] = None


async def get_db() -> Database:
    """Get or create database instance."""
    global db
    if db is None:
        from tinybrain.config import settings
        db_path = Path(settings.cog_path_prefix) / settings.cog_home
        db = Database(db_path)
        await db.initialize()
    return db


TOKEN_RE = re.compile(r"[a-z0-9_./:-]+")

SECURITY_TEMPLATES = {
    "web_vulnerability": {
        "category": "vulnerability",
        "priority": 7,
        "confidence": 0.7,
        "tags": ["web", "vulnerability"],
        "content": (
            "Finding: {finding}\nAffected asset: {asset}\nEvidence: {evidence}\n"
            "Impact: {impact}\nRecommendation: {recommendation}"
        ),
    },
    "mitre_technique": {
        "category": "technique",
        "priority": 6,
        "confidence": 0.75,
        "tags": ["mitre-attack", "technique"],
        "content": (
            "Technique: {technique_id} {technique_name}\nTactic: {tactic}\n"
            "Observed behavior: {evidence}\nDetection notes: {detection}\n"
            "Mitigation: {mitigation}"
        ),
    },
    "cve_mapping": {
        "category": "reference",
        "priority": 6,
        "confidence": 0.8,
        "tags": ["cve", "cwe", "vulnerability-intel"],
        "content": (
            "CVE: {cve_id}\nCWE: {cwe_id}\nAffected component: {component}\n"
            "Relevance: {relevance}\nSource: {source}"
        ),
    },
    "hypothesis": {
        "category": "hypothesis",
        "priority": 5,
        "confidence": 0.4,
        "tags": ["hypothesis", "needs-validation"],
        "content": "Hypothesis: {hypothesis}\nRationale: {rationale}\nValidation plan: {validation_plan}",
    },
}


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _memory_text(memory: Memory) -> str:
    category = memory.category.value if hasattr(memory.category, "value") else str(memory.category)
    return " ".join([memory.title, memory.content, category, " ".join(memory.tags)])


def _cosine_similarity(left: str, right: str) -> float:
    left_counts = Counter(_tokenize(left))
    right_counts = Counter(_tokenize(right))
    if not left_counts or not right_counts:
        return 0.0
    shared = set(left_counts) & set(right_counts)
    dot = sum(left_counts[t] * right_counts[t] for t in shared)
    left_norm = math.sqrt(sum(v * v for v in left_counts.values()))
    right_norm = math.sqrt(sum(v * v for v in right_counts.values()))
    return round(dot / (left_norm * right_norm), 4)


def _memory_preview(memory: Memory) -> dict:
    data = memory.model_dump(mode="json")
    if len(data.get("content", "")) > 300:
        data["content"] = data["content"][:300] + "..."
    return data


async def _create_high_priority_notification(
    database: Database,
    session_id: str,
    memory_id: str,
    title: str,
    priority: int,
    confidence: float,
) -> None:
    if priority < 8 or confidence < 0.8:
        return
    notification = Notification(
        id=f"notif_{uuid4().hex[:16]}",
        session_id=session_id,
        notification_type=NotificationType.HIGH_PRIORITY,
        priority=priority,
        message=f"High priority memory created: {title}",
        metadata={"memory_id": memory_id},
    )
    await database.create_notification(notification)


# ── Core Memory Operations ────────────────────────────────────────

@mcp.tool()
async def store_memory(
    session_id: str,
    title: str,
    content: str,
    category: str,
    priority: int = 5,
    confidence: float = 0.5,
    tags: Optional[list[str]] = None,
    source: Optional[str] = None,
) -> dict:
    """TinyBrain: Store a security-focused memory entry.

    REQUIRES: An existing session_id from create_session.

    Valid categories: finding, vulnerability, exploit, payload, technique, tool,
    reference, context, hypothesis, evidence, recommendation, note

    Priority: 0-10 (0=low, 10=critical)
    Confidence: 0.0-1.0 (0.0=uncertain, 1.0=certain)
    """
    database = await get_db()
    try:
        memory = Memory(
            id=f"mem_{uuid4().hex[:16]}",
            session_id=session_id,
            title=title,
            content=content,
            category=MemoryCategory(category),
            priority=priority,
            confidence=confidence,
            tags=tags or [],
            source=source,
        )
        await database.create_memory(memory)

        await _create_high_priority_notification(
            database,
            session_id=session_id,
            memory_id=memory.id,
            title=title,
            priority=priority,
            confidence=confidence,
        )

        return {"id": memory.id, "status": "created"}
    except ValueError as e:
        return {
            "error": str(e),
            "valid_categories": [c.value for c in MemoryCategory],
            "hint": "Use list_memory_categories tool for details",
        }


@mcp.tool()
async def get_memory(memory_id: str) -> Optional[dict]:
    """TinyBrain: Get a specific memory by ID."""
    database = await get_db()
    memory = await database.get_memory(memory_id)
    if not memory:
        return None
    return memory.model_dump(mode="json")


@mcp.tool()
async def search_memories(
    query: Optional[str] = None,
    session_id: Optional[str] = None,
    category: Optional[str] = None,
    min_priority: Optional[int] = None,
    limit: int = 20,
) -> list[dict]:
    """TinyBrain: Search memories with filters.

    query: Full-text search across title and content
    session_id: Filter by session
    category: Filter by category (use list_memory_categories)
    min_priority: Minimum priority level (0-10)
    limit: Maximum results to return
    """
    database = await get_db()
    memories = await database.search_memories(
        query=query,
        session_id=session_id,
        category=category,
        min_priority=min_priority,
        limit=limit,
    )
    return [m.model_dump(mode="json") for m in memories]


@mcp.tool()
async def update_memory(
    memory_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    priority: Optional[int] = None,
    confidence: Optional[float] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """TinyBrain: Update an existing memory entry.

    Only provided fields will be updated.
    """
    database = await get_db()
    updates = {}
    if title is not None:
        updates["title"] = title
    if content is not None:
        updates["content"] = content
    if priority is not None:
        updates["priority"] = priority
    if confidence is not None:
        updates["confidence"] = confidence
    if tags is not None:
        updates["tags"] = tags

    success = await database.update_memory(memory_id, updates)
    return {"success": success}


@mcp.tool()
async def delete_memory(memory_id: str) -> dict:
    """TinyBrain: Delete a memory entry."""
    database = await get_db()
    success = await database.delete_memory(memory_id)
    return {"success": success}


# ── Session Management ────────────────────────────────────────────

@mcp.tool()
async def create_session(
    name: str,
    task_type: str,
    description: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """TinyBrain: Create a new security assessment session.

    Valid task_types: security_review, penetration_test, exploit_dev,
    vulnerability_analysis, threat_modeling, incident_response, general

    Returns session_id for use with store_memory and other tools.
    """
    database = await get_db()
    try:
        session = Session(
            id=f"sess_{uuid4().hex[:16]}",
            name=name,
            description=description,
            task_type=TaskType(task_type),
            metadata=metadata,
        )
        await database.create_session(session)
        return {"id": session.id, "status": "created"}
    except ValueError as e:
        return {
            "error": str(e),
            "valid_task_types": [t.value for t in TaskType],
            "hint": "Use list_task_types tool for details",
        }


@mcp.tool()
async def get_session(session_id: str) -> Optional[dict]:
    """TinyBrain: Get session information by ID."""
    database = await get_db()
    session = await database.get_session(session_id)
    if not session:
        return None
    return session.model_dump(mode="json")


@mcp.tool()
async def list_sessions(
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """TinyBrain: List all sessions with optional filters.

    task_type: Filter by task type (use list_task_types)
    status: Filter by status (active, paused, completed, archived)
    """
    database = await get_db()
    sessions = await database.list_sessions(
        task_type=task_type,
        status=status,
        limit=limit,
    )
    return [s.model_dump(mode="json") for s in sessions]


@mcp.tool()
async def delete_session(session_id: str) -> dict:
    """TinyBrain: Delete a session and its memories, relationships, and notifications."""
    database = await get_db()
    success = await database.delete_session(session_id)
    return {"success": success}


# ── Relationship Management ───────────────────────────────────────

@mcp.tool()
async def create_relationship(
    source_memory_id: str,
    target_memory_id: str,
    relationship_type: str,
    strength: float = 0.5,
    description: Optional[str] = None,
) -> dict:
    """TinyBrain: Create a relationship between two memories.

    REQUIRES: Both memory IDs must exist.

    Valid relationship_types: depends_on, causes, mitigates, exploits, references,
    contradicts, supports, related_to, parent_of, child_of

    strength: 0.0-1.0 (0.0=weak, 1.0=strong)
    """
    database = await get_db()
    try:
        relationship = Relationship(
            id=f"rel_{uuid4().hex[:16]}",
            source_entry_id=source_memory_id,
            target_entry_id=target_memory_id,
            relationship_type=RelationshipType(relationship_type),
            strength=strength,
            description=description,
        )
        await database.create_relationship(relationship)
        return {"id": relationship.id, "status": "created"}
    except ValueError as e:
        return {
            "error": str(e),
            "valid_relationship_types": [r.value for r in RelationshipType],
            "hint": "Use list_relationship_types tool for details",
        }


@mcp.tool()
async def get_related_memories(
    memory_id: str, relationship_type: Optional[str] = None, limit: int = 10
) -> list[dict]:
    """TinyBrain: Get memories related to a specific memory.

    relationship_type: Optional filter by relationship type
    """
    database = await get_db()
    memories = await database.get_related_memories(memory_id, relationship_type, limit)
    return [m.model_dump(mode="json") for m in memories]


# ── Notifications ─────────────────────────────────────────────────

@mcp.tool()
async def get_notifications(
    session_id: Optional[str] = None,
    read: Optional[bool] = None,
    limit: int = 20,
) -> list[dict]:
    """TinyBrain: Get notifications and alerts.

    Notifications are created for high-priority memories (priority >= 8, confidence >= 0.8).
    """
    database = await get_db()
    notifications = await database.get_notifications(session_id, read, limit)
    return [n.model_dump(mode="json") for n in notifications]


# ── Health & Stats ────────────────────────────────────────────────

@mcp.tool()
async def health_check() -> dict:
    """TinyBrain: Perform system health check."""
    try:
        await get_db()
        return {
            "status": "healthy",
            "database": "cogdb",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@mcp.tool()
async def get_memory_stats(session_id: Optional[str] = None) -> dict:
    """TinyBrain: Get comprehensive memory statistics.

    Returns counts by category, priority distribution, and access patterns.
    """
    database = await get_db()
    memories = await database.search_memories(
        session_id=session_id, limit=100000
    )

    by_category: dict[str, int] = Counter()
    by_priority: dict[int, int] = Counter()
    total_confidence = 0.0
    high_priority = 0

    for m in memories:
        by_category[m.category.value if hasattr(m.category, "value") else str(m.category)] += 1
        by_priority[m.priority] += 1
        total_confidence += m.confidence
        if m.priority >= 8:
            high_priority += 1

    total = len(memories)
    avg_confidence = round(total_confidence / total, 2) if total else 0.0

    return {
        "total_memories": total,
        "by_category": dict(by_category),
        "by_priority": dict(sorted(by_priority.items(), reverse=True)),
        "high_priority_count": high_priority,
        "average_confidence": avg_confidence,
    }


# ── Tag-Based Linking ─────────────────────────────────────────────

@mcp.tool()
async def get_popular_tags(
    session_id: Optional[str] = None, limit: int = 20
) -> dict:
    """TinyBrain: Get most frequently used tags across memories.

    Helps discover common themes and topics in your security work.
    """
    database = await get_db()
    memories = await database.search_memories(
        session_id=session_id, limit=100000
    )

    tag_counts: dict[str, int] = Counter()
    for m in memories:
        for tag in m.tags:
            tag_counts[tag] += 1

    sorted_tags = tag_counts.most_common(limit)
    return {
        "tags": [{"tag": tag, "count": count} for tag, count in sorted_tags],
        "total_unique_tags": len(tag_counts),
    }


@mcp.tool()
async def find_memories_by_tags(
    tags: list[str],
    match_all: bool = False,
    session_id: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """TinyBrain: Find memories that have specific tags.

    match_all=True: Memories must have ALL specified tags
    match_all=False: Memories with ANY of the specified tags

    Great for discovering related findings across sessions.
    """
    database = await get_db()
    memories = await database.search_memories(
        session_id=session_id, limit=100000
    )

    matches = []
    for m in memories:
        if match_all:
            if all(tag in m.tags for tag in tags):
                matches.append(m)
        else:
            if any(tag in m.tags for tag in tags):
                matches.append(m)
        if len(matches) >= limit:
            break

    return [m.model_dump(mode="json") for m in matches]


@mcp.tool()
async def suggest_related_by_tags(memory_id: str, limit: int = 10) -> dict:
    """TinyBrain: Suggest related memories based on shared tags.

    Passive linking - finds memories with overlapping tags.
    Returns memories sorted by number of shared tags.
    """
    database = await get_db()

    source = await database.get_memory(memory_id)
    if not source or not source.tags:
        return {"related": [], "message": "No tags found on source memory"}

    all_memories = await database.search_memories(limit=100000)

    related = []
    source_tag_set = set(source.tags)
    for m in all_memories:
        if m.id == memory_id:
            continue
        shared = source_tag_set & set(m.tags)
        if shared:
            related.append(
                {
                    "memory": m.model_dump(mode="json"),
                    "shared_tags": list(shared),
                    "overlap_count": len(shared),
                }
            )

    related.sort(key=lambda x: x["overlap_count"], reverse=True)

    return {
        "source_tags": source.tags,
        "related": related[:limit],
        "total_found": len(related),
    }


# ── Parity & Analysis Tools ───────────────────────────────────────

@mcp.tool()
async def calculate_similarity(text_a: str, text_b: str) -> dict:
    """TinyBrain: Calculate deterministic token similarity between two text blocks."""
    return {
        "similarity": _cosine_similarity(text_a, text_b),
        "method": "token_cosine",
    }


@mcp.tool()
async def generate_embedding(text: str, dimensions: int = 64) -> dict:
    """TinyBrain: Generate a deterministic local feature vector for lightweight matching.

    This is not a neural embedding. It is stable, offline, and useful for duplicate
    detection, test fixtures, and tools that need an embedding-shaped signal.
    """
    dimensions = max(8, min(dimensions, 512))
    vector = [0.0] * dimensions
    tokens = _tokenize(text)
    for token in tokens:
        idx = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16) % dimensions
        vector[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return {
        "embedding": [round(v / norm, 6) for v in vector],
        "dimensions": dimensions,
        "method": "hashed_token_counts",
        "token_count": len(tokens),
    }


@mcp.tool()
async def find_similar_memories(
    memory_id: str,
    session_id: Optional[str] = None,
    threshold: float = 0.35,
    limit: int = 10,
) -> dict:
    """TinyBrain: Find memories similar to a source memory using local text similarity."""
    database = await get_db()
    source = await database.get_memory(memory_id)
    if not source:
        return {"error": f"Memory not found: {memory_id}"}

    memories = await database.search_memories(session_id=session_id, limit=100000)
    source_text = _memory_text(source)
    matches = []
    for memory in memories:
        if memory.id == memory_id:
            continue
        score = _cosine_similarity(source_text, _memory_text(memory))
        if score >= threshold:
            matches.append({"memory": _memory_preview(memory), "similarity": score})
    matches.sort(key=lambda item: item["similarity"], reverse=True)
    return {"source_memory_id": memory_id, "matches": matches[:limit], "count": len(matches)}


@mcp.tool()
async def semantic_search(
    query: str,
    session_id: Optional[str] = None,
    category: Optional[str] = None,
    min_score: float = 0.15,
    limit: int = 20,
) -> dict:
    """TinyBrain: Search memories ranked by deterministic local semantic-ish similarity."""
    database = await get_db()
    memories = await database.search_memories(session_id=session_id, category=category, limit=100000)
    results = []
    for memory in memories:
        score = _cosine_similarity(query, _memory_text(memory))
        if score >= min_score:
            results.append({"memory": _memory_preview(memory), "score": score})
    results.sort(key=lambda item: item["score"], reverse=True)
    return {"results": results[:limit], "count": len(results), "method": "token_cosine"}


@mcp.tool()
async def check_duplicates(
    session_id: Optional[str] = None,
    threshold: float = 0.9,
    limit: int = 50,
) -> dict:
    """TinyBrain: Detect likely duplicate memories."""
    database = await get_db()
    memories = await database.search_memories(session_id=session_id, limit=100000)
    duplicates = []
    for i, left in enumerate(memories):
        for right in memories[i + 1:]:
            title_match = left.title.strip().lower() == right.title.strip().lower()
            score = _cosine_similarity(_memory_text(left), _memory_text(right))
            if title_match or score >= threshold:
                duplicates.append(
                    {
                        "memory_a": _memory_preview(left),
                        "memory_b": _memory_preview(right),
                        "similarity": score,
                        "reason": "same_title" if title_match else "content_similarity",
                    }
                )
    duplicates.sort(key=lambda item: item["similarity"], reverse=True)
    return {"duplicates": duplicates[:limit], "count": len(duplicates)}


@mcp.tool()
async def batch_create_memories(session_id: str, memories: list[dict]) -> dict:
    """TinyBrain: Create multiple memories in one call."""
    database = await get_db()
    created = []
    errors = []
    for index, item in enumerate(memories):
        try:
            memory = Memory(
                id=item.get("id") or f"mem_{uuid4().hex[:16]}",
                session_id=session_id,
                title=item["title"],
                content=item["content"],
                category=MemoryCategory(item["category"]),
                priority=item.get("priority", 5),
                confidence=item.get("confidence", 0.5),
                tags=item.get("tags") or [],
                source=item.get("source"),
            )
            await database.create_memory(memory)
            await _create_high_priority_notification(
                database,
                session_id=session_id,
                memory_id=memory.id,
                title=memory.title,
                priority=memory.priority,
                confidence=memory.confidence,
            )
            created.append(memory.model_dump(mode="json"))
        except Exception as exc:
            errors.append({"index": index, "error": str(exc)})
    return {"created": created, "created_count": len(created), "errors": errors}


@mcp.tool()
async def batch_update_memories(updates: list[dict]) -> dict:
    """TinyBrain: Update multiple memories. Each item requires memory_id plus fields."""
    database = await get_db()
    updated = []
    errors = []
    for index, item in enumerate(updates):
        memory_id = item.get("memory_id") or item.get("id")
        if not memory_id:
            errors.append({"index": index, "error": "memory_id is required"})
            continue
        allowed = {"title", "content", "priority", "confidence", "tags", "source", "category"}
        patch = {key: value for key, value in item.items() if key in allowed}
        success = await database.update_memory(memory_id, patch)
        if success:
            updated.append(memory_id)
        else:
            errors.append({"index": index, "memory_id": memory_id, "error": "not found"})
    return {"updated": updated, "updated_count": len(updated), "errors": errors}


@mcp.tool()
async def batch_delete_memories(memory_ids: list[str]) -> dict:
    """TinyBrain: Delete multiple memories in one call."""
    database = await get_db()
    deleted = []
    missing = []
    for memory_id in memory_ids:
        if await database.delete_memory(memory_id):
            deleted.append(memory_id)
        else:
            missing.append(memory_id)
    return {"deleted": deleted, "deleted_count": len(deleted), "missing": missing}


@mcp.tool()
async def cleanup_orphan_relationships() -> dict:
    """TinyBrain: Delete relationship records whose source or target memory is missing."""
    database = await get_db()
    return await database.cleanup_orphan_relationships()


@mcp.tool()
async def export_session_data(session_id: str) -> dict:
    """TinyBrain: Export a session with its memories and relationships."""
    database = await get_db()
    session = await database.get_session(session_id)
    if not session:
        return {"error": f"Session not found: {session_id}"}
    memories = await database.search_memories(session_id=session_id, limit=100000)
    memory_ids = {m.id for m in memories}
    relationships = [
        r for r in await database.list_relationships(limit=100000)
        if r.source_entry_id in memory_ids or r.target_entry_id in memory_ids
    ]
    return {
        "schema_version": "tinybrain-export-v1",
        "exported_at": datetime.utcnow().isoformat(),
        "session": session.model_dump(mode="json"),
        "memories": [m.model_dump(mode="json") for m in memories],
        "relationships": [r.model_dump(mode="json") for r in relationships],
    }


@mcp.tool()
async def import_session_data(data: dict, preserve_ids: bool = True) -> dict:
    """TinyBrain: Import data produced by export_session_data."""
    database = await get_db()
    id_map = {}
    session_data = dict(data["session"])
    if not preserve_ids:
        old_session_id = session_data["id"]
        session_data["id"] = f"sess_{uuid4().hex[:16]}"
        id_map[old_session_id] = session_data["id"]
    session = Session(**session_data)
    await database.create_session(session)

    imported_memories = []
    for item in data.get("memories", []):
        memory_data = dict(item)
        if not preserve_ids:
            old_id = memory_data["id"]
            memory_data["id"] = f"mem_{uuid4().hex[:16]}"
            memory_data["session_id"] = session.id
            id_map[old_id] = memory_data["id"]
        memory = Memory(**memory_data)
        await database.create_memory(memory)
        imported_memories.append(memory.id)

    imported_relationships = []
    for item in data.get("relationships", []):
        rel_data = dict(item)
        if not preserve_ids:
            rel_data["id"] = f"rel_{uuid4().hex[:16]}"
            rel_data["source_entry_id"] = id_map.get(rel_data["source_entry_id"], rel_data["source_entry_id"])
            rel_data["target_entry_id"] = id_map.get(rel_data["target_entry_id"], rel_data["target_entry_id"])
        relationship = Relationship(**rel_data)
        await database.create_relationship(relationship)
        imported_relationships.append(relationship.id)

    return {
        "session_id": session.id,
        "memories_imported": len(imported_memories),
        "relationships_imported": len(imported_relationships),
        "id_map": id_map,
    }


@mcp.tool()
async def get_context_summary(session_id: str, max_memories: int = 20) -> dict:
    """TinyBrain: Produce a compact context packet for LLM coding/security agents."""
    database = await get_db()
    session = await database.get_session(session_id)
    if not session:
        return {"error": f"Session not found: {session_id}"}
    memories = await database.search_memories(session_id=session_id, limit=100000)
    memories.sort(key=lambda m: (m.priority, m.confidence, m.updated_at), reverse=True)
    tag_counts = Counter(tag for m in memories for tag in m.tags)
    return {
        "session": session.model_dump(mode="json"),
        "memory_count": len(memories),
        "top_tags": [{"tag": tag, "count": count} for tag, count in tag_counts.most_common(15)],
        "high_signal_memories": [_memory_preview(m) for m in memories[:max_memories]],
    }


@mcp.tool()
async def get_detailed_memory_info(memory_id: str) -> dict:
    """TinyBrain: Return a memory with related entries and similarity hints."""
    database = await get_db()
    memory = await database.get_memory(memory_id)
    if not memory:
        return {"error": f"Memory not found: {memory_id}"}
    related = await database.get_related_memories(memory_id, limit=25)
    similar = await find_similar_memories(memory_id=memory_id, threshold=0.35, limit=10)
    return {
        "memory": memory.model_dump(mode="json"),
        "related_memories": [_memory_preview(m) for m in related],
        "similar_memories": similar.get("matches", []),
    }


@mcp.tool()
async def get_security_templates() -> dict:
    """TinyBrain: List built-in security memory templates."""
    return {"templates": SECURITY_TEMPLATES}


@mcp.tool()
async def create_memory_from_template(
    session_id: str,
    template_name: str,
    title: str,
    values: dict,
    priority: Optional[int] = None,
    confidence: Optional[float] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """TinyBrain: Create a memory from a built-in security template."""
    template = SECURITY_TEMPLATES.get(template_name)
    if not template:
        return {"error": f"Unknown template: {template_name}", "valid_templates": list(SECURITY_TEMPLATES)}
    try:
        content = template["content"].format(**values)
    except KeyError as exc:
        return {"error": f"Missing template value: {exc.args[0]}"}
    return await store_memory(
        session_id=session_id,
        title=title,
        content=content,
        category=template["category"],
        priority=priority if priority is not None else template["priority"],
        confidence=confidence if confidence is not None else template["confidence"],
        tags=(template["tags"] + (tags or [])),
    )


@mcp.tool()
async def mark_notification_read(notification_id: str, read: bool = True) -> dict:
    """TinyBrain: Mark a notification as read or unread."""
    database = await get_db()
    return {"success": await database.mark_notification_read(notification_id, read)}


@mcp.tool()
async def check_high_priority_memories(
    session_id: Optional[str] = None,
    min_priority: int = 8,
    min_confidence: float = 0.8,
    limit: int = 50,
) -> dict:
    """TinyBrain: Find high-priority, high-confidence memories needing attention."""
    database = await get_db()
    memories = await database.search_memories(
        session_id=session_id,
        min_priority=min_priority,
        limit=100000,
    )
    matches = [m for m in memories if m.confidence >= min_confidence]
    matches.sort(key=lambda m: (m.priority, m.confidence), reverse=True)
    return {"memories": [_memory_preview(m) for m in matches[:limit]], "count": len(matches)}


@mcp.tool()
async def check_duplicate_memories(
    session_id: Optional[str] = None,
    threshold: float = 0.9,
    limit: int = 50,
) -> dict:
    """TinyBrain: Alias for check_duplicates for Go-tool compatibility."""
    return await check_duplicates(session_id=session_id, threshold=threshold, limit=limit)


@mcp.tool()
async def get_system_diagnostics() -> dict:
    """TinyBrain: Return storage and tool-surface diagnostics."""
    database = await get_db()
    memories = await database.search_memories(limit=100000)
    sessions = await database.list_sessions(limit=100000)
    relationships = await database.list_relationships(limit=100000)
    notifications = await database.get_notifications(limit=100000)
    return {
        "status": "healthy",
        "database": "cogdb",
        "counts": {
            "sessions": len(sessions),
            "memories": len(memories),
            "relationships": len(relationships),
            "notifications": len(notifications),
        },
        "storage": {
            "cog_home": database.db_path.name,
            "cog_path_prefix": str(database.db_path.parent),
        },
        "feature_notes": {
            "duckdb": "Recommended as an analytical sidecar for CVE/ATT&CK/CWE datasets, not as the primary graph memory store.",
            "embeddings": "Current embedding tools are deterministic local token vectors; neural providers can be added behind the same MCP contract.",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Discovery Tools ──────────────────────────────────────────────

@mcp.tool()
async def list_memory_categories() -> dict:
    """TinyBrain: List all valid memory categories with descriptions."""
    return {
        "categories": {
            "finding": "General security finding",
            "vulnerability": "Security vulnerability",
            "exploit": "Exploit code or technique",
            "payload": "Attack payload",
            "technique": "Attack or defense technique",
            "tool": "Security tool or utility",
            "reference": "Reference material or documentation",
            "context": "Contextual information",
            "hypothesis": "Security hypothesis or theory",
            "evidence": "Evidence supporting a finding",
            "recommendation": "Security recommendation",
            "note": "General note or observation",
        }
    }


@mcp.tool()
async def list_task_types() -> dict:
    """TinyBrain: List all valid task types for sessions."""
    return {
        "task_types": {
            "security_review": "Security code review",
            "penetration_test": "Penetration testing",
            "exploit_dev": "Exploit development",
            "vulnerability_analysis": "Vulnerability analysis",
            "threat_modeling": "Threat modeling",
            "incident_response": "Incident response",
            "general": "General security task",
        }
    }


@mcp.tool()
async def list_relationship_types() -> dict:
    """TinyBrain: List all valid relationship types between memories."""
    return {
        "relationship_types": {
            "depends_on": "Memory depends on another",
            "causes": "Memory causes another",
            "mitigates": "Memory mitigates another",
            "exploits": "Memory exploits another",
            "references": "Memory references another",
            "contradicts": "Memory contradicts another",
            "supports": "Memory supports another",
            "related_to": "Memory is related to another",
            "parent_of": "Memory is parent of another",
            "child_of": "Memory is child of another",
        }
    }


@mcp.tool()
async def get_tinybrain_help() -> dict:
    """TinyBrain: Get quick start guide and usage information."""
    return {
        "quick_start": [
            "1. Create a session: create_session(name='My Review', task_type='security_review')",
            "2. Store memories: store_memory(session_id='sess_xxx', title='Finding', content='Details', category='vulnerability')",
            "3. Search memories: search_memories(query='SQL injection', session_id='sess_xxx')",
            "4. Create relationships: create_relationship(source_memory_id='mem_xxx', target_memory_id='mem_yyy', relationship_type='exploits')",
        ],
        "discovery_tools": [
            "list_memory_categories() - See all valid memory categories",
            "list_task_types() - See all valid task types",
            "list_relationship_types() - See all valid relationship types",
            "get_popular_tags() - See frequently used tags",
        ],
        "workflow": "Session → Memories → Relationships → Search",
        "version": "2.0.0",
    }
