import json
from typing import Dict, Any, List
from collections import defaultdict

from src.logging_config import get_logger

from google import genai
from google.genai.types import GenerateContentConfig

from ...models import SearchResult, SearchOptions, MemoryContext
from ...core.memory import MemoryService
from ...config import config

logger = get_logger('memoire.mcp.intelligence')


class IngestionCurator:
    """Handles intelligent curation during the ingestion process."""

    def __init__(self, gemini_client: genai.Client, memory_service: MemoryService):
        self.gemini_client = gemini_client
        self.memory_service = memory_service
        self.light_model = config.get("processing.light_model", "gemini-2.5-flash-lite")
        logger.info(f"IngestionCurator initialized with light_model: {self.light_model}")

    async def curate_and_chunk(self, content: str, project_id: str) -> Dict[str, Any]:
        """
        Orchestrates the entire intelligent ingestion process.
        1. Searches for relevant existing fragments and contexts.
        2. Uses an LLM to decide which fragments/contexts to create and which fragments to delete.
        3. Applies the decision to the memory store.
        """
        logger.info(f"Starting intelligent ingestion for project {project_id}")

        # Step 1: Embed the entire content for similarity search and find relevant fragments
        try:
            embedding = await self.memory_service.embedding.generate_embedding(
                content, task_type='SEMANTIC_SIMILARITY'
            )
            search_options = SearchOptions(
                project_id=project_id,
                max_results=config.get("search.max_results", 50),
                similarity_threshold=config.get("intelligence.curation_search_threshold", 0.4)
            )
            relevant_fragments = await self.memory_service.search_memory_by_vector(embedding, search_options)
        except Exception as e:
            logger.error(f"Failed to search for relevant fragments during curation: {e}", exc_info=True)
            relevant_fragments = []

        # Step 1b: Fetch existing contexts
        try:
            existing_contexts = self.memory_service.list_contexts_by_project(project_id)
        except Exception as e:
            logger.error(f"Failed to list contexts for project {project_id}: {e}", exc_info=True)
            existing_contexts = []

        # Step 2: Get curation and chunking decision from the light model
        decision = await self._get_curation_decision(content, relevant_fragments, existing_contexts)

        # Step 3: Apply the decision
        result = await self._apply_curation_decision(decision, project_id, existing_contexts)
        
        logger.info(f"Intelligent ingestion completed. Created fragments: {len(result.get('created_fragment_ids', []))}, Created contexts: {len(result.get('created_context_ids', []))}, Deleted fragments: {len(result.get('deleted_ids', []))}")
        return result

    async def _get_curation_decision(self, new_content: str, existing_fragments: List[SearchResult], existing_contexts: List[MemoryContext]) -> Dict[str, Any]:
        """
        Uses the light model with a defined schema to decide which fragments and contexts to create, and which fragments to delete.
        """
        prompt = self._build_curation_prompt_with_context(new_content, existing_fragments, existing_contexts)

        response_schema = {
            "type": "object",
            "properties": {
                "contexts_to_create": {
                    "type": "array",
                    "description": "Lista de NUEVOS contextos que deben ser creados. Solo si ninguno de los existentes es adecuado.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Nombre único y descriptivo para el nuevo contexto.", "minLength": 1},
                            "description": {"type": "string", "description": "Descripción clara del propósito de este nuevo contexto.", "minLength": 1}
                        },
                        "required": ["name", "description"]
                    }
                },
                "fragments_to_create": {
                    "type": "array",
                    "description": "Lista de nuevos fragmentos de información a crear.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "El contenido de texto del fragmento.", "minLength": 1},
                            "context_name": {"type": "string", "description": "El nombre del contexto (existente o nuevo) al que este fragmento pertenece.", "minLength": 1}
                        },
                        "required": ["content", "context_name"]
                    }
                },
                "ids_to_delete": {
                    "type": "array",
                    "description": "Lista de IDs de fragmentos existentes que se vuelven redundantes.",
                    "items": {"type": "string", "minLength": 1}
                }
            },
            "required": ["fragments_to_create", "ids_to_delete"]
        }

        config = GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=response_schema
        )
        
        try:
            response = self.gemini_client.models.generate_content(
                model=self.light_model,
                contents=prompt,
                config=config
            )
            decision = json.loads(response.text)
            # Ensure all required keys are present, even if empty
            decision.setdefault('contexts_to_create', [])
            decision.setdefault('fragments_to_create', [])
            decision.setdefault('ids_to_delete', [])
            return decision
        except Exception as e:
            logger.error(f"Failed to get structured curation decision from LLM: {e}", exc_info=True)
            raise e

    def _build_curation_prompt_with_context(self, new_content: str, existing_fragments: List[SearchResult], existing_contexts: List[MemoryContext]) -> str:
        """Builds the prompt for the LLM curation task, including existing contexts."""
        # This is a pure function, extensive logging is less critical here.
        # A single debug log at the start can be useful.
        fragments_text = ""
        for i, res in enumerate(existing_fragments):
            fragments_text += f"\n--- FRAGMENTO EXISTENTE {i+1} (ID: {res.fragment.id}) ---"
            fragments_text += f"Contenido: {res.fragment.content}\n"

        contexts_text = "No hay contextos existentes."
        if existing_contexts:
            contexts_text = "\n".join([
                f"- {ctx.name}: {ctx.description}" for ctx in existing_contexts
            ])

        return f"""
        Eres un asistente experto en organización de memoria semántica. Tu tarea es analizar nuevo contenido y decidir cómo integrarlo de la forma más coherente y fiel posible en una memoria existente.

        NUEVO CONTENIDO A PROCESAR:
        {new_content}
        ---
        CONTEXTOS YA DISPONIBLES EN EL PROYECTO (puedes usar uno de estos o crear uno nuevo):
        {contexts_text}
        ---
        FRAGMENTOS EXISTENTES SIMILARES (para evitar duplicados y guiar la edición):
        {fragments_text if fragments_text else "No se encontraron fragmentos existentes relevantes."} 
        ---
        CRITERIOS DE FRAGMENTACIÓN:
        1.  **Integridad Semántica**: Cada fragmento debe ser una idea completa que tenga sentido por sí misma.
        2.  **Fidelidad al Original**: NO RESUMAS NI ALTERES el significado original. El contenido de los fragmentos, al unirse, debe ser idéntico al input. Las ediciones son solo para segmentar, no para parafrasear o modificar.
        3.  **División por Contexto**: Usa los cambios de tema, sujeto o pasos lógicos como puntos de división naturales.
        4.  **Autocontención**: Un fragmento no debe depender del anterior o siguiente para ser comprendido.
        5.  **Sin Límites Artificiales**: La longitud de un fragmento la determina su coherencia semántica, no un número de palabras.
        ---
        INSTRUCCIONES DE EJECUCIÓN:
        1.  Aplica los `CRITERIOS DE FRAGMENTACIÓN` al `NUEVO CONTENIDO` para decidir los nuevos `fragments_to_create`.
        2.  Asigna a cada nuevo fragmento un `context_name` de los `CONTEXTOS YA DISPONIBLES` o define uno nuevo en `contexts_to_create` si es necesario. Un buen contexto es reutilizable y describe un tema claro.
        3.  Si el `NUEVO CONTENIDO` actualiza o reemplaza `FRAGMENTOS EXISTENTES`, añade sus IDs a `ids_to_delete` y crea los nuevos fragmentos corregidos. El objetivo es que la memoria evolucione sin redundancia.
        4.  Tu respuesta DEBE seguir el esquema JSON proporcionado. No incluyas explicaciones fuera del JSON.
        """

    async def _apply_curation_decision(self, decision: Dict[str, Any], project_id: str, existing_contexts: List[MemoryContext]) -> Dict[str, Any]:
        """Applies the structured curation decision from the LLM to the memory."""
        ids_to_delete = decision.get("ids_to_delete", [])
        contexts_to_create = decision.get("contexts_to_create", [])
        fragments_to_create = decision.get("fragments_to_create", [])
        
        created_fragment_ids = []
        created_context_ids = []
        
        # 1. Delete old fragments
        if ids_to_delete:
            logger.info(f"Deleting {len(ids_to_delete)} fragments due to curation: {ids_to_delete}")
            await self.memory_service.delete_fragments(ids_to_delete, project_id)

        # 2. Create new contexts
        context_map = {ctx.name: ctx.id for ctx in existing_contexts}
        if contexts_to_create:
            for context_data in contexts_to_create:
                name = context_data.get("name")
                desc = context_data.get("description")
                if name and desc and name not in context_map:
                    try:
                        new_context_id = self.memory_service.create_context(
                            project_id=project_id,
                            name=name,
                            description=desc
                        )
                        context_map[name] = new_context_id
                        created_context_ids.append(new_context_id)
                        logger.info(f"Created new context '{name}' ({new_context_id})")
                    except Exception as e:
                        logger.error(f"Failed to create new context '{name}': {e}", exc_info=True)

        # 3. Create new fragments and group them by context
        fragments_by_context = defaultdict(list)
        if fragments_to_create:
            for fragment_data in fragments_to_create:
                if not isinstance(fragment_data, dict):
                    logger.warning(f"Skipping fragment creation due to invalid format: {fragment_data}")
                    continue
                content = fragment_data.get("content")
                context_name = fragment_data.get("context_name")
                
                if not (content and content.strip() and context_name):
                    logger.warning(f"Skipping fragment creation due to missing content or context name: {fragment_data}")
                    continue

                context_id = context_map.get(context_name)
                if not context_id:
                    logger.warning(f"Could not find or create context '{context_name}'. Storing in 'general'.")
                    if 'general' not in context_map:
                        general_id = self.memory_service.create_context(project_id, "general", "Contenedor para fragmentos sin un contexto específico.")
                        context_map['general'] = general_id
                    context_id = context_map['general']

                try:
                    new_id = await self.memory_service.store_fragment(
                        project_id=project_id, 
                        content=content, 
                        source="curated_ingestion",
                        context_ids=[context_id]
                    )
                    created_fragment_ids.append(new_id)
                    fragments_by_context[context_id].append(new_id)
                except Exception as e:
                    logger.error(f"Failed to store curated fragment: {e}", exc_info=True)

        # 4. Update contexts with their new fragments
        for context_id, new_fragment_ids in fragments_by_context.items():
            if not new_fragment_ids:
                continue
            try:
                # It's better to get the existing fragments and append, rather than overwrite.
                # However, the current logic assumes we are creating from scratch or replacing.
                # For now, we will overwrite. A more robust solution would be to merge.
                context = self.memory_service.get_context(context_id)
                if context:
                    all_fragment_ids = list(set(context.fragment_ids + new_fragment_ids))
                    self.memory_service.storage.update_context_fragments(context_id, all_fragment_ids)
                    logger.info(f"Updated context {context_id} with {len(new_fragment_ids)} new fragments.")
            except Exception as e:
                logger.error(f"Failed to update context {context_id} with new fragments: {e}", exc_info=True)

        result = {
            "created_fragment_ids": created_fragment_ids, 
            "created_context_ids": created_context_ids,
            "deleted_ids": ids_to_delete
        }
        return result
