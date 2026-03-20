"""Base database interface and abstraction."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pathlib import Path

from ..models.memory import Memory, MemoryCreateRequest, MemoryUpdateRequest
from ..models.session import Session, SessionCreateRequest, SessionUpdateRequest
from ..models.relationship import (
    Relationship,
    RelationshipCreateRequest,
    RelationshipUpdateRequest,
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


class DatabaseBackend(ABC):
    """Abstract base class for database backends."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the database backend."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Perform a health check on the database."""
        pass

    # Session operations
    @abstractmethod
    async def create_session(self, request: SessionCreateRequest) -> Session:
        """Create a new session."""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        pass

    @abstractmethod
    async def list_sessions(
        self, limit: int = 50, offset: int = 0, status: Optional[str] = None, task_type: Optional[str] = None
    ) -> list[Session]:
        """List sessions with optional filtering."""
        pass

    @abstractmethod
    async def update_session(self, session_id: str, request: SessionUpdateRequest) -> Session:
        """Update a session."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        pass

    # Memory operations
    @abstractmethod
    async def create_memory(self, request: MemoryCreateRequest) -> Memory:
        """Create a new memory entry."""
        pass

    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory entry by ID."""
        pass

    @abstractmethod
    async def update_memory(self, memory_id: str, request: MemoryUpdateRequest) -> Memory:
        """Update a memory entry."""
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        pass

    @abstractmethod
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
        pass

    # Relationship operations
    @abstractmethod
    async def create_relationship(self, request: RelationshipCreateRequest) -> Relationship:
        """Create a new relationship."""
        pass

    @abstractmethod
    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID."""
        pass

    @abstractmethod
    async def get_related_memories(
        self, memory_id: str, relationship_type: Optional[str] = None, limit: int = 10
    ) -> list[Memory]:
        """Get memories related to a specific memory."""
        pass

    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        pass

    # Context snapshot operations
    @abstractmethod
    async def create_context_snapshot(
        self, request: ContextSnapshotCreateRequest
    ) -> ContextSnapshot:
        """Create a new context snapshot."""
        pass

    @abstractmethod
    async def get_context_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Get a context snapshot by ID."""
        pass

    @abstractmethod
    async def list_context_snapshots(
        self, session_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[ContextSnapshot]:
        """List context snapshots."""
        pass

    # Task progress operations
    @abstractmethod
    async def create_task_progress(
        self, request: TaskProgressCreateRequest
    ) -> TaskProgress:
        """Create a new task progress entry."""
        pass

    @abstractmethod
    async def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get a task progress entry by ID."""
        pass

    @abstractmethod
    async def update_task_progress(
        self, task_id: str, request: TaskProgressUpdateRequest
    ) -> TaskProgress:
        """Update a task progress entry."""
        pass

    @abstractmethod
    async def list_task_progress(
        self,
        session_id: Optional[str] = None,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskProgress]:
        """List task progress entries."""
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        pass


class Database:
    """Database manager that wraps a backend implementation."""

    def __init__(self, backend: DatabaseBackend):
        """Initialize the database with a backend."""
        self.backend = backend

    async def initialize(self) -> None:
        """Initialize the database."""
        await self.backend.initialize()

    async def close(self) -> None:
        """Close the database connection."""
        await self.backend.close()

    async def health_check(self) -> bool:
        """Perform a health check."""
        return await self.backend.health_check()

    # Delegate all operations to the backend
    async def create_session(self, request: SessionCreateRequest) -> Session:
        """Create a new session."""
        return await self.backend.create_session(request)

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return await self.backend.get_session(session_id)

    async def list_sessions(
        self, limit: int = 50, offset: int = 0, status: Optional[str] = None, task_type: Optional[str] = None
    ) -> list[Session]:
        """List sessions."""
        return await self.backend.list_sessions(limit, offset, status, task_type)

    async def update_session(self, session_id: str, request: SessionUpdateRequest) -> Session:
        """Update a session."""
        return await self.backend.update_session(session_id, request)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return await self.backend.delete_session(session_id)

    async def create_memory(self, request: MemoryCreateRequest) -> Memory:
        """Create a new memory entry."""
        return await self.backend.create_memory(request)

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory entry by ID."""
        return await self.backend.get_memory(memory_id)

    async def update_memory(self, memory_id: str, request: MemoryUpdateRequest) -> Memory:
        """Update a memory entry."""
        return await self.backend.update_memory(memory_id, request)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        return await self.backend.delete_memory(memory_id)

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
        return await self.backend.search_memories(
            query,
            session_id,
            category,
            tags,
            min_priority,
            min_confidence,
            search_type,
            limit,
            offset,
        )

    async def create_relationship(self, request: RelationshipCreateRequest) -> Relationship:
        """Create a new relationship."""
        return await self.backend.create_relationship(request)

    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID."""
        return await self.backend.get_relationship(relationship_id)

    async def get_related_memories(
        self, memory_id: str, relationship_type: Optional[str] = None, limit: int = 10
    ) -> list[Memory]:
        """Get memories related to a specific memory."""
        return await self.backend.get_related_memories(memory_id, relationship_type, limit)

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        return await self.backend.delete_relationship(relationship_id)

    async def create_context_snapshot(
        self, request: ContextSnapshotCreateRequest
    ) -> ContextSnapshot:
        """Create a new context snapshot."""
        return await self.backend.create_context_snapshot(request)

    async def get_context_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Get a context snapshot by ID."""
        return await self.backend.get_context_snapshot(snapshot_id)

    async def list_context_snapshots(
        self, session_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[ContextSnapshot]:
        """List context snapshots."""
        return await self.backend.list_context_snapshots(session_id, limit, offset)

    async def create_task_progress(
        self, request: TaskProgressCreateRequest
    ) -> TaskProgress:
        """Create a new task progress entry."""
        return await self.backend.create_task_progress(request)

    async def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get a task progress entry by ID."""
        return await self.backend.get_task_progress(task_id)

    async def update_task_progress(
        self, task_id: str, request: TaskProgressUpdateRequest
    ) -> TaskProgress:
        """Update a task progress entry."""
        return await self.backend.update_task_progress(task_id, request)

    async def list_task_progress(
        self,
        session_id: Optional[str] = None,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskProgress]:
        """List task progress entries."""
        return await self.backend.list_task_progress(session_id, task_name, status, limit, offset)

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        return await self.backend.get_stats()

