"""Main storage manager class that integrates all storage operations."""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from src.logging_config import get_logger

from qdrant_client import QdrantClient

from ...models import (
    Project, MemoryFragment, MemoryContext, CognitiveAnchor, 
    SearchOptions, SearchResult
)

from .db import init_sqlite, get_or_create_collection
from .project import create_project, get_project, list_projects, delete_project, update_project
from .fragment import store_fragment, get_fragment, delete_fragment, delete_fragments, list_fragments_by_project, count_fragments_by_project, get_fragments_by_context
from .context import create_context, get_context, list_contexts_by_project, get_contexts_by_fragment, update_context_fragments, count_contexts_by_project
from .anchor import create_anchor, get_anchor
from .task import create_task, get_task, list_tasks_by_project, update_task, delete_task
from .search import semantic_search
from .utils import get_stats, health_check

logger = get_logger('memoire.mcp.storage')

class StorageManager:
    """Unified storage manager powered by Qdrant vector database."""
    
    def __init__(self, data_dir: str = None, use_memory: bool = None):
        # Get config values if not provided
        from src.config import config
        
        if data_dir is None:
            data_dir = config.get("storage.data_dir", "data")
        if use_memory is None:
            use_memory = config.get("storage.use_memory", False)

        # Hot-reloadable configuration
        self.config = config
        self.similarity_threshold = config.get("search.similarity_threshold", 0.6)
        
        # Subscribe to config changes for hot reload
        config.add_observer(self._on_config_change)
        
        # Always resolve data_dir relative to project root if not absolute
        if not Path(data_dir).is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent  # From src/core/storage/ to project root
            self.data_dir = project_root / data_dir
        else:
            self.data_dir = Path(data_dir)
            
        self.data_dir.mkdir(exist_ok=True)
        
        # Qdrant for vector storage
        if use_memory:
            # In-memory mode for testing
            self.qdrant_client = QdrantClient(":memory:")
            logger.info("Qdrant initialized in memory mode")
        else:
            # Persistent mode for production
            qdrant_path = self.data_dir / "qdrant"
            qdrant_path.mkdir(exist_ok=True)
            self.qdrant_client = QdrantClient(path=str(qdrant_path))
            logger.info(f"Qdrant initialized with persistent storage: {qdrant_path}")
        
        # SQLite for structured data
        sqlite_path = self.data_dir / "sqlite"
        sqlite_path.mkdir(exist_ok=True)
        self.db_path = sqlite_path / "memoire.db"
        
        # Initialize databases
        init_sqlite(self.db_path)
        
        logger.info(f"StorageManager initialized with data_dir: {self.data_dir}, similarity_threshold: {self.similarity_threshold}")

    def _on_config_change(self, new_config):
        """Handle configuration changes for hot reload."""
        try:
            old_threshold = self.similarity_threshold
            self.similarity_threshold = new_config.get("search", {}).get("similarity_threshold", 0.6)
            
            if old_threshold != self.similarity_threshold:
                logger.info(f"Hot reload: Similarity threshold updated {old_threshold:.2f} → {self.similarity_threshold:.2f}")
                
        except Exception as e:
            logger.error(f"Error during config hot reload in StorageManager: {e}")

    # ==================== PROJECT OPERATIONS ====================
    
    def create_project(self, project: Project) -> str:
        """Create a new project."""
        return create_project(self.db_path, self.qdrant_client, project)
    
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        return get_project(self.db_path, project_id)
    
    def list_projects(self) -> List[Project]:
        """List all projects."""
        return list_projects(self.db_path)
    
    def delete_project(self, project_id: str):
        """Delete a project and all its data."""
        return delete_project(self.db_path, self.qdrant_client, project_id)
    
    def update_project(self, project: Project) -> bool:
        """Update an existing project."""
        return update_project(self.db_path, project)
    
    # ==================== FRAGMENT OPERATIONS ====================
    
    def store_fragment(self, fragment: MemoryFragment, embedding: List[float]) -> str:
        """Store fragment in both SQLite and Qdrant."""
        logger.debug(f"Calling sub-module store_fragment for fragment_id: {fragment.id}")
        return store_fragment(self.db_path, self.qdrant_client, fragment, embedding)
    
    def get_fragment(self, fragment_id: str) -> Optional[MemoryFragment]:
        """Get fragment by ID."""
        logger.debug(f"Calling sub-module get_fragment for fragment_id: {fragment_id}")
        return get_fragment(self.db_path, fragment_id)
    
    def delete_fragment(self, fragment_id: str) -> bool:
        """Delete fragment from both SQLite and Qdrant."""
        return delete_fragment(self.db_path, self.qdrant_client, fragment_id)
    
    def delete_fragments(self, fragment_ids: List[str], project_id: str) -> bool:
        """Delete multiple fragments from both SQLite and Qdrant."""
        return delete_fragments(self.db_path, self.qdrant_client, fragment_ids, project_id)
    
    def list_fragments_by_project(self, project_id: str, limit: int = None) -> List[MemoryFragment]:
        """List fragments for a project."""
        logger.debug(f"Calling sub-module list_fragments_by_project for project_id: {project_id}")
        if limit is None:
            # Use hot-reloadable config
            limit = self.config.get("search.max_results", 50)
            logger.debug(f"Limit not provided, using config value: {limit}")
        return list_fragments_by_project(self.db_path, project_id, limit)

    def count_fragments_by_project(self, project_id: str) -> int:
        """Count fragments for a project."""
        return count_fragments_by_project(self.db_path, project_id)
    
    def get_fragments_by_context(self, context_id: str) -> List[MemoryFragment]:
        """Get all fragments for a given context ID."""
        return get_fragments_by_context(self.db_path, context_id)

    # ==================== SEARCH OPERATIONS ====================
    
    def semantic_search(self, query_embedding: List[float], options: SearchOptions) -> List[Tuple[str, float]]:
        """
        Perform semantic search using Qdrant vector database.
        """
        return semantic_search(self.qdrant_client, query_embedding, options)
    
    def search_fragments(self, query_embedding: List[float], options: SearchOptions) -> List[SearchResult]:
        """Complete search with fragment objects and context."""
        # Get semantic search results
        search_results = self.semantic_search(query_embedding, options)

        # Fetch full fragment objects
        results = []
        for fragment_id, similarity in search_results:
            fragment = self.get_fragment(fragment_id)
            if fragment:
                # Get context if fragment belongs to one
                context = None
                if fragment.context_ids:
                    context = self.get_context(fragment.context_ids[0])
                
                # Get anchors
                anchors = []
                if fragment.anchor_ids:
                    anchors = [self.get_anchor(aid) for aid in fragment.anchor_ids]
                    anchors = [a for a in anchors if a]  # Filter None
                
                results.append(SearchResult(
                    fragment=fragment,
                    similarity=similarity,
                    context=context,
                    anchors=anchors
                ))
            else:
                logger.warning(f"Fragment with id {fragment_id} found in vector search but not in DB.")

        return results
    
    # ==================== CONTEXT OPERATIONS ====================
    
    def create_context(self, context: MemoryContext) -> str:
        """Create a new context."""
        return create_context(self.db_path, context)
    
    def get_context(self, context_id: str) -> Optional[MemoryContext]:
        """Get context by ID."""
        return get_context(self.db_path, context_id)
    
    
    
    def list_contexts_by_project(self, project_id: str) -> List[MemoryContext]:
        """List all contexts for a project."""
        return list_contexts_by_project(self.db_path, project_id)
    
    def get_contexts_by_fragment(self, fragment_id: str) -> List[MemoryContext]:
        """Get all contexts containing a specific fragment."""
        return get_contexts_by_fragment(self.db_path, fragment_id)
    
    def update_context_fragments(self, context_id: str, fragment_ids: List[str]) -> bool:
        """Update fragment list for a context."""
        return update_context_fragments(self.db_path, context_id, fragment_ids)

    def count_contexts_by_project(self, project_id: str) -> int:
        """Count contexts for a project."""
        return count_contexts_by_project(self.db_path, project_id)
    
    def delete_context(self, context_id: str) -> bool:
        """Delete a context and its associated fragments."""
        from .context import delete_context as delete_context_func
        return delete_context_func(self.db_path, self.qdrant_client, context_id)
    
    # ==================== ANCHOR OPERATIONS ====================
    
    def create_anchor(self, anchor: CognitiveAnchor) -> str:
        """Create a new cognitive anchor."""
        return create_anchor(self.db_path, anchor)
    
    def get_anchor(self, anchor_id: str) -> Optional[CognitiveAnchor]:
        """Get anchor by ID."""
        return get_anchor(self.db_path, anchor_id)

    # ==================== TASK OPERATIONS ====================

    def create_task(self, task: 'Task') -> str:
        """Create a new task."""
        return create_task(self.db_path, task)

    def get_task(self, task_id: str) -> Optional['Task']:
        """Get a task by its ID."""
        return get_task(self.db_path, task_id)

    def list_tasks_by_project(self, project_id: str, status: Optional['TaskStatus'] = None) -> List['Task']:
        """List all tasks for a project, optionally filtering by status."""
        return list_tasks_by_project(self.db_path, project_id, status)

    def update_task(self, task_id: str, title: Optional[str] = None, description: Optional[str] = None, status: Optional['TaskStatus'] = None) -> bool:
        """Update a task's title, description, or status."""
        return update_task(self.db_path, task_id, title=title, description=description, status=status)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        return delete_task(self.db_path, task_id)

    def count_tasks_by_project(self, project_id: str) -> Dict[str, int]:
        """Count tasks for a project, grouped by status."""
        from .task import count_tasks_by_project
        return count_tasks_by_project(self.db_path, project_id)
    
    # ==================== UTILITY METHODS ====================
    
    def get_stats(self, project_id: str) -> Dict[str, int]:
        """Get statistics for a project."""
        return get_stats(self.db_path, self.qdrant_client, project_id)
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of both storage systems."""
        return health_check(self.db_path, self.qdrant_client)