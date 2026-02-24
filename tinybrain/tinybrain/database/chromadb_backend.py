"""ChromaDB backend implementation (optional)."""

from typing import Any, Optional

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from tinybrain.database.base import DatabaseBackend
from tinybrain.models.memory import Memory, MemoryCreateRequest, MemoryUpdateRequest
from tinybrain.models.session import Session, SessionCreateRequest, SessionUpdateRequest
from tinybrain.models.relationship import (
    Relationship,
    RelationshipCreateRequest,
    RelationshipUpdateRequest,
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


class ChromaDBBackend(DatabaseBackend):
    """ChromaDB implementation of the database backend (for vector/semantic search)."""

    def __init__(self, persist_directory: str, sqlite_backend: DatabaseBackend):
        """Initialize the ChromaDB backend.
        
        Note: ChromaDB is used for semantic search only. All other operations
        are delegated to the SQLite backend.
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB is not installed. Install it with: pip install chromadb"
            )
        
        self.persist_directory = persist_directory
        self.sqlite_backend = sqlite_backend
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialize the ChromaDB backend."""
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is not installed")
        
        # Initialize SQLite backend first
        await self.sqlite_backend.initialize()
        
        # Initialize ChromaDB client
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection for memory embeddings
        self._collection = self._client.get_or_create_collection(
            name="memory_embeddings",
            metadata={"hnsw:space": "cosine"}
        )

    async def close(self) -> None:
        """Close the database connection."""
        await self.sqlite_backend.close()
        self._client = None
        self._collection = None

    async def health_check(self) -> bool:
        """Perform a health check."""
        return await self.sqlite_backend.health_check()

    # Delegate all non-search operations to SQLite
    async def create_session(self, request: SessionCreateRequest) -> Session:
        """Create a new session."""
        return await self.sqlite_backend.create_session(request)

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return await self.sqlite_backend.get_session(session_id)

    async def list_sessions(
        self, limit: int = 50, offset: int = 0, status: Optional[str] = None, task_type: Optional[str] = None
    ) -> list[Session]:
        """List sessions."""
        return await self.sqlite_backend.list_sessions(limit, offset, status, task_type)

    async def update_session(self, session_id: str, request: SessionUpdateRequest) -> Session:
        """Update a session."""
        return await self.sqlite_backend.update_session(session_id, request)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return await self.sqlite_backend.delete_session(session_id)

    async def create_memory(self, request: MemoryCreateRequest) -> Memory:
        """Create a new memory entry."""
        memory = await self.sqlite_backend.create_memory(request)
        
        # TODO: Generate embedding and store in ChromaDB
        # This would require an embedding model (e.g., sentence-transformers)
        # For now, we just store in SQLite
        
        return memory

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory entry by ID."""
        return await self.sqlite_backend.get_memory(memory_id)

    async def update_memory(self, memory_id: str, request: MemoryUpdateRequest) -> Memory:
        """Update a memory entry."""
        memory = await self.sqlite_backend.update_memory(memory_id, request)
        
        # TODO: Update embedding in ChromaDB if content changed
        
        return memory

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        # TODO: Delete from ChromaDB as well
        return await self.sqlite_backend.delete_memory(memory_id)

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
        """Search for memory entries.
        
        If search_type is 'semantic' and ChromaDB is available, use semantic search.
        Otherwise, delegate to SQLite backend.
        """
        if search_type == "semantic" and query and CHROMADB_AVAILABLE and self._collection:
            # TODO: Implement semantic search using ChromaDB
            # This would require:
            # 1. Generating an embedding for the query
            # 2. Querying ChromaDB for similar embeddings
            # 3. Getting the corresponding memory IDs
            # 4. Fetching full memory objects from SQLite
            # For now, fall back to SQLite search
            pass
        
        # Fall back to SQLite search
        return await self.sqlite_backend.search_memories(
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
        return await self.sqlite_backend.create_relationship(request)

    async def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID."""
        return await self.sqlite_backend.get_relationship(relationship_id)

    async def get_related_memories(
        self, memory_id: str, relationship_type: Optional[str] = None, limit: int = 10
    ) -> list[Memory]:
        """Get memories related to a specific memory."""
        return await self.sqlite_backend.get_related_memories(memory_id, relationship_type, limit)

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        return await self.sqlite_backend.delete_relationship(relationship_id)

    async def create_context_snapshot(
        self, request: ContextSnapshotCreateRequest
    ) -> ContextSnapshot:
        """Create a new context snapshot."""
        return await self.sqlite_backend.create_context_snapshot(request)

    async def get_context_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Get a context snapshot by ID."""
        return await self.sqlite_backend.get_context_snapshot(snapshot_id)

    async def list_context_snapshots(
        self, session_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[ContextSnapshot]:
        """List context snapshots."""
        return await self.sqlite_backend.list_context_snapshots(session_id, limit, offset)

    async def create_task_progress(
        self, request: TaskProgressCreateRequest
    ) -> TaskProgress:
        """Create a new task progress entry."""
        return await self.sqlite_backend.create_task_progress(request)

    async def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get a task progress entry by ID."""
        return await self.sqlite_backend.get_task_progress(task_id)

    async def update_task_progress(
        self, task_id: str, request: TaskProgressUpdateRequest
    ) -> TaskProgress:
        """Update a task progress entry."""
        return await self.sqlite_backend.update_task_progress(task_id, request)

    async def list_task_progress(
        self,
        session_id: Optional[str] = None,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TaskProgress]:
        """List task progress entries."""
        return await self.sqlite_backend.list_task_progress(session_id, task_name, status, limit, offset)

    async def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        stats = await self.sqlite_backend.get_stats()
        if self._collection:
            stats["chromadb_collection_count"] = self._collection.count()
        return stats

