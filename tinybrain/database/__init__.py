"""CogDB database backend for TinyBrain (outer layer).

Provides a high-level Database class that uses CogDB as the storage engine.
This layer accepts full model objects (Session, Memory, etc.) rather than
CreateRequest objects used by the inner DatabaseBackend layer.

Also re-exports inner-layer components for convenience:
  from tinybrain.database import Database, CogDBBackend, DatabaseBackend
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from cog.torque import Graph
from loguru import logger

from tinybrain.models import Memory, Notification, Relationship, Session

TOKEN_RE = re.compile(r"[a-z0-9_./:-]+")

# Re-export inner layer components so `from tinybrain.database import CogDBBackend` works
# when running from the project root (where outer tinybrain/ shadows inner tinybrain/tinybrain/).
try:
    from tinybrain.tinybrain.database.base import Database as _InnerDatabase
    from tinybrain.tinybrain.database.base import DatabaseBackend
    from tinybrain.tinybrain.database.cogdb_backend import CogDBBackend
except ImportError:
    try:
        from tinybrain.database.base import DatabaseBackend
        from tinybrain.database.cogdb_backend import CogDBBackend
        _InnerDatabase = None
    except ImportError:
        DatabaseBackend = None  # type: ignore[assignment, misc]
        CogDBBackend = None  # type: ignore[assignment, misc]
        _InnerDatabase = None


def _json_serial(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


class Database:
    """CogDB-backed database for TinyBrain."""

    SESSION_PREFIX = "session:"
    MEMORY_PREFIX = "memory:"
    REL_PREFIX = "rel:"
    TASK_PREFIX = "task:"
    SNAPSHOT_PREFIX = "snapshot:"
    NOTIF_PREFIX = "notif:"

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._graph: Optional[Graph] = None

    async def connect(self) -> None:
        def _init() -> Graph:
            return Graph(
                "tinybrain",
                cog_home=self.db_path.stem,
                cog_path_prefix=str(self.db_path.parent),
            )

        self._graph = await asyncio.to_thread(_init)
        logger.info(f"Connected to CogDB: {self.db_path.parent}")

    async def initialize(self) -> None:
        if not self._graph:
            await self.connect()
        logger.info("CogDB initialized")

    async def close(self) -> None:
        if self._graph:
            try:
                await asyncio.to_thread(self._graph.sync)
            except Exception:
                pass
            self._graph = None
            logger.info("CogDB connection closed")

    # ── Private helpers ──────────────────────────────────────────────

    def _put_entity(
        self, entity_id: str, entity_type: str, data: dict, index_fields: tuple[str, ...]
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
        self, entity_id: str, entity_type: str, data: dict, index_fields: tuple[str, ...]
    ) -> None:
        self._graph.delete(entity_id, "_type", entity_type)
        self._graph.delete(entity_id, "_data", json.dumps(data, default=_json_serial))
        for field in index_fields:
            val = data.get(field)
            if val is not None:
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, default=_json_serial)
                try:
                    self._graph.delete(entity_id, field, str(val))
                except Exception:
                    pass

    def _list_ids_by_type(self, entity_type: str) -> list[str]:
        result = self._graph.v().has("_type", entity_type).all()
        if not result or not result.get("result"):
            return []
        return [item["id"] for item in result["result"]]

    def _list_ids_by_field(self, field: str, value: str, prefix: str) -> list[str]:
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

    def _delete_relationship_data(self, rel_entity_id: str, rel_data: dict) -> None:
        self._delete_entity(
            rel_entity_id,
            "relationship",
            rel_data,
            ("source_entry_id", "target_entry_id", "relationship_type"),
        )
        src = rel_data.get("source_entry_id")
        tgt = rel_data.get("target_entry_id")
        rel_type = rel_data.get("relationship_type")
        if src and tgt and rel_type:
            try:
                self._graph.delete(
                    f"{self.MEMORY_PREFIX}{src}",
                    rel_type,
                    f"{self.MEMORY_PREFIX}{tgt}",
                )
            except Exception:
                pass

    def _delete_relationships_for_memory(self, memory_id: str) -> int:
        src_ids = self._list_ids_by_field("source_entry_id", memory_id, self.REL_PREFIX)
        tgt_ids = self._list_ids_by_field("target_entry_id", memory_id, self.REL_PREFIX)
        deleted = 0
        for rid in set(src_ids + tgt_ids):
            rel_data = self._get_entity_data(rid)
            if rel_data:
                self._delete_relationship_data(rid, rel_data)
                deleted += 1
        return deleted

    def _delete_notifications_for_memory(self, memory_id: str) -> int:
        notif_ids = self._list_ids_by_type("notification")
        deleted = 0
        for nid in notif_ids:
            notif_data = self._get_entity_data(nid)
            metadata = notif_data.get("metadata") if notif_data else None
            if isinstance(metadata, dict) and metadata.get("memory_id") == memory_id:
                self._delete_entity(
                    nid,
                    "notification",
                    notif_data,
                    ("session_id", "notification_type", "read"),
                )
                deleted += 1
        return deleted

    @staticmethod
    def _query_matches(query: str, *fields: str) -> bool:
        query_lower = query.lower()
        haystack = " ".join(fields).lower()
        if query_lower in haystack:
            return True

        query_tokens = TOKEN_RE.findall(query_lower)
        if not query_tokens:
            return True
        haystack_tokens = set(TOKEN_RE.findall(haystack))
        return all(token in haystack_tokens for token in query_tokens)

    # ── Session operations ───────────────────────────────────────────

    async def create_session(self, session: Session) -> Session:
        entity_id = f"{self.SESSION_PREFIX}{session.id}"
        data = json.loads(session.model_dump_json())

        await asyncio.to_thread(
            self._put_entity, entity_id, "session", data, ("status", "task_type")
        )
        logger.info(f"Created session: {session.id}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        entity_id = f"{self.SESSION_PREFIX}{session_id}"
        data = await asyncio.to_thread(self._get_entity_data, entity_id)
        if not data:
            return None
        return Session(**data)

    # ── Memory operations ────────────────────────────────────────────

    async def create_memory(self, memory: Memory) -> Memory:
        entity_id = f"{self.MEMORY_PREFIX}{memory.id}"
        data = json.loads(memory.model_dump_json())

        await asyncio.to_thread(
            self._put_entity,
            entity_id,
            "memory",
            data,
            ("session_id", "category", "priority", "content_type"),
        )
        logger.info(f"Created memory: {memory.id}")
        return memory

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        entity_id = f"{self.MEMORY_PREFIX}{memory_id}"
        data = await asyncio.to_thread(self._get_entity_data, entity_id)
        if not data:
            return None
        return Memory(**data)

    async def search_memories(
        self,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        min_priority: Optional[int] = None,
        limit: int = 20,
    ) -> list[Memory]:
        def _search() -> list[dict]:
            if session_id:
                ids = self._list_ids_by_field("session_id", session_id, self.MEMORY_PREFIX)
            elif category:
                ids = self._list_ids_by_field("category", category, self.MEMORY_PREFIX)
            else:
                ids = self._list_ids_by_type("memory")
            return self._fetch_entities(ids)

        all_data = await asyncio.to_thread(_search)
        query_lower = query.lower() if query else None

        memories = []
        for d in all_data:
            if session_id and d.get("session_id") != session_id:
                continue
            if category and d.get("category") != category:
                continue
            if min_priority is not None and d.get("priority", 0) < min_priority:
                continue
            if query_lower:
                title = (d.get("title") or "").lower()
                content = (d.get("content") or "").lower()
                tags_str = " ".join(d.get("tags", []) if isinstance(d.get("tags"), list) else []).lower()
                if not self._query_matches(query_lower, title, content, tags_str):
                    continue
            memories.append(Memory(**d))

        memories.sort(key=lambda m: m.created_at, reverse=True)
        return memories[:limit]

    async def update_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        entity_id = f"{self.MEMORY_PREFIX}{memory_id}"

        def _update() -> bool:
            old_data = self._get_entity_data(entity_id)
            if not old_data:
                return False
            new_data = dict(old_data)
            for key, value in updates.items():
                new_data[key] = value
            new_data["updated_at"] = datetime.utcnow().isoformat()

            self._delete_entity(
                entity_id, "memory", old_data, ("session_id", "category", "priority", "content_type")
            )
            self._put_entity(
                entity_id, "memory", new_data, ("session_id", "category", "priority", "content_type")
            )
            return True

        result = await asyncio.to_thread(_update)
        if result:
            logger.info(f"Updated memory: {memory_id}")
        return result

    async def delete_memory(self, memory_id: str) -> bool:
        entity_id = f"{self.MEMORY_PREFIX}{memory_id}"

        def _delete() -> bool:
            data = self._get_entity_data(entity_id)
            if not data:
                return False
            self._delete_relationships_for_memory(memory_id)
            self._delete_notifications_for_memory(memory_id)
            self._delete_entity(
                entity_id, "memory", data, ("session_id", "category", "priority", "content_type")
            )
            return True

        result = await asyncio.to_thread(_delete)
        if result:
            logger.info(f"Deleted memory: {memory_id}")
        return result

    # ── Relationship operations ──────────────────────────────────────

    async def create_relationship(self, relationship: Relationship) -> Relationship:
        entity_id = f"{self.REL_PREFIX}{relationship.id}"
        data = json.loads(relationship.model_dump_json())

        def _create() -> None:
            self._put_entity(
                entity_id,
                "relationship",
                data,
                ("source_entry_id", "target_entry_id", "relationship_type"),
            )
            self._graph.put(
                f"{self.MEMORY_PREFIX}{relationship.source_entry_id}",
                relationship.relationship_type.value,
                f"{self.MEMORY_PREFIX}{relationship.target_entry_id}",
            )

        await asyncio.to_thread(_create)
        logger.info(f"Created relationship: {relationship.id}")
        return relationship

    async def get_related_memories(
        self,
        memory_id: str,
        relationship_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[Memory]:
        def _get_related() -> list[dict]:
            src_ids = self._list_ids_by_field(
                "source_entry_id", memory_id, self.REL_PREFIX
            )
            tgt_ids = self._list_ids_by_field(
                "target_entry_id", memory_id, self.REL_PREFIX
            )

            related_memory_ids: set[str] = set()
            for rid in set(src_ids + tgt_ids):
                rel_data = self._get_entity_data(rid)
                if not rel_data:
                    continue
                rtype = rel_data.get("relationship_type", "")
                if relationship_type and rtype != relationship_type:
                    continue
                src = rel_data.get("source_entry_id", "")
                tgt = rel_data.get("target_entry_id", "")
                other = tgt if src == memory_id else src
                if other:
                    related_memory_ids.add(other)

            results = []
            for mid in related_memory_ids:
                d = self._get_entity_data(f"{self.MEMORY_PREFIX}{mid}")
                if d:
                    results.append(d)
            return results

        all_data = await asyncio.to_thread(_get_related)
        return [Memory(**d) for d in all_data[:limit]]

    async def list_relationships(
        self,
        source_memory_id: Optional[str] = None,
        target_memory_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 1000,
    ) -> list[Relationship]:
        """List relationships with optional endpoint/type filters."""

        def _list() -> list[dict]:
            if source_memory_id:
                ids = self._list_ids_by_field(
                    "source_entry_id", source_memory_id, self.REL_PREFIX
                )
            elif target_memory_id:
                ids = self._list_ids_by_field(
                    "target_entry_id", target_memory_id, self.REL_PREFIX
                )
            elif relationship_type:
                ids = self._list_ids_by_field(
                    "relationship_type", relationship_type, self.REL_PREFIX
                )
            else:
                ids = self._list_ids_by_type("relationship")
            return self._fetch_entities(ids)

        all_data = await asyncio.to_thread(_list)
        relationships = []
        for d in all_data:
            if source_memory_id and d.get("source_entry_id") != source_memory_id:
                continue
            if target_memory_id and d.get("target_entry_id") != target_memory_id:
                continue
            if relationship_type and d.get("relationship_type") != relationship_type:
                continue
            relationships.append(Relationship(**d))
        relationships.sort(key=lambda r: r.created_at, reverse=True)
        return relationships[:limit]

    async def delete_relationship(self, relationship_id: str) -> bool:
        entity_id = f"{self.REL_PREFIX}{relationship_id}"

        def _delete() -> bool:
            data = self._get_entity_data(entity_id)
            if not data:
                return False
            self._delete_relationship_data(entity_id, data)
            return True

        return await asyncio.to_thread(_delete)

    async def cleanup_orphan_relationships(self) -> dict[str, int]:
        def _cleanup() -> dict[str, int]:
            rel_ids = self._list_ids_by_type("relationship")
            deleted = 0
            checked = 0
            for rid in rel_ids:
                checked += 1
                rel_data = self._get_entity_data(rid)
                if not rel_data:
                    continue
                src = rel_data.get("source_entry_id")
                tgt = rel_data.get("target_entry_id")
                if not src or not tgt:
                    self._delete_relationship_data(rid, rel_data)
                    deleted += 1
                    continue
                if (
                    self._get_entity_data(f"{self.MEMORY_PREFIX}{src}") is None
                    or self._get_entity_data(f"{self.MEMORY_PREFIX}{tgt}") is None
                ):
                    self._delete_relationship_data(rid, rel_data)
                    deleted += 1
            return {"checked": checked, "deleted": deleted}

        return await asyncio.to_thread(_cleanup)

    async def cleanup_memories_by_age(
        self,
        max_age_days: int,
        session_id: Optional[str] = None,
        dry_run: bool = True,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Find or delete memories older than the requested age."""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        candidates = [
            memory
            for memory in await self.search_memories(session_id=session_id, limit=limit)
            if (created_at := _parse_datetime(memory.created_at)) is not None
            and created_at < cutoff
        ]
        return await self._cleanup_memory_candidates(candidates, dry_run=dry_run)

    async def cleanup_low_priority_memories(
        self,
        max_priority: int = 2,
        min_age_days: int = 0,
        session_id: Optional[str] = None,
        dry_run: bool = True,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Find or delete low-priority memories, optionally after an age threshold."""
        cutoff = datetime.utcnow() - timedelta(days=min_age_days)
        candidates = []
        for memory in await self.search_memories(session_id=session_id, limit=limit):
            created_at = _parse_datetime(memory.created_at)
            if memory.priority <= max_priority and created_at is not None and created_at < cutoff:
                candidates.append(memory)
        return await self._cleanup_memory_candidates(candidates, dry_run=dry_run)

    async def cleanup_unused_memories(
        self,
        max_access_count: int = 0,
        min_age_days: int = 30,
        session_id: Optional[str] = None,
        dry_run: bool = True,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Find or delete old memories that have not been accessed often."""
        cutoff = datetime.utcnow() - timedelta(days=min_age_days)
        candidates = []
        for memory in await self.search_memories(session_id=session_id, limit=limit):
            accessed_at = _parse_datetime(memory.accessed_at)
            if (
                memory.access_count <= max_access_count
                and accessed_at is not None
                and accessed_at < cutoff
            ):
                candidates.append(memory)
        return await self._cleanup_memory_candidates(candidates, dry_run=dry_run)

    async def _cleanup_memory_candidates(
        self,
        candidates: list[Memory],
        dry_run: bool,
    ) -> dict[str, Any]:
        deleted = []
        if not dry_run:
            for memory in candidates:
                if await self.delete_memory(memory.id):
                    deleted.append(memory.id)
        return {
            "dry_run": dry_run,
            "candidate_count": len(candidates),
            "deleted_count": len(deleted),
            "deleted": deleted,
            "candidates": [
                {
                    "id": memory.id,
                    "session_id": memory.session_id,
                    "title": memory.title,
                    "category": memory.category.value,
                    "priority": memory.priority,
                    "confidence": memory.confidence,
                    "created_at": memory.created_at.isoformat(),
                    "accessed_at": memory.accessed_at.isoformat(),
                    "access_count": memory.access_count,
                }
                for memory in candidates
            ],
        }

    # ── Session list/delete ─────────────────────────────────────────

    async def list_sessions(
        self,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> list[Session]:
        def _list() -> list[dict]:
            if status:
                ids = self._list_ids_by_field("status", status, self.SESSION_PREFIX)
            elif task_type:
                ids = self._list_ids_by_field("task_type", task_type, self.SESSION_PREFIX)
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
        return sessions[:limit]

    async def delete_session(self, session_id: str) -> bool:
        entity_id = f"{self.SESSION_PREFIX}{session_id}"

        def _delete() -> bool:
            data = self._get_entity_data(entity_id)
            if not data:
                return False
            mem_ids = self._list_ids_by_field("session_id", session_id, self.MEMORY_PREFIX)
            for mid in mem_ids:
                mem_data = self._get_entity_data(mid)
                if mem_data:
                    plain_id = mem_data.get("id", mid.removeprefix(self.MEMORY_PREFIX))
                    self._delete_relationships_for_memory(plain_id)
                    self._delete_notifications_for_memory(plain_id)
                    self._delete_entity(
                        mid, "memory", mem_data, ("session_id", "category", "priority", "content_type")
                    )
            notif_ids = self._list_ids_by_field("session_id", session_id, self.NOTIF_PREFIX)
            for nid in notif_ids:
                notif_data = self._get_entity_data(nid)
                if notif_data:
                    self._delete_entity(
                        nid,
                        "notification",
                        notif_data,
                        ("session_id", "notification_type", "read"),
                    )
            self._delete_entity(entity_id, "session", data, ("status", "task_type"))
            return True

        result = await asyncio.to_thread(_delete)
        if result:
            logger.info(f"Deleted session: {session_id}")
        return result

    # ── Notification operations ──────────────────────────────────────

    async def create_notification(self, notification: Notification) -> Notification:
        entity_id = f"{self.NOTIF_PREFIX}{notification.id}"
        data = json.loads(notification.model_dump_json())

        await asyncio.to_thread(
            self._put_entity,
            entity_id,
            "notification",
            data,
            ("session_id", "notification_type", "read"),
        )
        return notification

    async def get_notifications(
        self,
        session_id: Optional[str] = None,
        read: Optional[bool] = None,
        limit: int = 20,
    ) -> list[Notification]:
        def _list() -> list[dict]:
            if session_id:
                ids = self._list_ids_by_field("session_id", session_id, self.NOTIF_PREFIX)
            else:
                ids = self._list_ids_by_type("notification")
            return self._fetch_entities(ids)

        all_data = await asyncio.to_thread(_list)

        notifications = []
        for d in all_data:
            if session_id and d.get("session_id") != session_id:
                continue
            if read is not None and d.get("read") != read:
                continue
            notifications.append(Notification(**d))

        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications[:limit]

    async def mark_notification_read(self, notification_id: str, read: bool = True) -> bool:
        """Mark a notification read/unread."""
        entity_id = f"{self.NOTIF_PREFIX}{notification_id}"

        def _update() -> bool:
            old_data = self._get_entity_data(entity_id)
            if not old_data:
                return False
            new_data = dict(old_data)
            new_data["read"] = read
            self._delete_entity(
                entity_id,
                "notification",
                old_data,
                ("session_id", "notification_type", "read"),
            )
            self._put_entity(
                entity_id,
                "notification",
                new_data,
                ("session_id", "notification_type", "read"),
            )
            return True

        return await asyncio.to_thread(_update)
