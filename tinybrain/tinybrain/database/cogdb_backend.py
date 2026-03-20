"""CogDB graph database backend implementation.

Stores all entities as graph vertices with prefixed IDs for type discrimination.
Each entity gets:
  - A _type triple for type-based listing
  - A _data triple containing the full JSON serialization (fast reads)
  - Individual property triples for queryable fields (filtering)

Relationships between memories are also stored as direct graph edges for traversal.
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from cog.torque import Graph

from .base import DatabaseBackend
from ..models.memory import Memory, MemoryCreateRequest, MemoryUpdateRequest
from ..models.session import Session, SessionCreateRequest, SessionUpdateRequest
from ..models.relationship import (
    Relationship,
    RelationshipCreateRequest,
    RelationshipType,
)
from ..models.context_snapshot import (
    ContextSnapshot,
    ContextSnapshotCreateRequest,
)
from ..models.task_progress import (
    TaskProgress,
    TaskProgressCreateRequest,
    TaskProgressUpdateRequest,
)


def _json_serial(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class CogDBBackend(DatabaseBackend):
    """CogDB graph database implementation of the database backend."""

    SESSION_PREFIX = "session:"
    MEMORY_PREFIX = "memory:"
    REL_PREFIX = "rel:"
    TASK_PREFIX = "task:"
    SNAPSHOT_PREFIX = "snapshot:"

    SESSION_INDEXES = ("status", "task_type")
    MEMORY_INDEXES = ("session_id", "category", "priority", "content_type")
    REL_INDEXES = ("source_id", "target_id", "relationship_type")
    TASK_INDEXES = ("session_id", "status", "task_name")
    SNAPSHOT_INDEXES = ("session_id",)

    def __init__(
        self,
        cog_home: str = "tinybrain",
        cog_path_prefix: Optional[str] = None,
    ):
        self.cog_home = cog_home
        self.cog_path_prefix = cog_path_prefix or str(Path.home() / ".tinybrain")
        self._graph: Optional[Graph] = None

    async def initialize(self) -> None:
        def _init() -> Graph:
            Path(self.cog_path_prefix).mkdir(parents=True, exist_ok=True)
            return Graph(
                "tinybrain",
                cog_home=self.cog_home,
                cog_path_prefix=self.cog_path_prefix,
            )

        self._graph = await asyncio.to_thread(_init)

    async def close(self) -> None:
        if self._graph:
            try:
                await asyncio.to_thread(self._graph.sync)
            except Exception:
                pass
        self._graph = None

    async def health_check(self) -> bool:
        if not self._graph:
            return False
        try:
            await asyncio.to_thread(self._graph.scan, 1)
            return True
        except Exception:
            return False

    # ── Private helpers ──────────────────────────────────────────────

    def _put_entity(
        self,
        entity_id: str,
        entity_type: str,
        data: dict,
        index_fields: tuple[str, ...],
    ) -> None:
        triples = [
            (entity_id, "_type", entity_type),
            (entity_id, "_data", json.dumps(data, default=_json_serial)),
        ]
        for field in index_fields:
            val = data.get(field)
            if val is not None:
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, default=_json_serial)
                triples.append((entity_id, field, str(val)))
        self._graph.put_batch(triples)

    def _get_entity_data(self, entity_id: str) -> Optional[dict]:
        result = self._graph.v(entity_id).out("_data").all()
        if not result or not result.get("result"):
            return None
        return json.loads(result["result"][0]["id"])

    def _delete_entity(
        self,
        entity_id: str,
        entity_type: str,
        data: dict,
        index_fields: tuple[str, ...],
    ) -> None:
        self._graph.delete(entity_id, "_type", entity_type)
        self._graph.delete(
            entity_id, "_data", json.dumps(data, default=_json_serial)
        )
        for field in index_fields:
            val = data.get(field)
            if val is not None:
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, default=_json_serial)
                try:
                    self._graph.delete(entity_id, field, str(val))
                except Exception:
                    pass

    def _update_entity(
        self,
        entity_id: str,
        entity_type: str,
        old_data: dict,
        new_data: dict,
        index_fields: tuple[str, ...],
    ) -> None:
        self._delete_entity(entity_id, entity_type, old_data, index_fields)
        self._put_entity(entity_id, entity_type, new_data, index_fields)

    def _list_ids_by_type(self, entity_type: str) -> list[str]:
        result = self._graph.v().has("_type", entity_type).all()
        if not result or not result.get("result"):
            return []
        return [item["id"] for item in result["result"]]

    def _list_ids_by_field(
        self, field: str, value: str, prefix: str
    ) -> list[str]:
        result = (
            self._graph.v()
            .has(field, value)
            .filter(func=lambda x, p=prefix: x.startswith(p))
            .all()
        )
        if not result or not result.get("result"):
            return []
        return [item["id"] for item in result["result"]]

    def _fetch_entities(self, entity_ids: list[str]) -> list[dict]:
        entities = []
        for eid in entity_ids:
            data = self._get_entity_data(eid)
            if data:
                entities.append(data)
        return entities

    @staticmethod
    def _parse_dt(val: Any) -> datetime:
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return datetime.utcnow()

    # ── Session operations ───────────────────────────────────────────

    async def create_session(self, request: SessionCreateRequest) -> Session:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()

        session = Session(
            id=session_id,
            name=request.name,
            task_type=request.task_type,
            status="active",
            description=request.description,
            metadata=request.metadata or {},
            created_at=now,
            updated_at=now,
        )
        data = json.loads(session.model_dump_json())
        entity_id = f"{self.SESSION_PREFIX}{session_id}"

        await asyncio.to_thread(
            self._put_entity, entity_id, "session", data, self.SESSION_INDEXES
        )
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        entity_id = f"{self.SESSION_PREFIX}{session_id}"
        data = await asyncio.to_thread(self._get_entity_data, entity_id)
        if not data:
            return None
        return Session(**data)

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> list[Session]:
        def _list() -> list[dict]:
            if status:
                ids = self._list_ids_by_field(
                    "status", status, self.SESSION_PREFIX
                )
            else:
                ids = self._list_ids_by_type("session")
            return self._fetch_entities(ids)

        all_data = await asyncio.to_thread(_list)

        sessions = []
        for d in all_data:
            if task_type and d.get("task_type") != task_type:
                continue
            if status and d.get("status") != status:
                continue
            sessions.append(Session(**d))

        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions[offset : offset + limit]

    async def update_session(
        self, session_id: str, request: SessionUpdateRequest
    ) -> Session:
        entity_id = f"{self.SESSION_PREFIX}{session_id}"

        def _update() -> Optional[dict]:
            old_data = self._get_entity_data(entity_id)
            if not old_data:
                return None

            new_data = dict(old_data)
            if request.name is not None:
                new_data["name"] = request.name
            if request.status is not None:
                new_data["status"] = request.status
            if request.description is not None:
                new_data["description"] = request.description
            if request.metadata is not None:
                new_data["metadata"] = request.metadata
            new_data["updated_at"] = datetime.utcnow().isoformat()

            self._update_entity(
                entity_id, "session", old_data, new_data, self.SESSION_INDEXES
            )
            return new_data

        data = await asyncio.to_thread(_update)
        if not data:
            raise ValueError(f"Session {session_id} not found")
        return Session(**data)

    async def delete_session(self, session_id: str) -> bool:
        entity_id = f"{self.SESSION_PREFIX}{session_id}"

        def _delete() -> bool:
            data = self._get_entity_data(entity_id)
            if not data:
                return False

            # Cascade: delete memories (and their relationships), tasks, snapshots
            self._cascade_delete_session(session_id)
            self._delete_entity(
                entity_id, "session", data, self.SESSION_INDEXES
            )
            return True

        return await asyncio.to_thread(_delete)

    def _cascade_delete_session(self, session_id: str) -> None:
        mem_ids = self._list_ids_by_field(
            "session_id", session_id, self.MEMORY_PREFIX
        )
        for mid in mem_ids:
            mem_data = self._get_entity_data(mid)
            if mem_data:
                plain_id = mem_data.get("id", mid.removeprefix(self.MEMORY_PREFIX))
                self._cascade_delete_memory_relationships(plain_id)
                self._delete_entity(mid, "memory", mem_data, self.MEMORY_INDEXES)

        task_ids = self._list_ids_by_field(
            "session_id", session_id, self.TASK_PREFIX
        )
        for tid in task_ids:
            task_data = self._get_entity_data(tid)
            if task_data:
                self._delete_entity(tid, "task", task_data, self.TASK_INDEXES)

        snap_ids = self._list_ids_by_field(
            "session_id", session_id, self.SNAPSHOT_PREFIX
        )
        for sid in snap_ids:
            snap_data = self._get_entity_data(sid)
            if snap_data:
                self._delete_entity(
                    sid, "snapshot", snap_data, self.SNAPSHOT_INDEXES
                )

    def _cascade_delete_memory_relationships(self, memory_id: str) -> None:
        rel_ids_src = self._list_ids_by_field(
            "source_id", memory_id, self.REL_PREFIX
        )
        rel_ids_tgt = self._list_ids_by_field(
            "target_id", memory_id, self.REL_PREFIX
        )
        for rid in set(rel_ids_src + rel_ids_tgt):
            rel_data = self._get_entity_data(rid)
            if rel_data:
                self._delete_relationship_triples(rid, rel_data)

    def _delete_relationship_triples(self, entity_id: str, data: dict) -> None:
        self._delete_entity(entity_id, "relationship", data, self.REL_INDEXES)
        src = data.get("source_id", "")
        tgt = data.get("target_id", "")
        rtype = data.get("type") or data.get("relationship_type", "")
        if src and tgt and rtype:
            try:
                self._graph.delete(
                    f"{self.MEMORY_PREFIX}{src}", rtype, f"{self.MEMORY_PREFIX}{tgt}"
                )
            except Exception:
                pass

    # ── Memory operations ────────────────────────────────────────────

    async def create_memory(self, request: MemoryCreateRequest) -> Memory:
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow()

        memory = Memory(
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
        data = json.loads(memory.model_dump_json())
        entity_id = f"{self.MEMORY_PREFIX}{memory_id}"

        await asyncio.to_thread(
            self._put_entity, entity_id, "memory", data, self.MEMORY_INDEXES
        )
        return memory

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        entity_id = f"{self.MEMORY_PREFIX}{memory_id}"

        def _get() -> Optional[dict]:
            data = self._get_entity_data(entity_id)
            if not data:
                return None
            data["access_count"] = data.get("access_count", 0) + 1
            data["accessed_at"] = datetime.utcnow().isoformat()
            old_data = self._get_entity_data(entity_id)
            if old_data:
                self._update_entity(
                    entity_id, "memory", old_data, data, self.MEMORY_INDEXES
                )
            return data

        data = await asyncio.to_thread(_get)
        if not data:
            return None
        return Memory(**data)

    async def update_memory(
        self, memory_id: str, request: MemoryUpdateRequest
    ) -> Memory:
        entity_id = f"{self.MEMORY_PREFIX}{memory_id}"

        def _update() -> Optional[dict]:
            old_data = self._get_entity_data(entity_id)
            if not old_data:
                return None

            new_data = dict(old_data)
            if request.title is not None:
                new_data["title"] = request.title
            if request.content is not None:
                new_data["content"] = request.content
            if request.category is not None:
                new_data["category"] = request.category
            if request.priority is not None:
                new_data["priority"] = request.priority
            if request.confidence is not None:
                new_data["confidence"] = request.confidence
            if request.tags is not None:
                new_data["tags"] = request.tags
            if request.source is not None:
                new_data["source"] = request.source
            if request.content_type is not None:
                new_data["content_type"] = request.content_type
            new_data["updated_at"] = datetime.utcnow().isoformat()

            self._update_entity(
                entity_id, "memory", old_data, new_data, self.MEMORY_INDEXES
            )
            return new_data

        data = await asyncio.to_thread(_update)
        if not data:
            raise ValueError(f"Memory {memory_id} not found")
        return Memory(**data)

    async def delete_memory(self, memory_id: str) -> bool:
        entity_id = f"{self.MEMORY_PREFIX}{memory_id}"

        def _delete() -> bool:
            data = self._get_entity_data(entity_id)
            if not data:
                return False
            self._cascade_delete_memory_relationships(memory_id)
            self._delete_entity(entity_id, "memory", data, self.MEMORY_INDEXES)
            return True

        return await asyncio.to_thread(_delete)

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
        def _search() -> list[dict]:
            if session_id:
                ids = self._list_ids_by_field(
                    "session_id", session_id, self.MEMORY_PREFIX
                )
            elif category:
                ids = self._list_ids_by_field(
                    "category", category, self.MEMORY_PREFIX
                )
            else:
                ids = self._list_ids_by_type("memory")
            return self._fetch_entities(ids)

        all_data = await asyncio.to_thread(_search)

        memories: list[Memory] = []
        query_lower = query.lower() if query else None

        for d in all_data:
            if session_id and d.get("session_id") != session_id:
                continue
            if category and d.get("category") != category:
                continue
            if min_priority is not None and (d.get("priority", 0) < min_priority):
                continue
            if min_confidence is not None and (
                d.get("confidence", 0.0) < min_confidence
            ):
                continue
            if tags:
                mem_tags = d.get("tags", [])
                if isinstance(mem_tags, str):
                    try:
                        mem_tags = json.loads(mem_tags)
                    except (json.JSONDecodeError, TypeError):
                        mem_tags = []
                if not any(t in mem_tags for t in tags):
                    continue
            if query_lower:
                title = (d.get("title") or "").lower()
                content = (d.get("content") or "").lower()
                tag_str = " ".join(d.get("tags", []) if isinstance(d.get("tags"), list) else []).lower()
                if (
                    query_lower not in title
                    and query_lower not in content
                    and query_lower not in tag_str
                ):
                    continue

            memories.append(Memory(**d))

        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[offset : offset + limit]

    # ── Relationship operations ──────────────────────────────────────

    async def create_relationship(
        self, request: RelationshipCreateRequest
    ) -> Relationship:
        rel_id = str(uuid.uuid4())
        now = datetime.utcnow()

        relationship = Relationship(
            id=rel_id,
            source_id=request.source_id,
            target_id=request.target_id,
            type=request.type,
            strength=request.strength,
            description=request.description,
            created_at=now,
            updated_at=now,
        )
        data = json.loads(relationship.model_dump_json())
        data["relationship_type"] = data.pop("type", request.type.value)
        entity_id = f"{self.REL_PREFIX}{rel_id}"

        def _create() -> None:
            self._put_entity(
                entity_id, "relationship", data, self.REL_INDEXES
            )
            # Direct graph edge for traversal
            self._graph.put(
                f"{self.MEMORY_PREFIX}{request.source_id}",
                request.type.value,
                f"{self.MEMORY_PREFIX}{request.target_id}",
            )

        await asyncio.to_thread(_create)
        return relationship

    async def get_relationship(
        self, relationship_id: str
    ) -> Optional[Relationship]:
        entity_id = f"{self.REL_PREFIX}{relationship_id}"
        data = await asyncio.to_thread(self._get_entity_data, entity_id)
        if not data:
            return None
        if "relationship_type" in data and "type" not in data:
            data["type"] = data.pop("relationship_type")
        return Relationship(**data)

    async def get_related_memories(
        self,
        memory_id: str,
        relationship_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[Memory]:
        def _get_related() -> list[dict]:
            vertex = f"{self.MEMORY_PREFIX}{memory_id}"

            # Find relationship entities where this memory is source or target
            src_ids = self._list_ids_by_field(
                "source_id", memory_id, self.REL_PREFIX
            )
            tgt_ids = self._list_ids_by_field(
                "target_id", memory_id, self.REL_PREFIX
            )

            related_memory_ids: set[str] = set()
            for rid in set(src_ids + tgt_ids):
                rel_data = self._get_entity_data(rid)
                if not rel_data:
                    continue
                rtype = rel_data.get("relationship_type") or rel_data.get("type", "")
                if relationship_type and rtype != relationship_type:
                    continue
                src = rel_data.get("source_id", "")
                tgt = rel_data.get("target_id", "")
                other = tgt if src == memory_id else src
                if other:
                    related_memory_ids.add(other)

            results = []
            for mid in related_memory_ids:
                eid = f"{self.MEMORY_PREFIX}{mid}"
                d = self._get_entity_data(eid)
                if d:
                    results.append(d)
            return results

        all_data = await asyncio.to_thread(_get_related)
        memories = [Memory(**d) for d in all_data[:limit]]
        return memories

    async def delete_relationship(self, relationship_id: str) -> bool:
        entity_id = f"{self.REL_PREFIX}{relationship_id}"

        def _delete() -> bool:
            data = self._get_entity_data(entity_id)
            if not data:
                return False
            self._delete_relationship_triples(entity_id, data)
            return True

        return await asyncio.to_thread(_delete)

    # ── Context snapshot operations ──────────────────────────────────

    async def create_context_snapshot(
        self, request: ContextSnapshotCreateRequest
    ) -> ContextSnapshot:
        snap_id = str(uuid.uuid4())
        now = datetime.utcnow()

        snapshot = ContextSnapshot(
            id=snap_id,
            session_id=request.session_id,
            name=request.name,
            context_data=request.context_data,
            description=request.description,
            created_at=now,
            updated_at=now,
        )
        data = json.loads(snapshot.model_dump_json())
        entity_id = f"{self.SNAPSHOT_PREFIX}{snap_id}"

        await asyncio.to_thread(
            self._put_entity, entity_id, "snapshot", data, self.SNAPSHOT_INDEXES
        )
        return snapshot

    async def get_context_snapshot(
        self, snapshot_id: str
    ) -> Optional[ContextSnapshot]:
        entity_id = f"{self.SNAPSHOT_PREFIX}{snapshot_id}"
        data = await asyncio.to_thread(self._get_entity_data, entity_id)
        if not data:
            return None
        return ContextSnapshot(**data)

    async def list_context_snapshots(
        self,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContextSnapshot]:
        def _list() -> list[dict]:
            if session_id:
                ids = self._list_ids_by_field(
                    "session_id", session_id, self.SNAPSHOT_PREFIX
                )
            else:
                ids = self._list_ids_by_type("snapshot")
            return self._fetch_entities(ids)

        all_data = await asyncio.to_thread(_list)
        snapshots = [ContextSnapshot(**d) for d in all_data]
        snapshots.sort(key=lambda s: s.created_at, reverse=True)
        return snapshots[offset : offset + limit]

    # ── Task progress operations ─────────────────────────────────────

    async def create_task_progress(
        self, request: TaskProgressCreateRequest
    ) -> TaskProgress:
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()

        task = TaskProgress(
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
        data = json.loads(task.model_dump_json())
        entity_id = f"{self.TASK_PREFIX}{task_id}"

        await asyncio.to_thread(
            self._put_entity, entity_id, "task", data, self.TASK_INDEXES
        )
        return task

    async def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        entity_id = f"{self.TASK_PREFIX}{task_id}"
        data = await asyncio.to_thread(self._get_entity_data, entity_id)
        if not data:
            return None
        return TaskProgress(**data)

    async def update_task_progress(
        self, task_id: str, request: TaskProgressUpdateRequest
    ) -> TaskProgress:
        entity_id = f"{self.TASK_PREFIX}{task_id}"

        def _update() -> Optional[dict]:
            old_data = self._get_entity_data(entity_id)
            if not old_data:
                return None

            new_data = dict(old_data)
            if request.stage is not None:
                new_data["stage"] = request.stage
            if request.status is not None:
                new_data["status"] = request.status
            if request.progress_percentage is not None:
                new_data["progress_percentage"] = request.progress_percentage
            if request.notes is not None:
                new_data["notes"] = request.notes
            new_data["updated_at"] = datetime.utcnow().isoformat()

            self._update_entity(
                entity_id, "task", old_data, new_data, self.TASK_INDEXES
            )
            return new_data

        data = await asyncio.to_thread(_update)
        if not data:
            raise ValueError(f"Task progress {task_id} not found")
        return TaskProgress(**data)

    async def list_task_progress(
        self,
        session_id: Optional[str] = None,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskProgress]:
        def _list() -> list[dict]:
            if session_id:
                ids = self._list_ids_by_field(
                    "session_id", session_id, self.TASK_PREFIX
                )
            elif status:
                ids = self._list_ids_by_field(
                    "status", status, self.TASK_PREFIX
                )
            else:
                ids = self._list_ids_by_type("task")
            return self._fetch_entities(ids)

        all_data = await asyncio.to_thread(_list)

        tasks = []
        for d in all_data:
            if session_id and d.get("session_id") != session_id:
                continue
            if task_name and d.get("task_name") != task_name:
                continue
            if status and d.get("status") != status:
                continue
            tasks.append(TaskProgress(**d))

        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[offset : offset + limit]

    # ── Stats ────────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        def _stats() -> dict[str, Any]:
            stats: dict[str, Any] = {}
            for entity_type, label in [
                ("session", "sessions_count"),
                ("memory", "memory_entries_count"),
                ("relationship", "relationships_count"),
                ("snapshot", "context_snapshots_count"),
                ("task", "task_progress_count"),
            ]:
                ids = self._list_ids_by_type(entity_type)
                stats[label] = len(ids)

            # Top accessed memories
            mem_ids = self._list_ids_by_type("memory")
            all_mems = self._fetch_entities(mem_ids)
            all_mems.sort(
                key=lambda d: d.get("access_count", 0), reverse=True
            )
            stats["top_accessed_entries"] = [
                {
                    "title": m.get("title"),
                    "access_count": m.get("access_count", 0),
                    "category": m.get("category"),
                    "priority": m.get("priority"),
                }
                for m in all_mems[:5]
            ]

            if self._graph:
                try:
                    es = self._graph.embedding_stats()
                    stats["embedding_stats"] = es
                except Exception:
                    pass

            return stats

        return await asyncio.to_thread(_stats)
