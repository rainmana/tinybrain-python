"""SQLite database backend implementation."""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from tinybrain.database.base import DatabaseBackend
from tinybrain.models.memory import Memory, MemoryCreateRequest, MemoryUpdateRequest
from tinybrain.models.session import Session, SessionCreateRequest, SessionUpdateRequest
from tinybrain.models.relationship import (
    Relationship,
    RelationshipCreateRequest,
    RelationshipType,
)
from tinybrain.models.context_snapshot import (
    ContextSnapshot,
    ContextSnapshotCreateRequest,
)
from tinybrain.models.task_progress import (
    TaskProgress,
    TaskProgressCreateRequest,
    TaskProgressUpdateRequest,
)


class SQLiteBackend(DatabaseBackend):
    """SQLite implementation of the database backend."""

    def __init__(self, db_path: str | Path):
        """Initialize the SQLite backend."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize the database connection and schema."""
        self._connection = await aiosqlite.connect(
            str(self.db_path),
            isolation_level=None,  # Autocommit mode
        )
        # Enable WAL mode and foreign keys
        await self._connection.execute("PRAGMA foreign_keys = ON")
        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.execute("PRAGMA case_sensitive_like = OFF")
        await self._connection.execute("PRAGMA busy_timeout = 30000")

        # Create schema
        await self._create_schema()
        await self._connection.commit()

    async def _create_schema(self) -> None:
        """Create the database schema."""
        schema = """
        -- Sessions table
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            task_type TEXT NOT NULL CHECK (task_type IN ('security_review', 'penetration_test', 'exploit_dev', 'vulnerability_analysis', 'threat_modeling', 'incident_response', 'general')),
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        );

        -- Memory entries table
        CREATE TABLE IF NOT EXISTS memory_entries (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'text' CHECK (content_type IN ('text', 'code', 'json', 'yaml', 'markdown', 'binary_ref')),
            category TEXT NOT NULL CHECK (category IN ('finding', 'vulnerability', 'exploit', 'payload', 'technique', 'tool', 'reference', 'context', 'hypothesis', 'evidence', 'recommendation', 'note')),
            priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 10),
            confidence REAL DEFAULT 0.5 CHECK (confidence >= 0.0 AND confidence <= 1.0),
            tags TEXT,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            access_count INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        -- Relationships table
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            source_entry_id TEXT NOT NULL,
            target_entry_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL CHECK (relationship_type IN ('depends_on', 'causes', 'mitigates', 'exploits', 'references', 'contradicts', 'supports', 'related_to', 'parent_of', 'child_of')),
            strength REAL DEFAULT 0.5 CHECK (strength >= 0.0 AND strength <= 1.0),
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_entry_id) REFERENCES memory_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (target_entry_id) REFERENCES memory_entries(id) ON DELETE CASCADE,
            UNIQUE(source_entry_id, target_entry_id, relationship_type)
        );

        -- Context snapshots table
        CREATE TABLE IF NOT EXISTS context_snapshots (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            context_data TEXT NOT NULL,
            memory_summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        -- Task progress table
        CREATE TABLE IF NOT EXISTS task_progress (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            task_name TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'blocked')),
            progress_percentage REAL DEFAULT 0.0 CHECK (progress_percentage >= 0.0 AND progress_percentage <= 100.0),
            notes TEXT,
            started_at DATETIME,
            completed_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_memory_entries_session_id ON memory_entries(session_id);
        CREATE INDEX IF NOT EXISTS idx_memory_entries_category ON memory_entries(category);
        CREATE INDEX IF NOT EXISTS idx_memory_entries_priority ON memory_entries(priority);
        CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_entry_id);
        CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_entry_id);
        CREATE INDEX IF NOT EXISTS idx_context_snapshots_session_id ON context_snapshots(session_id);
        CREATE INDEX IF NOT EXISTS idx_task_progress_session_id ON task_progress(session_id);

        -- Create FTS5 virtual table if available
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_entries_fts USING fts5(
            title,
            content,
            tags,
            content='memory_entries',
            content_rowid='rowid'
        );

        -- FTS triggers
        CREATE TRIGGER IF NOT EXISTS memory_entries_fts_insert AFTER INSERT ON memory_entries BEGIN
            INSERT INTO memory_entries_fts(rowid, title, content, tags) 
            VALUES (new.rowid, new.title, new.content, new.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS memory_entries_fts_delete AFTER DELETE ON memory_entries BEGIN
            INSERT INTO memory_entries_fts(memory_entries_fts, rowid, title, content, tags) 
            VALUES('delete', old.rowid, old.title, old.content, old.tags);
        END;

        CREATE TRIGGER IF NOT EXISTS memory_entries_fts_update AFTER UPDATE ON memory_entries BEGIN
            INSERT INTO memory_entries_fts(memory_entries_fts, rowid, title, content, tags) 
            VALUES('delete', old.rowid, old.title, old.content, old.tags);
            INSERT INTO memory_entries_fts(rowid, title, content, tags) 
            VALUES (new.rowid, new.title, new.content, new.tags);
        END;

        -- Security Knowledge Hub Tables
        CREATE TABLE IF NOT EXISTS nvd_cves (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            cvss_v2_score REAL,
            cvss_v2_vector TEXT,
            cvss_v3_score REAL,
            cvss_v3_vector TEXT,
            severity TEXT CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
            published_date DATETIME,
            last_modified_date DATETIME,
            cwe_ids TEXT,
            affected_products TEXT,
            refs TEXT,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attack_techniques (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            tactic TEXT NOT NULL,
            tactics TEXT,
            platforms TEXT,
            kill_chain_phases TEXT,
            data_sources TEXT,
            detection TEXT,
            mitigation TEXT,
            refs TEXT,
            sub_techniques TEXT,
            parent_technique TEXT,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS attack_tactics (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            external_id TEXT,
            kill_chain_phases TEXT,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS owasp_procedures (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            subcategory TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            objective TEXT,
            how_to_test TEXT,
            tools TEXT,
            refs TEXT,
            severity TEXT CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS security_data_updates (
            id TEXT PRIMARY KEY,
            data_source TEXT NOT NULL CHECK (data_source IN ('nvd', 'attack', 'owasp')),
            last_update DATETIME,
            total_records INTEGER,
            update_status TEXT CHECK (update_status IN ('pending', 'in_progress', 'completed', 'failed')),
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for security data
        CREATE INDEX IF NOT EXISTS idx_nvd_cves_severity ON nvd_cves(severity);
        CREATE INDEX IF NOT EXISTS idx_nvd_cves_published ON nvd_cves(published_date);
        CREATE INDEX IF NOT EXISTS idx_nvd_cves_cvss3 ON nvd_cves(cvss_v3_score);
        CREATE INDEX IF NOT EXISTS idx_attack_techniques_tactic ON attack_techniques(tactic);
        CREATE INDEX IF NOT EXISTS idx_owasp_procedures_category ON owasp_procedures(category);
        """
        await self._connection.executescript(schema)

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def health_check(self) -> bool:
        """Perform a health check."""
        try:
            if not self._connection:
                return False
            await self._connection.execute("SELECT 1")
            return True
        except Exception:
            return False

    # Session operations
    async def create_session(self, request: SessionCreateRequest) -> Session:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        metadata_json = json.dumps(request.metadata or {})

        await self._connection.execute(
            """
            INSERT INTO sessions (id, name, description, task_type, status, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (
                session_id,
                request.name,
                request.description,
                request.task_type,
                metadata_json,
                now,
                now,
            ),
        )

        return Session(
            id=session_id,
            name=request.name,
            task_type=request.task_type,
            status="active",
            description=request.description,
            metadata=request.metadata or {},
            created_at=now,
            updated_at=now,
        )

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        async with self._connection.execute(
            "SELECT id, name, description, task_type, status, metadata, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            metadata = {}
            if row[5]:
                try:
                    metadata = json.loads(row[5])
                except (json.JSONDecodeError, TypeError):
                    pass

            return Session(
                id=row[0],
                name=row[1],
                description=row[2],
                task_type=row[3],
                status=row[4],
                metadata=metadata,
                created_at=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6],
                updated_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
            )

    async def list_sessions(
        self, limit: int = 50, offset: int = 0, status: Optional[str] = None, task_type: Optional[str] = None
    ) -> list[Session]:
        """List sessions with optional filtering."""
        query = "SELECT id, name, description, task_type, status, metadata, created_at, updated_at FROM sessions WHERE 1=1"
        params: list[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        sessions = []
        async with self._connection.execute(query, params) as cursor:
            async for row in cursor:
                metadata = {}
                if row[5]:
                    try:
                        metadata = json.loads(row[5])
                    except (json.JSONDecodeError, TypeError):
                        pass

                sessions.append(
                    Session(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        task_type=row[3],
                        status=row[4],
                        metadata=metadata,
                        created_at=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6],
                        updated_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
                    )
                )

        return sessions

    async def update_session(self, session_id: str, request: SessionUpdateRequest) -> Session:
        """Update a session."""
        updates = []
        params: list[Any] = []

        if request.name is not None:
            updates.append("name = ?")
            params.append(request.name)
        if request.status is not None:
            updates.append("status = ?")
            params.append(request.status)
        if request.description is not None:
            updates.append("description = ?")
            params.append(request.description)
        if request.metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(request.metadata))

        if not updates:
            # No updates, just return the existing session
            session = await self.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            return session

        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(session_id)

        query = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
        await self._connection.execute(query, params)

        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        cursor = await self._connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0

    # Memory operations
    async def create_memory(self, request: MemoryCreateRequest) -> Memory:
        """Create a new memory entry."""
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow()
        tags_json = json.dumps(request.tags or [])

        await self._connection.execute(
            """
            INSERT INTO memory_entries (id, session_id, title, content, category, priority, confidence, tags, source, content_type, created_at, updated_at, accessed_at, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id,
                request.session_id,
                request.title,
                request.content,
                request.category,
                request.priority,
                request.confidence,
                tags_json,
                request.source,
                request.content_type,
                now,
                now,
                now,
                0,
            ),
        )

        return Memory(
            id=memory_id,
            session_id=request.session_id,
            title=request.title,
            content=request.content,
            category=request.category,
            priority=request.priority,
            confidence=request.confidence,
            tags=request.tags or [],
            source=request.source,
            content_type=request.content_type,
            created_at=now,
            updated_at=now,
            accessed_at=now,
            access_count=0,
        )

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory entry by ID."""
        # Update access count
        await self._connection.execute(
            "UPDATE memory_entries SET access_count = access_count + 1, accessed_at = ? WHERE id = ?",
            (datetime.utcnow(), memory_id),
        )

        async with self._connection.execute(
            "SELECT id, session_id, title, content, category, priority, confidence, tags, source, content_type, created_at, updated_at, accessed_at, access_count FROM memory_entries WHERE id = ?",
            (memory_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            tags = []
            if row[7]:
                try:
                    tags = json.loads(row[7])
                except (json.JSONDecodeError, TypeError):
                    pass

            return Memory(
                id=row[0],
                session_id=row[1],
                title=row[2],
                content=row[3],
                category=row[4],
                priority=row[5],
                confidence=row[6],
                tags=tags,
                source=row[8],
                content_type=row[9],
                created_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
                updated_at=datetime.fromisoformat(row[11]) if isinstance(row[11], str) else row[11],
                accessed_at=datetime.fromisoformat(row[12]) if isinstance(row[12], str) else row[12],
                access_count=row[13],
            )

    async def update_memory(self, memory_id: str, request: MemoryUpdateRequest) -> Memory:
        """Update a memory entry."""
        updates = []
        params: list[Any] = []

        if request.title is not None:
            updates.append("title = ?")
            params.append(request.title)
        if request.content is not None:
            updates.append("content = ?")
            params.append(request.content)
        if request.category is not None:
            updates.append("category = ?")
            params.append(request.category)
        if request.priority is not None:
            updates.append("priority = ?")
            params.append(request.priority)
        if request.confidence is not None:
            updates.append("confidence = ?")
            params.append(request.confidence)
        if request.tags is not None:
            updates.append("tags = ?")
            params.append(json.dumps(request.tags))
        if request.source is not None:
            updates.append("source = ?")
            params.append(request.source)
        if request.content_type is not None:
            updates.append("content_type = ?")
            params.append(request.content_type)

        if not updates:
            memory = await self.get_memory(memory_id)
            if not memory:
                raise ValueError(f"Memory {memory_id} not found")
            return memory

        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(memory_id)

        query = f"UPDATE memory_entries SET {', '.join(updates)} WHERE id = ?"
        await self._connection.execute(query, params)

        memory = await self.get_memory(memory_id)
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")
        return memory

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        cursor = await self._connection.execute("DELETE FROM memory_entries WHERE id = ?", (memory_id,))
        return cursor.rowcount > 0

    async def search_memories(
        self,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        min_priority: Optional[int] = None,
        min_confidence: Optional[float] = None,
        search_type: str = "semantic",
        limit: int = 20,
        offset: int = 0,
    ) -> list[Memory]:
        """Search for memory entries."""
        conditions = []
        params: list[Any] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if min_priority is not None:
            conditions.append("priority >= ?")
            params.append(min_priority)
        if min_confidence is not None:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        if tags:
            # Search for memories that have any of the specified tags
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        if query and search_type == "semantic":
            # Try FTS5 search first, but fall back to LIKE if FTS5 table doesn't exist or query fails
            # Check if FTS5 table exists by trying the query
            fts_query = query.replace(" ", " OR ")
            base_query = f"""
                SELECT DISTINCT me.id, me.session_id, me.title, me.content, me.category, 
                       me.priority, me.confidence, me.tags, me.source, me.content_type,
                       me.created_at, me.updated_at, me.accessed_at, me.access_count
                FROM memory_entries me
                JOIN memory_entries_fts fts ON me.rowid = fts.rowid
                WHERE memory_entries_fts MATCH ? AND {where_clause}
                ORDER BY me.created_at DESC
                LIMIT ? OFFSET ?
            """
            params = [fts_query] + params + [limit, offset]
        elif query:
            # Use LIKE for fuzzy search
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
            where_clause = " AND ".join(conditions)
            base_query = f"""
                SELECT id, session_id, title, content, category, priority, confidence, tags, source, content_type,
                       created_at, updated_at, accessed_at, access_count
                FROM memory_entries
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
        else:
            base_query = f"""
                SELECT id, session_id, title, content, category, priority, confidence, tags, source, content_type,
                       created_at, updated_at, accessed_at, access_count
                FROM memory_entries
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

        memories = []
        try:
            async with self._connection.execute(base_query, params) as cursor:
                async for row in cursor:
                    tags_list = []
                    if row[7]:
                        try:
                            tags_list = json.loads(row[7])
                        except (json.JSONDecodeError, TypeError):
                            pass

                    memories.append(
                        Memory(
                            id=row[0],
                            session_id=row[1],
                            title=row[2],
                            content=row[3],
                            category=row[4],
                            priority=row[5],
                            confidence=row[6],
                            tags=tags_list,
                            source=row[8],
                            content_type=row[9],
                            created_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
                            updated_at=datetime.fromisoformat(row[11]) if isinstance(row[11], str) else row[11],
                            accessed_at=datetime.fromisoformat(row[12]) if isinstance(row[12], str) else row[12],
                            access_count=row[13],
                        )
                    )
        except Exception:
            # FTS5 not available or query failed, fall back to LIKE search
            if query:
                # Rebuild conditions and params for LIKE search
                conditions = []
                params = []
                if session_id:
                    conditions.append("session_id = ?")
                    params.append(session_id)
                if category:
                    conditions.append("category = ?")
                    params.append(category)
                if min_priority is not None:
                    conditions.append("priority >= ?")
                    params.append(min_priority)
                if min_confidence is not None:
                    conditions.append("confidence >= ?")
                    params.append(min_confidence)
                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append("tags LIKE ?")
                        params.append(f'%"{tag}"%')
                    if tag_conditions:
                        conditions.append(f"({' OR '.join(tag_conditions)})")
                
                conditions.append("(title LIKE ? OR content LIKE ?)")
                params.extend([f"%{query}%", f"%{query}%"])
                where_clause = " AND ".join(conditions)
                base_query = f"""
                    SELECT id, session_id, title, content, category, priority, confidence, tags, source, content_type,
                           created_at, updated_at, accessed_at, access_count
                    FROM memory_entries
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                async with self._connection.execute(base_query, params) as cursor:
                    async for row in cursor:
                        tags_list = []
                        if row[7]:
                            try:
                                tags_list = json.loads(row[7])
                            except (json.JSONDecodeError, TypeError):
                                pass

                        memories.append(
                            Memory(
                                id=row[0],
                                session_id=row[1],
                                title=row[2],
                                content=row[3],
                                category=row[4],
                                priority=row[5],
                                confidence=row[6],
                                tags=tags_list,
                                source=row[8],
                                content_type=row[9],
                                created_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
                                updated_at=datetime.fromisoformat(row[11]) if isinstance(row[11], str) else row[11],
                                accessed_at=datetime.fromisoformat(row[12]) if isinstance(row[12], str) else row[12],
                                access_count=row[13],
                            )
                        )
                tags_list = []
                if row[7]:
                    try:
                        tags_list = json.loads(row[7])
                    except (json.JSONDecodeError, TypeError):
                        pass

                memories.append(
                    Memory(
                        id=row[0],
                        session_id=row[1],
                        title=row[2],
                        content=row[3],
                        category=row[4],
                        priority=row[5],
                        confidence=row[6],
                        tags=tags_list,
                        source=row[8],
                        content_type=row[9],
                        created_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
                        updated_at=datetime.fromisoformat(row[11]) if isinstance(row[11], str) else row[11],
                        accessed_at=datetime.fromisoformat(row[12]) if isinstance(row[12], str) else row[12],
                        access_count=row[13],
                    )
                )

        return memories

    # Relationship operations
    async def create_relationship(self, request: RelationshipCreateRequest) -> Relationship:
        """Create a new relationship."""
        relationship_id = str(uuid.uuid4())
        now = datetime.utcnow()

        await self._connection.execute(
            """
            INSERT INTO relationships (id, source_entry_id, target_entry_id, relationship_type, strength, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                relationship_id,
                request.source_id,
                request.target_id,
                request.type.value,
                request.strength,
                request.description,
                now,
                now,
            ),
        )

        return Relationship(
            id=relationship_id,
            source_id=request.source_id,
            target_id=request.target_id,
            type=request.type,
            strength=request.strength,
            description=request.description,
            created_at=now,
            updated_at=now,
        )

    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID."""
        async with self._connection.execute(
            "SELECT id, source_entry_id, target_entry_id, relationship_type, strength, description, created_at, updated_at FROM relationships WHERE id = ?",
            (relationship_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            return Relationship(
                id=row[0],
                source_id=row[1],
                target_id=row[2],
                type=RelationshipType(row[3]),
                strength=row[4],
                description=row[5],
                created_at=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6],
                updated_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
            )

    async def get_related_memories(
        self, memory_id: str, relationship_type: Optional[str] = None, limit: int = 10
    ) -> list[Memory]:
        """Get memories related to a specific memory."""
        query = """
            SELECT DISTINCT me.id, me.session_id, me.title, me.content, me.category, 
                   me.priority, me.confidence, me.tags, me.source, me.content_type,
                   me.created_at, me.updated_at, me.accessed_at, me.access_count
            FROM memory_entries me
            JOIN relationships r ON (me.id = r.target_entry_id OR me.id = r.source_entry_id)
            WHERE (r.source_entry_id = ? OR r.target_entry_id = ?) AND me.id != ?
        """
        params: list[Any] = [memory_id, memory_id, memory_id]

        if relationship_type:
            query += " AND r.relationship_type = ?"
            params.append(relationship_type)

        query += " ORDER BY r.strength DESC, me.created_at DESC LIMIT ?"
        params.append(limit)

        memories = []
        async with self._connection.execute(query, params) as cursor:
            async for row in cursor:
                tags_list = []
                if row[7]:
                    try:
                        tags_list = json.loads(row[7])
                    except (json.JSONDecodeError, TypeError):
                        pass

                memories.append(
                    Memory(
                        id=row[0],
                        session_id=row[1],
                        title=row[2],
                        content=row[3],
                        category=row[4],
                        priority=row[5],
                        confidence=row[6],
                        tags=tags_list,
                        source=row[8],
                        content_type=row[9],
                        created_at=datetime.fromisoformat(row[10]) if isinstance(row[10], str) else row[10],
                        updated_at=datetime.fromisoformat(row[11]) if isinstance(row[11], str) else row[11],
                        accessed_at=datetime.fromisoformat(row[12]) if isinstance(row[12], str) else row[12],
                        access_count=row[13],
                    )
                )

        return memories

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        cursor = await self._connection.execute(
            "DELETE FROM relationships WHERE id = ?", (relationship_id,)
        )
        return cursor.rowcount > 0

    # Context snapshot operations
    async def create_context_snapshot(
        self, request: ContextSnapshotCreateRequest
    ) -> ContextSnapshot:
        """Create a new context snapshot."""
        snapshot_id = str(uuid.uuid4())
        now = datetime.utcnow()
        context_data_json = json.dumps(request.context_data)

        await self._connection.execute(
            """
            INSERT INTO context_snapshots (id, session_id, name, description, context_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                request.session_id,
                request.name,
                request.description,
                context_data_json,
                now,
                now,
            ),
        )

        return ContextSnapshot(
            id=snapshot_id,
            session_id=request.session_id,
            name=request.name,
            context_data=request.context_data,
            description=request.description,
            created_at=now,
            updated_at=now,
        )

    async def get_context_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Get a context snapshot by ID."""
        async with self._connection.execute(
            "SELECT id, session_id, name, description, context_data, created_at, updated_at FROM context_snapshots WHERE id = ?",
            (snapshot_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            context_data = {}
            if row[4]:
                try:
                    context_data = json.loads(row[4])
                except (json.JSONDecodeError, TypeError):
                    pass

            return ContextSnapshot(
                id=row[0],
                session_id=row[1],
                name=row[2],
                description=row[3],
                context_data=context_data,
                created_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                updated_at=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6],
            )

    async def list_context_snapshots(
        self, session_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[ContextSnapshot]:
        """List context snapshots."""
        if session_id:
            query = "SELECT id, session_id, name, description, context_data, created_at, updated_at FROM context_snapshots WHERE session_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (session_id, limit, offset)
        else:
            query = "SELECT id, session_id, name, description, context_data, created_at, updated_at FROM context_snapshots ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (limit, offset)

        snapshots = []
        async with self._connection.execute(query, params) as cursor:
            async for row in cursor:
                context_data = {}
                if row[4]:
                    try:
                        context_data = json.loads(row[4])
                    except (json.JSONDecodeError, TypeError):
                        pass

                snapshots.append(
                    ContextSnapshot(
                        id=row[0],
                        session_id=row[1],
                        name=row[2],
                        description=row[3],
                        context_data=context_data,
                        created_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                        updated_at=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6],
                    )
                )

        return snapshots

    # Task progress operations
    async def create_task_progress(
        self, request: TaskProgressCreateRequest
    ) -> TaskProgress:
        """Create a new task progress entry."""
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()

        await self._connection.execute(
            """
            INSERT INTO task_progress (id, session_id, task_name, stage, status, progress_percentage, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                request.session_id,
                request.task_name,
                request.stage,
                request.status,
                request.progress_percentage,
                request.notes,
                now,
                now,
            ),
        )

        return TaskProgress(
            id=task_id,
            session_id=request.session_id,
            task_name=request.task_name,
            stage=request.stage,
            status=request.status,
            progress_percentage=request.progress_percentage,
            notes=request.notes,
            created_at=now,
            updated_at=now,
        )

    async def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get a task progress entry by ID."""
        async with self._connection.execute(
            "SELECT id, session_id, task_name, stage, status, progress_percentage, notes, created_at, updated_at FROM task_progress WHERE id = ?",
            (task_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None

            return TaskProgress(
                id=row[0],
                session_id=row[1],
                task_name=row[2],
                stage=row[3],
                status=row[4],
                progress_percentage=row[5],
                notes=row[6],
                created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
                updated_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
            )

    async def update_task_progress(
        self, task_id: str, request: TaskProgressUpdateRequest
    ) -> TaskProgress:
        """Update a task progress entry."""
        updates = []
        params: list[Any] = []

        if request.stage is not None:
            updates.append("stage = ?")
            params.append(request.stage)
        if request.status is not None:
            updates.append("status = ?")
            params.append(request.status)
        if request.progress_percentage is not None:
            updates.append("progress_percentage = ?")
            params.append(request.progress_percentage)
        if request.notes is not None:
            updates.append("notes = ?")
            params.append(request.notes)

        if not updates:
            task = await self.get_task_progress(task_id)
            if not task:
                raise ValueError(f"Task progress {task_id} not found")
            return task

        updates.append("updated_at = ?")
        params.append(datetime.utcnow())
        params.append(task_id)

        query = f"UPDATE task_progress SET {', '.join(updates)} WHERE id = ?"
        await self._connection.execute(query, params)

        task = await self.get_task_progress(task_id)
        if not task:
            raise ValueError(f"Task progress {task_id} not found")
        return task

    async def list_task_progress(
        self,
        session_id: Optional[str] = None,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskProgress]:
        """List task progress entries."""
        conditions = []
        params: list[Any] = []

        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if task_name:
            conditions.append("task_name = ?")
            params.append(task_name)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT id, session_id, task_name, stage, status, progress_percentage, notes, created_at, updated_at
            FROM task_progress
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        tasks = []
        async with self._connection.execute(query, params) as cursor:
            async for row in cursor:
                tasks.append(
                    TaskProgress(
                        id=row[0],
                        session_id=row[1],
                        task_name=row[2],
                        stage=row[3],
                        status=row[4],
                        progress_percentage=row[5],
                        notes=row[6],
                        created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
                        updated_at=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
                    )
                )

        return tasks

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        stats: dict[str, Any] = {}

        # Get table counts
        tables = ["sessions", "memory_entries", "relationships", "context_snapshots", "task_progress"]
        for table in tables:
            async with self._connection.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                row = await cursor.fetchone()
                stats[f"{table}_count"] = row[0] if row else 0

        # Get database size
        async with self._connection.execute("PRAGMA page_count") as cursor:
            page_count_row = await cursor.fetchone()
            page_count = page_count_row[0] if page_count_row else 0

        async with self._connection.execute("PRAGMA page_size") as cursor:
            page_size_row = await cursor.fetchone()
            page_size = page_size_row[0] if page_size_row else 0

        stats["database_size_bytes"] = page_count * page_size

        # Get top accessed entries
        top_accessed = []
        async with self._connection.execute(
            """
            SELECT title, access_count, category, priority
            FROM memory_entries
            ORDER BY access_count DESC
            LIMIT 5
            """
        ) as cursor:
            async for row in cursor:
                top_accessed.append({
                    "title": row[0],
                    "access_count": row[1],
                    "category": row[2],
                    "priority": row[3],
                })

        stats["top_accessed_entries"] = top_accessed

        return stats

