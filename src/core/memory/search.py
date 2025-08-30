"""
Search operations for Memoire memory system.

Handles semantic search, similarity detection, and intelligent fragment discovery.
"""

from typing import List, Optional, Dict, Any, Union

from src.logging_config import get_logger
from ...models import SearchOptions, SearchResult, MemoryFragment
from ..storage import StorageManager
from ..embedding import EmbeddingService

logger = get_logger('memoire.mcp.memory')


async def search_memory(storage: StorageManager, embedding_service: EmbeddingService,
                       query: str, options: SearchOptions = None,
                       project_ids: Optional[Union[str, List[str]]] = None,
                       default_project_id: str = None) -> Dict[str, Dict[str, List[SearchResult]]]:
    """
    Search memory using semantic similarity and filters, with mandatory grouping.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        query: Search query text
        options: Search configuration options
        project_ids: Project(s) to search in (single ID, list of IDs, or None for global search).
        default_project_id: Default project ID if none specified in options.
        
    Returns:
        A dictionary grouped by project_id, then by context_id, containing lists of SearchResult objects.
        Example: { "project_id_1": { "context_id_A": [sr1, sr2], "context_id_B": [sr3] }, "project_id_2": { ... } }
    
    Raises:
        ValueError: If no project is specified and no default is available.
    """
    if options is None:
        options = SearchOptions()
    
    # Resolve target project IDs
    target_project_ids: List[str] = []
    if project_ids is None:
        # Global search: get all projects
        all_projects = storage.list_projects()
        target_project_ids = [p.id for p in all_projects]
    elif isinstance(project_ids, str):
        target_project_ids = [project_ids]
    else: # It's a list of strings
        target_project_ids = project_ids
    
    if not target_project_ids:
        if default_project_id:
            target_project_ids = [default_project_id]
        else:
            logger.error("Search failed: No project_ids specified and no default_project_id available.")
            raise ValueError("No project specified and no default project available for search.")
    
    # Generate query embedding
    query_embedding = await embedding_service.generate_embedding(query)

    # Perform search and group results
    grouped_results: Dict[str, Dict[str, List[SearchResult]]] = {}
    
    for p_id in target_project_ids:
        logger.debug(f"Searching in project_id: {p_id}")
        # Ensure options are specific to the current project for the search call
        current_options = options.copy(update={'project_id': p_id})
        
        # Perform search for the current project
        project_search_results = storage.search_fragments(query_embedding, current_options)
        logger.debug(f"storage.search_fragments returned {len(project_search_results)} results for project {p_id}")

        if project_search_results:
            grouped_results[p_id] = {}
            # Group by context within the project
            for sr in project_search_results:
                context_id = "unassigned" # Default context if fragment has none
                if sr.fragment.context_ids:
                    # Use the first context ID for grouping, or a more sophisticated logic if needed
                    context_id = sr.fragment.context_ids[0]
                
                if context_id not in grouped_results[p_id]:
                    grouped_results[p_id][context_id] = []
                grouped_results[p_id][context_id].append(sr)
    
    logger.info(f"Search returned grouped results for query: {query[:50]}... across {len(target_project_ids)} projects.")
    return grouped_results


async def search_memory_by_vector(storage: StorageManager, query_vector: List[float], options: SearchOptions) -> List[SearchResult]:
    """Search memory using a pre-computed vector and filters."""
    if not options.project_id:
        logger.error("Vector search failed: No project_id specified in options.")
        raise ValueError("No project specified for vector search")

    results = storage.search_fragments(query_vector, options)
    logger.info(f"Vector search returned {len(results)} results.")
    return results


async def find_similar_fragments(storage: StorageManager, embedding_service: EmbeddingService,
                                fragment_id: str, limit: int = 5) -> List[SearchResult]:
    """Find fragments similar to a given fragment.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        fragment_id: ID of the reference fragment
        limit: Maximum number of similar fragments to return
        
    Returns:
        List of SearchResult objects for similar fragments
        
    Raises:
        ValueError: If the reference fragment is not found
    """
    fragment = storage.get_fragment(fragment_id)
    if not fragment:
        logger.error(f"Fragment not found in find_similar_fragments: {fragment_id}")
        raise ValueError(f"Fragment not found: {fragment_id}")
    
    # Use the fragment's content as the search query
    options = SearchOptions(
        project_id=fragment.project_id,
        max_results=limit + 1,  # +1 because we'll filter out the original
        similarity_threshold=0.3  # Lower threshold for similarity search
    )

    # This returns grouped results, so we need to flatten it.
    grouped_results = await search_memory(
        storage, embedding_service,
        fragment.content, options
    )
    
    # Flatten the grouped results into a single list of SearchResult
    results = []
    for project_group in grouped_results.values():
        for context_group in project_group.values():
            results.extend(context_group)

    # Filter out the original fragment
    similar_results = [r for r in results if r.fragment.id != fragment_id]

    return similar_results[:limit]


async def search_by_category(storage: StorageManager, embedding_service: EmbeddingService,
                            project_id: str, category: str,
                            query: str = "", limit: int = 20) -> List[SearchResult]:
    """Search fragments within a specific category.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        project_id: ID of the project to search in
        category: Category to filter by
        query: Optional semantic query (empty string for category-only search)
        limit: Maximum number of results to return
        
    Returns:
        List of SearchResult objects in the specified category
    """
    options = SearchOptions(
        project_id=project_id,
        max_results=limit,
        categories=[category],
        similarity_threshold=0.1 if query else 0.0  # Lower threshold for category search
    )
    
    # Use query if provided, otherwise use category name for semantic matching
    search_query = query if query else category

    # This returns grouped results, so we need to flatten it.
    grouped_results = await search_memory(storage, embedding_service, search_query, options)
    results = []
    for project_group in grouped_results.values():
        for context_group in project_group.values():
            results.extend(context_group)

    return results


async def search_by_tags(storage: StorageManager, embedding_service: EmbeddingService,
                        project_id: str, tags: List[str],
                        query: str = "", limit: int = 20) -> List[SearchResult]:
    """Search fragments with specific tags.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        project_id: ID of the project to search in
        tags: List of tags to filter by
        query: Optional semantic query
        limit: Maximum number of results to return
        
    Returns:
        List of SearchResult objects with the specified tags
    """
    options = SearchOptions(
        project_id=project_id,
        max_results=limit,
        tags=tags,
        similarity_threshold=0.1 if query else 0.0
    )
    
    # Use query if provided, otherwise use tags for semantic matching
    search_query = query if query else " ".join(tags)

    # This returns grouped results, so we need to flatten it.
    grouped_results = await search_memory(storage, embedding_service, search_query, options)
    results = []
    for project_group in grouped_results.values():
        for context_group in project_group.values():
            results.extend(context_group)

    return results


async def advanced_search(storage: StorageManager, embedding_service: EmbeddingService,
                         query: str, **filters) -> List[SearchResult]:
    """Perform advanced search with multiple filter options.
    
    Args:
        storage: Storage manager instance
        embedding_service: Embedding service instance
        query: Search query text
        **filters: Additional filter options (project_id, categories, tags, etc.)
        
    Returns:
        List of SearchResult objects matching the advanced criteria
    """
    options = SearchOptions(**filters)
    
    # This returns grouped results, so we need to flatten it.
    grouped_results = await search_memory(storage, embedding_service, query, options)
    results = []
    for project_group in grouped_results.values():
        for context_group in project_group.values():
            results.extend(context_group)

    return results


# Export functions
__all__ = [
    "search_memory",
    "search_memory_by_vector",
    "find_similar_fragments",
    "search_by_category", 
    "search_by_tags",
    "advanced_search"
]