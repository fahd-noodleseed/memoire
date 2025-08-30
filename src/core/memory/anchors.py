"""
Anchor operations for Memoire memory system.

Handles cognitive anchors - important reference points for navigation and recall.
"""

# TODO: Implement advanced anchor management functions:
# - access_anchor (for tracking usage)
# - list_anchors (with filters)
# - get_high_priority_anchors
# - update_anchor
# - delete_anchor
# - add_fragment_to_anchor
# - add_context_to_anchor

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from src.logging_config import get_logger
from ...models import CognitiveAnchor
from ..storage import StorageManager

logger = get_logger('memoire.mcp.memory')


def create_anchor(storage: StorageManager, project_id: str, title: str,
                 description: str = "", priority: str = "medium",
                 fragment_ids: List[str] = None, context_ids: List[str] = None,
                 tags: List[str] = None, custom_fields: Dict[str, Any] = None) -> str:
    """Create a new cognitive anchor.
    
    Args:
        storage: Storage manager instance
        project_id: ID of the project this anchor belongs to
        title: Title of the anchor
        description: Description of the anchor
        priority: Priority level ("low", "medium", "high", "critical")
        fragment_ids: List of fragment IDs this anchor references
        context_ids: List of context IDs this anchor references
        tags: List of tags for the anchor
        custom_fields: Additional metadata fields
        
    Returns:
        Anchor ID of the created anchor
    """
    if fragment_ids is None: fragment_ids = []
    if context_ids is None: context_ids = []
    if tags is None: tags = []
    if custom_fields is None: custom_fields = {}
    
    anchor_id = str(uuid.uuid4())
    anchor = CognitiveAnchor(
        id=anchor_id,
        project_id=project_id,
        title=title,
        description=description,
        priority=priority,
        fragment_ids=fragment_ids,
        context_ids=context_ids,
        tags=tags,
        custom_fields=custom_fields,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        last_accessed=datetime.now()
    )

    stored_id = storage.create_anchor(anchor)
    
    logger.info(f"Created anchor: {title} ({stored_id})")
    return stored_id


def get_anchor(storage: StorageManager, anchor_id: str) -> Optional[CognitiveAnchor]:
    """Get anchor by ID.
    
    Args:
        storage: Storage manager instance
        anchor_id: ID of the anchor to retrieve
        
    Returns:
        CognitiveAnchor object if found, None otherwise
    """
    anchor = storage.get_anchor(anchor_id)
    return anchor


# Export functions
__all__ = [
    "create_anchor",
    "get_anchor"
]
