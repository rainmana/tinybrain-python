"""FastMCP server with all TinyBrain tools."""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastmcp import FastMCP
from loguru import logger

from tinybrain.database import Database
from tinybrain.models import (
    ContextSnapshot,
    Memory,
    MemoryCategory,
    Notification,
    NotificationType,
    Relationship,
    RelationshipType,
    Session,
    SessionStatus,
    TaskProgress,
    TaskStatus,
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

        if priority >= 8 and confidence >= 0.8:
            notification = Notification(
                id=f"notif_{uuid4().hex[:16]}",
                session_id=session_id,
                notification_type=NotificationType.HIGH_PRIORITY,
                priority=priority,
                message=f"High priority memory created: {title}",
                metadata={"memory_id": memory.id},
            )
            await database.create_notification(notification)

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
        database = await get_db()
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
