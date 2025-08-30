"""
Intelligence layer for memoire.

This module contains the cognitive processing components that handle:
- Content analysis and chunking
- Emergent contextualization 
- Memory synthesis and curation
- Semantic organization
"""

from .middleware import IntelligentMiddleware
from .chunking import SemanticChunker, ContextualChunker
from .contextualization import EmergentContextualizer
from .synthesis import MemorySynthesizer
from .ingestion_curator import IngestionCurator # New import

__all__ = [
    "IntelligentMiddleware",
    "SemanticChunker", 
    "ContextualChunker",
    "EmergentContextualizer",
    "MemorySynthesizer",
    "IngestionCurator" # Updated
]
