"""
Health and maintenance operations for Memoire memory system.

Provides health checks, maintenance operations, and system monitoring.
"""

# TODO: Implement advanced maintenance functions:
# - optimize_storage (SQLite VACUUM, Qdrant optimization)
# - backup_project
# - restore_project
# - validate_data_integrity

from typing import Dict, Any

from src.logging_config import get_logger
from ..storage import StorageManager
from ..embedding import EmbeddingService

logger = get_logger('memoire.mcp.memory')


def health_check(storage: StorageManager, embedding_service: EmbeddingService,
                default_project_id: str = None) -> Dict[str, Any]:
    """Check health of memory service and dependencies.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        default_project_id: Default project ID if available
        
    Returns:
        Dictionary with health status of all components
    """
    health = {
        "memory_service": True,
        "embedding_service": True,
        "storage": storage.health_check(),
        "default_project": default_project_id,
        "cache_stats": embedding_service.get_cache_stats()
    }
    return health


def cleanup_old_cache(embedding_service: EmbeddingService) -> Dict[str, Any]:
    """Clean up old cache entries.
    
    Args:
        embedding_service: Embedding service instance
        
    Returns:
        Dictionary with cleanup results
    """
    # Get stats before cleanup
    before_stats = embedding_service.get_cache_stats()
    
    # Perform cleanup
    removed_entries = embedding_service.cleanup_cache()
    
    # Get stats after cleanup
    after_stats = embedding_service.get_cache_stats()
    
    logger.info(f"Cache cleanup: {removed_entries} expired entries removed")
    
    results = {
        "removed_entries": removed_entries,
        "before_stats": before_stats,
        "after_stats": after_stats
    }
    return results


def clear_all_cache(embedding_service: EmbeddingService) -> Dict[str, Any]:
    """Clear all cache entries.
    
    Args:
        embedding_service: Embedding service instance
        
    Returns:
        Dictionary with clear results
    """
    # Get stats before clearing
    before_stats = embedding_service.get_cache_stats()
    
    # Clear cache
    embedding_service.clear_cache()
    
    # Get stats after clearing
    after_stats = embedding_service.get_cache_stats()
    
    logger.info("All cache entries cleared")
    
    results = {
        "before_stats": before_stats,
        "after_stats": after_stats
    }
    return results


def get_system_metrics(storage: StorageManager, embedding_service: EmbeddingService) -> Dict[str, Any]:
    """Get comprehensive system metrics.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        
    Returns:
        Dictionary with system metrics
    """
    metrics = {
        "storage_health": storage.health_check(),
        "cache_stats": embedding_service.get_cache_stats(),
        "embedding_provider": embedding_service.provider.__class__.__name__,
        "embedding_model": embedding_service.model,
        "embedding_dimension": embedding_service.dimension
    }
    return metrics


def maintenance_report(storage: StorageManager, embedding_service: EmbeddingService,
                      project_id: str = None) -> Dict[str, Any]:
    """Generate a comprehensive maintenance report.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        project_id: Optional project ID to focus on
        
    Returns:
        Dictionary with maintenance report
    """
    report = {
        "system_health": health_check(storage, embedding_service),
        "system_metrics": get_system_metrics(storage, embedding_service),
        "recommendations": []
    }
    
    # Add project-specific stats if requested
    if project_id:
        try:
            report["project_stats"] = storage.get_stats(project_id)
        except Exception as e:
            logger.error(f"Failed to get project stats for {project_id}: {e}", exc_info=True)
            report["project_stats"] = {"error": str(e)}
    
    # Generate basic recommendations
    cache_stats = embedding_service.get_cache_stats()
    if cache_stats.get("hit_rate", 0) < 0.5:
        recommendation = "Cache hit rate is low - consider reviewing usage patterns"
        report["recommendations"].append(recommendation)

    return report


# Export functions
__all__ = [
    "health_check",
    "cleanup_old_cache",
    "clear_all_cache",
    "get_system_metrics",
    "maintenance_report"
]
