"""
Memory synthesis capabilities for coherent response generation.

Handles synthesis of memory fragments into coherent explanations and responses.
"""

import json
from typing import Dict, Any, List, Optional, Union

from src.logging_config import get_logger
from ...models import SearchResult

logger = get_logger('memoire.mcp.intelligence')


class MemorySynthesizer:
    """Handles synthesis of memory fragments into coherent responses."""
    
    def __init__(self, gemini_client, memory_service=None):
        self.gemini_client = gemini_client
        self.memory_service = memory_service # Added for access to project/context info
        
        # Hot-reloadable configuration
        from src.config import config
        self.config = config
        self.temperature = config.get("processing.temperature", 0.3)
        
        # Subscribe to config changes for hot reload
        config.add_observer(self._on_config_change)
        
        logger.info(f"MemorySynthesizer initialized with temperature: {self.temperature}")
        if memory_service:
            logger.debug(f"MemorySynthesizer received memory_service of type: {type(memory_service)}")

    def _on_config_change(self, new_config):
        """Handle configuration changes for hot reload."""
        try:
            old_temp = self.temperature
            self.temperature = new_config.get("processing", {}).get("temperature", 0.3)
            
            if old_temp != self.temperature:
                logger.info(f"Hot reload: Synthesis temperature updated {old_temp:.2f} → {self.temperature:.2f}")
                
        except Exception as e:
            logger.error(f"Error during config hot reload in MemorySynthesizer: {e}")

    def synthesize_legacy(self, query: str, fragments: List[SearchResult]) -> Dict[str, Any]:
        """
        Legacy synthesis method for backward compatibility.
        
        Maintains the same interface as the original intelligent_middleware.py
        """
        # Format fragments for analysis
        fragments_text = ""
        for i, fragment in enumerate(fragments, 1):
            fragments_text += f"\nFragment {i}:\n"
            fragments_text += f"Content: {fragment.fragment.content}\n"
            fragments_text += f"Category: {fragment.fragment.category}\n"
            fragments_text += f"Tags: {fragment.fragment.tags}\n"
            fragments_text += f"Similarity: {fragment.similarity:.3f}\n"
        
        # Create synthesis prompt (domain-agnostic)
        prompt = f"""You are a memory synthesis assistant. Your job is to organize and synthesize information, NOT to make decisions or solve problems.

QUERY: {query}

RETRIEVED FRAGMENTS:
{fragments_text}

SYNTHESIZE a coherent response that:
1. Directly addresses the query by organizing relevant information
2. Combines information from fragments into a unified view
3. Identifies relationships, patterns, and potential gaps
4. Maintains neutrality - organize info without making recommendations
5. Uses clear, domain-agnostic language suitable for any project type

RESPOND WITH JSON:
{{
    "synthesized_response": "A coherent explanation that organizes the retrieved information to address the query",
    "confidence": 0.8,
    "information_coverage": "complete|partial|sparse",
    "gaps": ["missing info 1", "missing info 2"],
    "patterns_identified": ["pattern 1", "pattern 2"],
    "fragments_relevance": {{'fragment_1': 'high', 'fragment_2': 'medium', 'fragment_3': 'low'}}
}}

Focus on synthesis and organization, not problem-solving."""

        try:
            # Use Gemini 2.5 Flash for synthesis
            model_name = self.config.get("processing.model", "gemini-2.5-flash-preview-05-20")
            response = self.gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": self.temperature}  # Use hot-reloadable temperature
            )
            
            synthesis_text = response.text.strip()

            # Extract JSON from response
            synthesis_text = self._extract_json(synthesis_text)
            synthesis = json.loads(synthesis_text)
            
            logger.info(f"Memory synthesis completed for query: {query[:50]}...")
            return synthesis
            
        except Exception as e:
            logger.error(f"Memory synthesis failed: {e}", exc_info=True)
            # Fallback synthesis
            fallback_response = {
                "synthesized_response": f"Found {len(fragments)} relevant fragments related to '{query}'. " +
                                    "Manual review recommended due to synthesis processing limitations.",
                "confidence": 0.3,
                "information_coverage": "partial",
                "gaps": ["synthesis processing error"],
                "patterns_identified": [],
                "fragments_relevance": {}
            }
            logger.warning("Returning fallback synthesis response")
            return fallback_response
    
    async def synthesize_contextual(self, query: str, grouped_results: Dict[str, Dict[str, List[SearchResult]]]) -> Dict[str, Any]:
        """
        Enhanced synthesis with context awareness, using pre-grouped results.
        
        Args:
            query: Search query
            grouped_results: Dictionary of SearchResult objects grouped by project and then by context.
            
        Returns:
            Synthesis result with context-aware insights
        """
        # Format fragments and contexts for the prompt
        formatted_content = ""
        all_contexts_info = {} # To store unique context descriptions

        for project_id, contexts_data in grouped_results.items():
            project = self.memory_service.get_project(project_id)
            project_name = project.name if project else project_id
            project_description = project.description if project else "No description available."

            formatted_content += f"\n--- PROJECT: {project_name} (ID: {project_id}) ---"
            formatted_content += f"\nDescription: {project_description}"

            for context_id, search_results_list in contexts_data.items():
                context = self.memory_service.get_context(context_id)
                context_name = context.name if context else context_id
                context_description = context.description if context else "No description available."

                # Store unique context info
                if context_id not in all_contexts_info:
                    all_contexts_info[context_id] = {"name": context_name, "description": context_description}

                formatted_content += f"\n---- CONTEXT: {context_name} (ID: {context_id}) ----"
                formatted_content += f"\nDescription: {context_description}"

                for i, sr in enumerate(search_results_list, 1):
                    formatted_content += f"Fragment {i} (Similarity: {sr.similarity:.3f}):\n"
                    formatted_content += f"Content: {sr.fragment.content}\n"
                    formatted_content += f"Category: {sr.fragment.category}\n"
                    formatted_content += f"Tags: {sr.fragment.tags}\n"
                    formatted_content += "\n"
        
        # Prepare relevant contexts info for the prompt
        context_info_for_prompt = ""
        if all_contexts_info:
            context_info_for_prompt = "\nRELEVANT CONTEXTS (with descriptions):\n"
            for ctx_id, ctx_data in all_contexts_info.items():
                context_info_for_prompt += f"- {ctx_data['name']} (ID: {ctx_id}): {ctx_data['description']}\n"
        
        prompt = f"""You are an advanced memory synthesis assistant. Your task is to answer a query using the provided information with absolute fidelity.

    QUERY: {query}

    RETRIEVED AND GROUPED FRAGMENTS:
    {formatted_content}
    {context_info_for_prompt}

    INSTRUCTIONS:
    1.  **Answer with Fidelity**: Construct a direct answer to the `QUERY` using ONLY the information from the `RETRIEVED AND GROUPED FRAGMENTS`.
    2.  **Do Not Alter**: Do not summarize, paraphrase, or add outside information. Preserve the original wording and data.
    3.  **Synthesize, Don't Hallucinate**: Combine the fragments into a coherent text. If the fragments do not contain the answer, state that the information is not available.
    4.  **Leverage Context**: Use the project and context descriptions to understand and structure the information.
    5.  **Output JSON**: Fill the `synthesized_response` field with your answer. Populate the other fields based on your analysis.

    RESPOND WITH JSON:
    {{
        "synthesized_response": "A coherent, context-aware explanation constructed directly from the provided fragments.",
        "confidence": 0.9,
        "information_coverage": "complete|partial|sparse",
        "gaps": ["list any specific information the query asked for that was not found in the fragments"],
        "patterns_identified": ["list any patterns or relationships you identified across fragments"],
        "context_insights": ["list any insights about how contexts relate to each other"],
        "fragments_relevance": {{'fragment_1_id': 'high', 'fragment_2_id': 'medium'}},
        "recommended_contexts": ["list any contexts the user might want to explore further"]
    }}"""

        try:
            model_name = self.config.get("processing.model", "gemini-2.5-flash-preview-05-20")
            response = self.gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"temperature": self.temperature}  # Use hot-reloadable temperature
            )
            
            synthesis_text = response.text.strip()
            synthesis_text = self._extract_json(synthesis_text)
            synthesis = json.loads(synthesis_text)
            
            # Add metadata about synthesis type
            synthesis["synthesis_type"] = "contextual"
            synthesis["projects_used"] = len(grouped_results)
            synthesis["contexts_used"] = len(all_contexts_info)
            
            logger.info(f"Contextual synthesis completed for query: {query[:50]}...")
            return synthesis
            
        except Exception as e:
            logger.error(f"Contextual synthesis failed: {e}", exc_info=True)
            logger.warning("Falling back to legacy synthesis due to error.")
            # Fallback to legacy synthesis
            # Need to flatten grouped_results for legacy synthesis
            flat_fragments = []
            for project_data in grouped_results.values():
                for context_data in project_data.values():
                    flat_fragments.extend(context_data)
            return self.synthesize_legacy(query, flat_fragments)
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from Gemini response."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            extracted = text[start:end].strip()
            return extracted
        elif "```" in text:
            start = text.find("```") + 3
            end = text.rfind("```")
            extracted = text[start:end].strip()
            return extracted
        return text
