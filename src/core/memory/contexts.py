"""
Context operations for Memoire memory system.

Handles creation and management of cognitive contexts for thematic organization.
"""

# TODO: Implement advanced context management functions:
# - remove_fragment_from_context
# - list_contexts (with hierarchy filtering)
# - get_context_hierarchy
# - update_context
# - delete_context

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from src.logging_config import get_logger
from ...models import MemoryContext
from ..storage import StorageManager

logger = get_logger('memoire.mcp.memory')


def create_context(storage: StorageManager, project_id: str, name: str,
                  description: str = "", fragment_ids: List[str] = None,
                  custom_fields: Dict[str, Any] = None,
                  parent_context_id: str = None) -> str:
    """Create a new context for organizing fragments.
    
    Args:
        storage: Storage manager instance
        project_id: ID of the project this context belongs to
        name: Name of the context
        description: Description of the context
        fragment_ids: List of fragment IDs to include in this context
        custom_fields: Additional metadata fields
        parent_context_id: ID of parent context for hierarchical organization
        
    Returns:
        Context ID of the created context
    """
    if fragment_ids is None: fragment_ids = []
    if custom_fields is None: custom_fields = {}
    
    context_id = str(uuid.uuid4())
    context = MemoryContext(
        id=context_id,
        project_id=project_id,
        name=name,
        description=description,
        fragment_ids=fragment_ids,
        parent_context_id=parent_context_id,
        custom_fields=custom_fields,
        fragment_count=len(fragment_ids),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    stored_id = storage.create_context(context)
    
    logger.info(f"Created context: {name} ({stored_id})")
    return stored_id


def get_context(storage: StorageManager, context_id: str) -> Optional[MemoryContext]:
    """Get context by ID.
    
    Args:
        storage: Storage manager instance
        context_id: ID of the context to retrieve
        
    Returns:
        MemoryContext object if found, None otherwise
    """
    return storage.get_context(context_id)


def add_fragment_to_context(storage: StorageManager, context_id: str, fragment_id: str) -> bool:
    """Add a fragment to a context.
    
    Args:
        storage: Storage manager instance
        context_id: ID of the context
        fragment_id: ID of the fragment to add
        
    Returns:
        True if the fragment was added successfully
    """
    try:
        # Get current context
        context = storage.get_context(context_id)
        if not context:
            logger.error(f"Context {context_id} not found in add_fragment_to_context")
            return False
        
        # Add fragment if not already in list
        if fragment_id not in context.fragment_ids:
            context.fragment_ids.append(fragment_id)
            
            # Update context in storage
            success = storage.update_context_fragments(context_id, context.fragment_ids)
            if success:
                logger.info(f"Added fragment {fragment_id} to context {context_id}")
            else:
                logger.error(f"storage.update_context_fragments failed for context {context_id}")
            return success
        else:
            logger.info(f"Fragment {fragment_id} already in context {context_id}, no action needed.")
            return True
            
    except Exception as e:
        logger.error(f"Failed to add fragment to context: {e}", exc_info=True)
        return False


# Export functions
__all__ = [
    "create_context",
    "get_context",
    "add_fragment_to_context"
]
