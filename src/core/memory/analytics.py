"""
Analytics and insights for Memoire memory system.

Provides statistics, analytics, and intelligent insights about memory usage and patterns.
"""

# TODO: Implement advanced analytics functions:
# - find_knowledge_gaps
# - suggest_contexts
# - analyze_fragment_distribution
# - get_usage_patterns
# - find_orphaned_fragments
# - suggest_anchors
# - analyze_semantic_clusters
# - get_memory_health_score

from typing import Dict, Any, List

from src.logging_config import get_logger
from ..storage import StorageManager
from ..embedding import EmbeddingService

logger = get_logger('memoire.mcp.memory')


def get_project_stats(storage: StorageManager, embedding_service: EmbeddingService,
                     project_id: str) -> Dict[str, Any]:
    """Get comprehensive statistics for a project.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        project_id: ID of the project to analyze
        
    Returns:
        Dictionary containing various project statistics
    """
    stats = storage.get_stats(project_id)

    # Add memory service specific stats
    stats["embedding_cache"] = embedding_service.get_cache_stats()

    return stats


# Export functions
__all__ = [
    "get_project_stats"
]
