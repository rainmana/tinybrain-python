"""Async SQLite database backend."""

import json
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import aiosqlite
from loguru import logger

from tinybrain.database.schema import SCHEMA
from tinybrain.models import (
    ContextSnapshot,
    Memory,
    Notification,
    Relationship,
    Session,
    TaskProgress,
)


class Database:
    """Async SQLite database."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Connect to database."""
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.commit()
        logger.info(f"Connected to database: {self.db_path}")

    async def initialize(self) -> None:
        """Initialize database schema."""
        if not self._conn:
            await self.connect()
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        logger.info("Database schema initialized")

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            logger.info("Database connection closed")

    # Session operations
    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        await self._conn.execute(
            """INSERT INTO sessions (id, name, description, task_type, status, created_at, updated_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session.id,
                session.name,
                session.description,
                session.task_type.value,
                session.status.value,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                json.dumps(session.metadata) if session.metadata else None,
            ),
        )
        await self._conn.commit()
        logger.info(f"Created session: {session.id}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return Session(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            task_type=row["task_type"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
        )

    # Memory operations
    async def create_memory(self, memory: Memory) -> Memory:
        """Create a new memory entry."""
        await self._conn.execute(
            """INSERT INTO memory_entries 
               (id, session_id, title, content, content_type, category, priority, confidence, 
                tags, source, created_at, updated_at, accessed_at, access_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id,
                memory.session_id,
                memory.title,
                memory.content,
                memory.content_type.value,
                memory.category.value,
                memory.priority,
                memory.confidence,
                json.dumps(memory.tags),
                memory.source,
                memory.created_at.isoformat(),
                memory.updated_at.isoformat(),
                memory.accessed_at.isoformat(),
                memory.access_count,
            ),
        )
        await self._conn.commit()
        logger.info(f"Created memory: {memory.id}")
        return memory

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get memory by ID."""
        cursor = await self._conn.execute(
            "SELECT * FROM memory_entries WHERE id = ?", (memory_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_memory(row)

    async def search_memories(
        self,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        min_priority: Optional[int] = None,
        limit: int = 20,
    ) -> list[Memory]:
        """Search memories with filters."""
        conditions = []
        params = []

        if query:
            # FTS5 search
            cursor = await self._conn.execute(
                """SELECT m.* FROM memory_entries m
                   JOIN memory_entries_fts fts ON m.rowid = fts.rowid
                   WHERE memory_entries_fts MATCH ?
                   ORDER BY rank LIMIT ?""",
                (query, limit),
            )
        else:
            # Regular search with filters
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            if category:
                conditions.append("category = ?")
                params.append(category)
            if min_priority is not None:
                conditions.append("priority >= ?")
                params.append(min_priority)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            cursor = await self._conn.execute(
                f"SELECT * FROM memory_entries WHERE {where_clause} ORDER BY created_at DESC LIMIT ?",
                (*params, limit),
            )

        rows = await cursor.fetchall()
        return [self._row_to_memory(row) for row in rows]

    async def update_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        """Update memory entry."""
        set_clauses = []
        params = []
        for key, value in updates.items():
            if key in ["tags"]:
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            params.append(value)

        if not set_clauses:
            return False

        params.append(memory_id)
        await self._conn.execute(
            f"UPDATE memory_entries SET {', '.join(set_clauses)} WHERE id = ?", params
        )
        await self._conn.commit()
        logger.info(f"Updated memory: {memory_id}")
        return True

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory entry."""
        cursor = await self._conn.execute(
            "DELETE FROM memory_entries WHERE id = ?", (memory_id,)
        )
        await self._conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted memory: {memory_id}")
        return deleted

    # Relationship operations
    async def create_relationship(self, relationship: Relationship) -> Relationship:
        """Create a relationship."""
        await self._conn.execute(
            """INSERT INTO relationships 
               (id, source_entry_id, target_entry_id, relationship_type, strength, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                relationship.id,
                relationship.source_entry_id,
                relationship.target_entry_id,
                relationship.relationship_type.value,
                relationship.strength,
                relationship.description,
                relationship.created_at.isoformat(),
            ),
        )
        await self._conn.commit()
        logger.info(f"Created relationship: {relationship.id}")
        return relationship

    async def get_related_memories(
        self, memory_id: str, relationship_type: Optional[str] = None, limit: int = 10
    ) -> list[Memory]:
        """Get related memories."""
        if relationship_type:
            cursor = await self._conn.execute(
                """SELECT m.* FROM memory_entries m
                   JOIN relationships r ON m.id = r.target_entry_id
                   WHERE r.source_entry_id = ? AND r.relationship_type = ?
                   LIMIT ?""",
                (memory_id, relationship_type, limit),
            )
        else:
            cursor = await self._conn.execute(
                """SELECT m.* FROM memory_entries m
                   JOIN relationships r ON m.id = r.target_entry_id
                   WHERE r.source_entry_id = ?
                   LIMIT ?""",
                (memory_id, limit),
            )

        rows = await cursor.fetchall()
        return [self._row_to_memory(row) for row in rows]

    # Notification operations
    async def create_notification(self, notification: Notification) -> Notification:
        """Create a notification."""
        await self._conn.execute(
            """INSERT INTO notifications 
               (id, session_id, notification_type, priority, message, metadata, read, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                notification.id,
                notification.session_id,
                notification.notification_type.value,
                notification.priority,
                notification.message,
                json.dumps(notification.metadata) if notification.metadata else None,
                1 if notification.read else 0,
                notification.created_at.isoformat(),
            ),
        )
        await self._conn.commit()
        return notification

    async def get_notifications(
        self, session_id: Optional[str] = None, read: Optional[bool] = None, limit: int = 20
    ) -> list[Notification]:
        """Get notifications."""
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if read is not None:
            conditions.append("read = ?")
            params.append(1 if read else 0)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        cursor = await self._conn.execute(
            f"SELECT * FROM notifications WHERE {where_clause} ORDER BY created_at DESC LIMIT ?",
            (*params, limit),
        )

        rows = await cursor.fetchall()
        return [self._row_to_notification(row) for row in rows]

    # Helper methods
    def _row_to_memory(self, row: aiosqlite.Row) -> Memory:
        """Convert database row to Memory model."""
        return Memory(
            id=row["id"],
            session_id=row["session_id"],
            title=row["title"],
            content=row["content"],
            content_type=row["content_type"],
            category=row["category"],
            priority=row["priority"],
            confidence=row["confidence"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            source=row["source"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            accessed_at=row["accessed_at"],
            access_count=row["access_count"],
        )

    def _row_to_notification(self, row: aiosqlite.Row) -> Notification:
        """Convert database row to Notification model."""
        return Notification(
            id=row["id"],
            session_id=row["session_id"],
            notification_type=row["notification_type"],
            priority=row["priority"],
            message=row["message"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            read=bool(row["read"]),
            created_at=row["created_at"],
        )
