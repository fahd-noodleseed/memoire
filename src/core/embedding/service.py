"""
Main embedding service that orchestrates providers and caching.

This is the main interface that other parts of the system use.
"""

import asyncio
from typing import List, Optional, Dict, Any

from src.logging_config import get_logger
from .cache import EmbeddingCache
from .providers import EmbeddingProvider, GeminiProvider
from ...config import config

logger = get_logger('memoire.mcp.embedding')


class EmbeddingService:
    """Main service for generating semantic embeddings."""
    
    def __init__(self, 
                 provider: Optional[EmbeddingProvider] = None,
                 cache_ttl_hours: int = None):
        """Initialize embedding service.
        
        Args:
            provider: Embedding provider to use (defaults to GeminiProvider)
            cache_ttl_hours: Cache time-to-live in hours
        """
        # Get config values if not provided
        
        if cache_ttl_hours is None:
            cache_ttl_hours = config.get("embedding.cache_ttl_hours", 24)
            
        self.provider = provider or GeminiProvider()
        self.cache = EmbeddingCache(ttl_hours=cache_ttl_hours)
        
        logger.info(f"EmbeddingService initialized with {self.provider.__class__.__name__}")

    
    @property
    def dimension(self) -> int:
        """Get the dimension of embeddings produced by the current provider."""
        return self.provider.get_dimension()
    
    @property
    def model(self) -> str:
        """Get the model name used by the current provider."""
        return self.provider.get_model_name()
    
    async def generate_embedding(self, text: str, task_type: str = None) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            task_type: The task type for the embedding (e.g., 'RETRIEVAL_DOCUMENT')
            
        Returns:
            Embedding vector
            
        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        if not text or not text.strip():
            logger.error("generate_embedding called with empty text")
            raise ValueError("Text cannot be empty")
        
        # Use a modified cache key if task_type is specified
        # The cache_key should be generated internally by the cache itself
        cached_embedding = self.cache.get(text, self.model) # Pass text and model separately
        if cached_embedding is not None:
            logger.debug("Cache hit for text")
            return cached_embedding
        
        logger.debug("Cache miss, generating new embedding")
        # Generate new embedding
        embedding = await self.provider.generate_embedding(text, task_type=task_type)

        # Cache the result
        self.cache.set(text, self.model, embedding) # Pass text, model, and embedding separately
        logger.debug("Cached new embedding")

        return embedding
    
    async def batch_embeddings(self, texts: List[str], 
                             batch_size: int = None,
                             delay_seconds: float = None) -> List[List[float]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of requests to process before adding delay
            delay_seconds: Delay between batches to respect rate limits
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            logger.warning("batch_embeddings called with empty list")
            return []
            
        # Get config values if not provided
        
        if batch_size is None:
            batch_size = config.get("embedding.batch_size", 10)
        if delay_seconds is None:
            delay_seconds = config.get("embedding.delay_seconds", 0.1)

        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        embeddings = []
        
        for i, text in enumerate(texts):
            try:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
                
                # Add delay between batches to respect rate limits
                if i > 0 and i % batch_size == 0:
                    logger.debug(f"Batch limit reached, sleeping for {delay_seconds}s")
                    await asyncio.sleep(delay_seconds)
                    
            except Exception as e:
                logger.error(f"Failed to generate embedding for text {i}: {e}")
                # Use zero vector as fallback
                logger.warning(f"Using zero vector as fallback for text {i}")
                embeddings.append([0.0] * self.dimension)
        
        logger.info(f"Successfully generated {len(embeddings)} embeddings")
        return embeddings
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")

    def cleanup_cache(self) -> int:
        """Clean up expired cache entries.
        
        Returns:
            Number of entries removed
        """
        removed_count = self.cache.cleanup_expired()
        logger.info(f"Cleaned up {removed_count} expired cache entries")
        return removed_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache and service statistics
        """
        cache_stats = self.cache.get_stats()
        
        stats = {
            **cache_stats,
            "provider": self.provider.__class__.__name__,
            "model": self.model,
            "dimension": self.dimension
        }
        return stats
