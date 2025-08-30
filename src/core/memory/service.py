"""
Memory service orchestrator for Memoire.

Main MemoryService class that coordinates all memory operations while maintaining
the same API as the original monolithic implementation.
"""

from typing import List, Dict, Any, Optional, Union

from src.logging_config import get_logger

from ...models import (
    Project, MemoryFragment, MemoryContext, CognitiveAnchor, 
    SearchOptions, SearchResult, Task, TaskStatus
)
from ..storage import StorageManager
from ..embedding import EmbeddingService
from ...config import config

# Import modular functions
from . import projects
from . import fragments
from . import contexts
from . import anchors
from . import search
from . import analytics
from . import health

logger = get_logger('memoire.mcp.memory')


class MemoryService:
    """Core service for semantic memory operations.
    
    This orchestrator maintains the same API as the original monolithic implementation
    while delegating to specialized modules for better organization and maintainability.
    """
    
    def __init__(self, storage: StorageManager, embedding: EmbeddingService):
        self.storage = storage
        self.embedding = embedding
        self._default_project_id: Optional[str] = None
        
        # Get config instance
        self.config = config
        
        logger.info("MemoryService initialized (modular architecture)")

    # ==================== PROJECT MANAGEMENT ====================
    
    async def create_project(self, name: str, description: str, 
                           system_prompt: str = "") -> str:
        """Create a new memory project with flexible schema."""
        project_id = await projects.create_project(
            self.storage, name, description, system_prompt
        )

        # Set as default if it's the first project
        if not self._default_project_id:
            self._default_project_id = project_id
            logger.info(f"Set new project as default: {project_id}")

        return project_id
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return projects.get_project(self.storage, project_id)
    
    def list_projects(self) -> List[Project]:
        """List all projects."""
        return projects.list_projects(self.storage)
    
    def get_default_project_id(self) -> Optional[str]:
        """Get the default project ID."""
        return self._default_project_id
    
    def set_default_project(self, project_id: str):
        """Set the default project."""
        self._default_project_id = project_id
        logger.info(f"Set default project: {project_id}")

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all its associated data."""
        if not self.storage.get_project(project_id):
            logger.error(f"Attempted to delete non-existent project with ID: {project_id}")
            return False
        try:
            self.storage.delete_project(project_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
            return False
    
    # ==================== FRAGMENT OPERATIONS ====================
    
    async def store_fragment(self, project_id: str, content: str,
                           category: str = "general", tags: List[str] = None,
                           source: str = "user", custom_fields: Dict[str, Any] = None,
                           context_ids: List[str] = None, anchor_ids: List[str] = None) -> str:
        """Store a fragment of information with semantic embedding."""
        return await fragments.store_fragment(
            self.storage, self.embedding, project_id, content,
            category, tags, source, custom_fields, context_ids, anchor_ids
        )
    
    def get_fragment(self, fragment_id: str) -> Optional[MemoryFragment]:
        """Get fragment by ID."""
        return fragments.get_fragment(self.storage, fragment_id)
    
    # Fragment updates not supported - use delete + create for modifications
    
    def delete_fragment(self, fragment_id: str) -> bool:
        """Delete a fragment."""
        return self.storage.delete_fragment(fragment_id)

    async def delete_fragments(self, fragment_ids: List[str], project_id: str) -> bool:
        """Delete multiple fragments."""
        return await fragments.delete_fragments(self.storage, fragment_ids, project_id)
    
    def list_fragments_by_project(self, project_id: str, limit: int = None) -> List[MemoryFragment]:
        """List fragments for a project."""
        if limit is None:
            limit = config.get("search.max_results", 50)
            
        return self.storage.list_fragments_by_project(project_id, limit)

    # ==================== RAW DATA ACCESS ====================

    def get_project_summary(self, project_id: str) -> Optional[Dict[str, any]]:
        """Get a summary of counts for a project."""
        if not self.storage.get_project(project_id):
            logger.error(f"Attempted to get summary for non-existent project with ID: {project_id}")
            return None

        context_count = self.storage.count_contexts_by_project(project_id)
        fragment_count = self.storage.count_fragments_by_project(project_id)
        task_counts = self.storage.count_tasks_by_project(project_id)

        return {
            "contexts": context_count,
            "fragments": fragment_count,
            "tasks": task_counts
        }

    def list_contexts(self, project_id: str) -> List[MemoryContext]:
        """List all contexts for a given project ID."""
        if not self.storage.get_project(project_id):
            logger.error(f"Attempted to list contexts for non-existent project with ID: {project_id}")
            return []
        return self.storage.list_contexts_by_project(project_id)

    def get_fragments_by_context(self, project_id: str, context_id: str) -> List[MemoryFragment]:
        """Get all fragments belonging to a specific context ID in a project ID."""
        # Validate project and context exist
        if not self.storage.get_project(project_id):
            logger.error(f"Attempted to get fragments for non-existent project with ID: {project_id}")
            return []
        context = self.storage.get_context(context_id)
        if not context or context.project_id != project_id:
            logger.error(f"Context {context_id} not found or does not belong to project {project_id}")
            return []

        # Directly query fragments by context_id for a more robust approach
        return self.storage.get_fragments_by_context(context_id)
    
    # ==================== SEARCH OPERATIONS ====================
    
    async def search_memory(self, query: str, 
                          project_ids: Optional[Union[str, List[str]]] = None,
                          options: SearchOptions = None) -> List[SearchResult]:
        """Search memory using semantic similarity and filters."""
        if options is None:
            # Get default threshold from config
            threshold = config.get("search.similarity_threshold", 0.6)
            max_results = config.get("search.max_results", 50)
            options = SearchOptions(
                similarity_threshold=threshold,
                max_results=max_results
            )
        
        # Handle project_ids: convert single string to list, or use None for global search
        if isinstance(project_ids, str):
            project_ids_list = [project_ids]
        elif project_ids is None:
            project_ids_list = None # Indicates global search
        else:
            project_ids_list = project_ids # Already a list

        return await search.search_memory(
            self.storage, self.embedding, query, options, project_ids, self._default_project_id
        )

    async def search_memory_by_vector(self, query_vector: List[float], options: SearchOptions) -> List[SearchResult]:
        """Search memory using a pre-computed vector."""
        return await search.search_memory_by_vector(self.storage, query_vector, options)
    
    async def find_similar_fragments(self, fragment_id: str, 
                                   limit: int = None) -> List[SearchResult]:
        """Find fragments similar to a given fragment."""
        if limit is None:
            limit = config.get("search.max_results", 50) // 10  # Use 1/10th for similar fragments

        return await search.find_similar_fragments(
            self.storage, self.embedding, fragment_id, limit
        )
    
    # ==================== CONTEXT OPERATIONS ====================
    
    def create_context(self, project_id: str, name: str,
                      description: str = "", fragment_ids: List[str] = None,
                      custom_fields: Dict[str, Any] = None,
                      parent_context_id: str = None) -> str:
        """Create a new context for organizing fragments."""
        return contexts.create_context(
            self.storage, project_id, name, description,
            fragment_ids, custom_fields, parent_context_id
        )
    
    def get_context(self, context_id: str) -> Optional[MemoryContext]:
        """Get context by ID."""
        return contexts.get_context(self.storage, context_id)
    
    def list_contexts_by_project(self, project_id: str) -> List[MemoryContext]:
        """List all contexts for a project."""
        return self.storage.list_contexts_by_project(project_id)
    
    def get_contexts_by_fragment(self, fragment_id: str) -> List[MemoryContext]:
        """Get all contexts containing a specific fragment."""
        return self.storage.get_contexts_by_fragment(fragment_id)
    
    def add_fragment_to_context(self, context_id: str, fragment_id: str) -> bool:
        """Add a fragment to a context."""
        return contexts.add_fragment_to_context(self.storage, context_id, fragment_id)

    def delete_context(self, project_id: str, context_id: str) -> bool:
        """Delete a context by its ID, ensuring it belongs to the correct project."""
        context = self.storage.get_context(context_id)
        if not context or context.project_id != project_id:
            logger.warning(f"Context '{context_id}' not found or does not belong to project '{project_id}' for deletion.")
            return False
        
        return self.storage.delete_context(context.id)
    
    # ==================== ANCHOR OPERATIONS ====================
    
    def create_anchor(self, project_id: str, title: str,
                     description: str = "", priority: str = "medium",
                     fragment_ids: List[str] = None, context_ids: List[str] = None,
                     tags: List[str] = None, custom_fields: Dict[str, Any] = None) -> str:
        """Create a new cognitive anchor."""
        return anchors.create_anchor(
            self.storage, project_id, title, description,
            priority, fragment_ids, context_ids, tags, custom_fields
        )
    
    def get_anchor(self, anchor_id: str) -> Optional[CognitiveAnchor]:
        """Get anchor by ID."""
        return anchors.get_anchor(self.storage, anchor_id)
    
    def access_anchor(self, anchor_id: str):
        """Mark an anchor as accessed (updates access count and timestamp)."""
        return anchors.access_anchor(self.storage, anchor_id)
    
    # ==================== ANALYTICS AND INSIGHTS ====================
    
    def get_project_stats(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a project."""
        return analytics.get_project_stats(self.storage, self.embedding, project_id)
    
    async def find_knowledge_gaps(self, project_id: str, threshold: float = None) -> List[str]:
        """Identify potential knowledge gaps in the memory."""
        if threshold is None:
            threshold = config.get("search.similarity_threshold", 0.6) / 2  # Use half of search threshold

        return await analytics.find_knowledge_gaps(self.storage, self.embedding, project_id, threshold)
    
    async def suggest_contexts(self, project_id: str) -> List[Dict[str, Any]]:
        """Suggest potential contexts based on fragment clustering."""
        return await analytics.suggest_contexts(self.storage, self.embedding, project_id)
    
    # ==================== HEALTH AND MAINTENANCE ====================
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of memory service and dependencies."""
        health_status = health.health_check(self.storage, self.embedding, self._default_project_id)
        return health_status
    
    def cleanup_old_cache(self):
        """Clean up old cache entries."""
        result = health.cleanup_old_cache(self.embedding)
        return result

    # ==================== TASK MANAGEMENT ====================

    def create_task(self, project_id: str, title: str, description: str = "") -> Optional[str]:
        """Create a new task in a project."""
        if not self.storage.get_project(project_id):
            logger.error(f"Attempted to create task in non-existent project with ID: {project_id}")
            return None
        task = Task(project_id=project_id, title=title, description=description)
        return self.storage.create_task(task)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
        return self.storage.get_task(task_id)

    def list_tasks(self, project_id: str, status: Optional[str] = None) -> List[Task]:
        """List tasks for a project, optionally filtering by status."""
        if not self.storage.get_project(project_id):
            logger.error(f"Attempted to list tasks for non-existent project with ID: {project_id}")
            return []
        task_status = TaskStatus(status) if status else None
        
        # Directly return the list of Task objects
        return self.storage.list_tasks_by_project(project_id, task_status)

    def update_task(self, task_id: str, title: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None) -> bool:
        """Update a task's title, description, or status."""
        task_status = TaskStatus(status) if status else None
        return self.storage.update_task(task_id, title=title, description=description, status=task_status)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        return self.storage.delete_task(task_id)

# Export main class
__all__ = ["MemoryService"]
