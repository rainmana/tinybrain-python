"""MCP server implementation using FastMCP."""

import json
from pathlib import Path
from typing import Any, Optional

from fastmcp import FastMCP
from pydantic import ValidationError

from ..database import Database, CogDBBackend
from ..models.memory import MemoryCreateRequest, MemoryUpdateRequest, MemorySearchRequest
from ..models.session import SessionCreateRequest, SessionUpdateRequest, SessionListRequest
from ..models.relationship import RelationshipCreateRequest, RelationshipType
from ..models.context_snapshot import ContextSnapshotCreateRequest
from ..models.task_progress import TaskProgressCreateRequest, TaskProgressUpdateRequest


_db_instance: Optional[Database] = None


def get_database(cog_home: Optional[str] = None, cog_path_prefix: Optional[str] = None) -> Database:
    """Get or create the database instance."""
    global _db_instance

    if _db_instance is None:
        if cog_home is None:
            cog_home = "tinybrain"
        if cog_path_prefix is None:
            cog_path_prefix = str(Path.home() / ".tinybrain")

        backend = CogDBBackend(cog_home=cog_home, cog_path_prefix=cog_path_prefix)
        _db_instance = Database(backend)

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(_db_instance.initialize())

    return _db_instance


def create_mcp_server(cog_home: Optional[str] = None, cog_path_prefix: Optional[str] = None) -> FastMCP:
    """Create and configure the MCP server."""
    mcp = FastMCP("TinyBrain")

    def get_db():
        return get_database(cog_home, cog_path_prefix)
    
    # Session management tools
    @mcp.tool()
    async def create_session(
        name: str,
        task_type: str = "general",
        description: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new security assessment session."""
        try:
            db = get_db()
            metadata_dict = {}
            if metadata:
                metadata_dict = json.loads(metadata)
            
            request = SessionCreateRequest(
                name=name,
                task_type=task_type,
                description=description,
                metadata=metadata_dict,
            )
            
            session = await db.create_session(request)
            return {
                "session_id": session.id,
                "name": session.name,
                "task_type": session.task_type,
                "status": session.status,
                "description": session.description,
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def get_session(session_id: str) -> dict[str, Any]:
        """Get session details by ID."""
        try:
            db = get_db()
            session = await db.get_session(session_id)
            if not session:
                return {"error": f"Session {session_id} not found"}
            
            return {
                "session_id": session.id,
                "name": session.name,
                "task_type": session.task_type,
                "status": session.status,
                "description": session.description,
                "metadata": session.metadata,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def list_sessions(
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> dict[str, Any]:
        """List all sessions with optional filtering."""
        try:
            db = get_db()
            sessions = await db.list_sessions(limit, offset, status, task_type)
            return {
                "sessions": [
                    {
                        "session_id": s.id,
                        "name": s.name,
                        "task_type": s.task_type,
                        "status": s.status,
                        "description": s.description,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in sessions
                ],
                "count": len(sessions),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Memory management tools
    @mcp.tool()
    async def store_memory(
        session_id: str,
        title: str,
        content: str,
        category: str,
        priority: int = 5,
        confidence: float = 0.5,
        tags: Optional[str] = None,
        source: Optional[str] = None,
        content_type: str = "text",
    ) -> dict[str, Any]:
        """Store a new piece of information in memory."""
        try:
            db = get_db()
            tags_list = []
            if tags:
                try:
                    tags_list = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            
            request = MemoryCreateRequest(
                session_id=session_id,
                title=title,
                content=content,
                category=category,
                priority=priority,
                confidence=confidence,
                tags=tags_list,
                source=source,
                content_type=content_type,
            )
            
            db = get_db()
            memory = await db.create_memory(request)
            return {
                "memory_id": memory.id,
                "title": memory.title,
                "category": memory.category,
                "priority": memory.priority,
                "confidence": memory.confidence,
                "created_at": memory.created_at.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def get_memory(memory_id: str    ) -> dict[str, Any]:
        """Retrieve a memory entry by ID."""
        try:
            db = get_db()
            memory = await db.get_memory(memory_id)
            if not memory:
                return {"error": f"Memory {memory_id} not found"}
            
            return {
                "memory_id": memory.id,
                "session_id": memory.session_id,
                "title": memory.title,
                "content": memory.content,
                "category": memory.category,
                "priority": memory.priority,
                "confidence": memory.confidence,
                "tags": memory.tags,
                "source": memory.source,
                "content_type": memory.content_type,
                "created_at": memory.created_at.isoformat(),
                "updated_at": memory.updated_at.isoformat(),
                "access_count": memory.access_count,
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def search_memories(
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        min_priority: Optional[int] = None,
        min_confidence: Optional[float] = None,
        search_type: str = "semantic",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search for memories using various strategies."""
        try:
            db = get_db()
            tags_list = None
            if tags:
                try:
                    tags_list = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            
            memories = await db.search_memories(
                query=query,
                session_id=session_id,
                category=category,
                tags=tags_list,
                min_priority=min_priority,
                min_confidence=min_confidence,
                search_type=search_type,
                limit=limit,
                offset=offset,
            )
            
            return {
                "memories": [
                    {
                        "memory_id": m.id,
                        "session_id": m.session_id,
                        "title": m.title,
                        "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                        "category": m.category,
                        "priority": m.priority,
                        "confidence": m.confidence,
                        "tags": m.tags,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in memories
                ],
                "count": len(memories),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def update_memory(
        memory_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[int] = None,
        confidence: Optional[float] = None,
        tags: Optional[str] = None,
        source: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update an existing memory entry."""
        try:
            db = get_db()
            tags_list = None
            if tags:
                try:
                    tags_list = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            
            request = MemoryUpdateRequest(
                title=title,
                content=content,
                category=category,
                priority=priority,
                confidence=confidence,
                tags=tags_list,
                source=source,
            )
            
            memory = await db.update_memory(memory_id, request)
            return {
                "memory_id": memory.id,
                "title": memory.title,
                "category": memory.category,
                "updated_at": memory.updated_at.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def delete_memory(memory_id: str    ) -> dict[str, Any]:
        """Delete a memory entry."""
        try:
            db = get_db()
            success = await db.delete_memory(memory_id)
            return {"success": success, "memory_id": memory_id}
        except Exception as e:
            return {"error": str(e)}
    
    # Relationship management tools
    @mcp.tool()
    async def create_relationship(
        source_memory_id: str,
        target_memory_id: str,
        relationship_type: str,
        strength: float = 0.5,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a relationship between two memory entries."""
        try:
            db = get_db()
            request = RelationshipCreateRequest(
                source_id=source_memory_id,
                target_id=target_memory_id,
                type=RelationshipType(relationship_type),
                strength=strength,
                description=description,
            )
            
            relationship = await db.create_relationship(request)
            return {
                "relationship_id": relationship.id,
                "source_id": relationship.source_id,
                "target_id": relationship.target_id,
                "type": relationship.type.value,
                "strength": relationship.strength,
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def get_related_memories(
        memory_id: str,
        relationship_type: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Get memories related to a specific memory."""
        try:
            db = get_db()
            memories = await db.get_related_memories(memory_id, relationship_type, limit)
            return {
                "memories": [
                    {
                        "memory_id": m.id,
                        "title": m.title,
                        "category": m.category,
                        "priority": m.priority,
                    }
                    for m in memories
                ],
                "count": len(memories),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Context snapshot tools
    @mcp.tool()
    async def create_context_snapshot(
        session_id: str,
        name: str,
        context_data: str,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a snapshot of the current context."""
        try:
            db = get_db()
            context_dict = json.loads(context_data)
            request = ContextSnapshotCreateRequest(
                session_id=session_id,
                name=name,
                context_data=context_dict,
                description=description,
            )
            
            snapshot = await db.create_context_snapshot(request)
            return {
                "snapshot_id": snapshot.id,
                "name": snapshot.name,
                "session_id": snapshot.session_id,
                "created_at": snapshot.created_at.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def get_context_snapshot(snapshot_id: str    ) -> dict[str, Any]:
        """Retrieve a context snapshot by ID."""
        try:
            db = get_db()
            snapshot = await db.get_context_snapshot(snapshot_id)
            if not snapshot:
                return {"error": f"Snapshot {snapshot_id} not found"}
            
            return {
                "snapshot_id": snapshot.id,
                "session_id": snapshot.session_id,
                "name": snapshot.name,
                "context_data": snapshot.context_data,
                "description": snapshot.description,
                "created_at": snapshot.created_at.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def list_context_snapshots(
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List context snapshots for a session."""
        try:
            db = get_db()
            snapshots = await db.list_context_snapshots(session_id, limit, offset)
            return {
                "snapshots": [
                    {
                        "snapshot_id": s.id,
                        "session_id": s.session_id,
                        "name": s.name,
                        "description": s.description,
                        "created_at": s.created_at.isoformat(),
                    }
                    for s in snapshots
                ],
                "count": len(snapshots),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Task progress tools
    @mcp.tool()
    async def create_task_progress(
        session_id: str,
        task_name: str,
        stage: str,
        status: str = "pending",
        progress_percentage: float = 0.0,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new task progress entry."""
        try:
            db = get_db()
            request = TaskProgressCreateRequest(
                session_id=session_id,
                task_name=task_name,
                stage=stage,
                status=status,
                progress_percentage=progress_percentage,
                notes=notes,
            )
            
            task = await db.create_task_progress(request)
            return {
                "task_id": task.id,
                "session_id": task.session_id,
                "task_name": task.task_name,
                "stage": task.stage,
                "status": task.status,
                "progress_percentage": task.progress_percentage,
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def update_task_progress(
        task_id: str,
        stage: Optional[str] = None,
        status: Optional[str] = None,
        progress_percentage: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update progress on a task."""
        try:
            db = get_db()
            request = TaskProgressUpdateRequest(
                stage=stage,
                status=status,
                progress_percentage=progress_percentage,
                notes=notes,
            )
            
            task = await db.update_task_progress(task_id, request)
            return {
                "task_id": task.id,
                "stage": task.stage,
                "status": task.status,
                "progress_percentage": task.progress_percentage,
                "updated_at": task.updated_at.isoformat(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def list_task_progress(
        session_id: Optional[str] = None,
        task_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List task progress entries for a session."""
        try:
            db = get_db()
            tasks = await db.list_task_progress(session_id, task_name, status, limit, offset)
            return {
                "tasks": [
                    {
                        "task_id": t.id,
                        "session_id": t.session_id,
                        "task_name": t.task_name,
                        "stage": t.stage,
                        "status": t.status,
                        "progress_percentage": t.progress_percentage,
                        "created_at": t.created_at.isoformat(),
                    }
                    for t in tasks
                ],
                "count": len(tasks),
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Statistics and health tools
    @mcp.tool()
    async def get_memory_stats() -> dict[str, Any]:
        """Get comprehensive statistics about memory usage."""
        try:
            db = get_db()
            stats = await db.get_stats()
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def health_check() -> dict[str, Any]:
        """Perform a health check on the database and server."""
        try:
            db = get_db()
            healthy = await db.health_check()
            return {"status": "healthy" if healthy else "unhealthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    # Security data tools
    @mcp.tool()
    async def download_security_data(
        data_source: str,
        force_update: bool = False,
    ) -> dict[str, Any]:
        """Download security datasets from external sources (NVD, ATT&CK, OWASP)."""
        try:
            from tinybrain.services.security_data_downloader import SecurityDataDownloader
            
            downloader = SecurityDataDownloader()
            
            if data_source == "nvd":
                cves = await downloader.download_nvd_dataset(max_results=100)  # Limit for testing
                await downloader.close()
                return {
                    "status": "completed",
                    "data_source": "nvd",
                    "records_downloaded": len(cves),
                    "message": f"Downloaded {len(cves)} CVEs (limited to 100 for testing)",
                }
            elif data_source == "attack":
                techniques, tactics = await downloader.download_attack_dataset()
                await downloader.close()
                return {
                    "status": "completed",
                    "data_source": "attack",
                    "techniques": len(techniques),
                    "tactics": len(tactics),
                    "message": f"Downloaded {len(techniques)} techniques and {len(tactics)} tactics",
                }
            elif data_source == "owasp":
                procedures = await downloader.download_owasp_dataset()
                await downloader.close()
                return {
                    "status": "completed",
                    "data_source": "owasp",
                    "records_downloaded": len(procedures),
                    "message": "OWASP download not fully implemented",
                }
            else:
                return {"error": f"Unknown data source: {data_source}"}
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def query_nvd(
        cwe_id: Optional[str] = None,
        min_cvss: Optional[float] = None,
        severity: Optional[str] = None,
        component: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Query NVD CVE data from the security knowledge hub."""
        try:
            from tinybrain.services.security_retrieval_service import SecurityRetrievalService
            
            db = get_db()
            service = SecurityRetrievalService(db.backend)
            
            results = await service.query_nvd(
                cwe_id=cwe_id,
                min_cvss=min_cvss,
                severity=severity,
                component=component,
                limit=limit,
            )
            
            return {
                "results": results,
                "count": len(results),
                "data_source": "nvd",
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def query_attack(
        query: Optional[str] = None,
        tactic: Optional[str] = None,
        technique_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Query MITRE ATT&CK data from the security knowledge hub."""
        try:
            from tinybrain.services.security_retrieval_service import SecurityRetrievalService
            
            db = get_db()
            service = SecurityRetrievalService(db.backend)
            
            results = await service.query_attack(
                query=query,
                tactic=tactic,
                technique_id=technique_id,
                platform=platform,
                limit=limit,
            )
            
            return {
                "results": results,
                "count": len(results),
                "data_source": "attack",
            }
        except Exception as e:
            return {"error": str(e)}
    
    @mcp.tool()
    async def query_owasp(
        query: Optional[str] = None,
        category: Optional[str] = None,
        vulnerability_type: Optional[str] = None,
        testing_phase: Optional[str] = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Query OWASP testing procedures from the security knowledge hub."""
        try:
            from tinybrain.services.security_retrieval_service import SecurityRetrievalService
            
            db = get_db()
            service = SecurityRetrievalService(db.backend)
            
            results = await service.query_owasp(
                query=query,
                category=category,
                vulnerability_type=vulnerability_type,
                testing_phase=testing_phase,
                limit=limit,
            )
            
            return {
                "results": results,
                "count": len(results),
                "data_source": "owasp",
            }
        except Exception as e:
            return {"error": str(e)}
    
    return mcp

