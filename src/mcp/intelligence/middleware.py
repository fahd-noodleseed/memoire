"""
Intelligent Middleware - Main orchestrator for cognitive processing.

Coordinates chunking, contextualization, synthesis, and curation.
Maintains the same interface as the original but delegates to specialized modules.
"""

import os
from typing import Dict, Any, List, Optional, Union

from src.logging_config import get_logger

from .chunking import SemanticChunker, ContextualChunker
from .contextualization import EmergentContextualizer
from .synthesis import MemorySynthesizer
from .ingestion_curator import IngestionCurator

logger = get_logger('memoire.mcp.intelligence')


class IntelligentMiddleware:
    """
    Main orchestrator for cognitive processing in Memoire.
    """
    
    def __init__(self, memory_service):
        self.memory = memory_service
        
        from dotenv import load_dotenv
        load_dotenv()
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY")
        
        try:
            from google import genai
            self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            logger.info("Gemini 2.5 Flash client initialized")
        except ImportError:
            logger.error("google-genai package not found")
            raise ImportError("google-genai package required: pip install google-genai")
        
        # Get config instance
        from src.config import config
        self.config = config
        
        self.ingestion_curator = IngestionCurator(self.gemini_client, memory_service)
        self.synthesizer = MemorySynthesizer(self.gemini_client, memory_service=memory_service)
        logger.info("Intelligence modules initialized")

    async def curate_and_chunk(self, content: str, project_id: str) -> Dict[str, Any]:
        """Public method to expose the ingestion curator's functionality."""
        result = await self.ingestion_curator.curate_and_chunk(content, project_id)
        return result
    
    async def process_recall(self, query: str, project_ids: Optional[Union[str, List[str]]] = None, focus: Optional[str] = None, raw_fragments: bool = False) -> Dict[str, Any]:
        """Process recall with context awareness and optional synthesis."""
        from ...models import SearchOptions
        
        # search_memory now handles project_ids directly and returns grouped results
        search_results_grouped = await self.memory.search_memory(query, project_ids)

        # Check if any results were found across all projects/contexts
        found_any_results = any(
            any(context_results for context_results in project_results.values())
            for project_results in search_results_grouped.values()
        )

        if not found_any_results:
            logger.info("No information found for query, returning empty response.")
            return {"success": True, "response": "No information found."}
        
        if raw_fragments:
            # Return raw fragments, which are already grouped by project and context
            # The structure is: { project_id: { context_id: [fragment_dict, ...], ... }, ... }
            
            # Convert SearchResult objects to dictionaries for raw output
            raw_output = {}
            for project_id, contexts_data in search_results_grouped.items():
                raw_output[project_id] = {}
                for context_id, search_results_list in contexts_data.items():
                    raw_output[project_id][context_id] = [sr.fragment.model_dump(mode='json') for sr in search_results_list]
            
            response = {
                "success": True, 
                "response": "Raw fragments retrieved successfully.", 
                "grouped_fragments": raw_output
            }
            return response

        # Synthesis logic (will receive grouped data in Phase 3.5)
        synthesis = await self.synthesizer.synthesize_contextual(query, search_results_grouped) # Pass grouped data
        response = {"success": True, **synthesis}
        return response