"""
Simplified natural language MCP handlers.
The Cognitive Engine that interprets user intent and manages memory operations.
"""

import uuid
from typing import Any, Dict, List, Optional, Union

from src.logging_config import get_logger

logger = get_logger('memoire.mcp.cognitive_engine')


class CognitiveEngine:
    """
    The cognitive engine that interprets natural language input and manages memory.
    """

    def __init__(self, server):
        self.server = server
        logger.info("CognitiveEngine initialized")

    async def remember(self, content: str, project_id: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Store information in semantic memory using the enhanced intelligent workflow.
        """
        if not self.server.is_ready():
            logger.error("Cannot remember: server is not ready.")
            raise RuntimeError("Services not ready")

        try:
            # --- Input Validation ---
            if not self._is_valid_uuid(project_id):
                return {"success": False, "error": f"Invalid format for project_id: '{project_id}'. Must be a valid UUID."}
            
            if not self.server.memory.get_project(project_id):
                return {"success": False, "error": f"Project with ID '{project_id}' not found."}

            # --- End Validation ---

            result = await self.server.middleware.curate_and_chunk(content, project_id)

            response = {
                "success": True,
                "message": f"Intelligent ingestion completed. Created: {len(result.get('created_fragment_ids', [])) + len(result.get('created_context_ids', []))}, Deleted: {len(result.get('deleted_ids', []))}.",
                "details": result
            }
            return response

        except Exception as e:
            logger.error(f"Error in remember workflow: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to store memory due to an internal error."
            }

    async def recall(self, query: str, project_ids: Optional[Union[str, List[str]]] = None, focus: Optional[str] = None, raw_fragments: bool = False) -> Dict[str, Any]:
        """
        Search memory and return a synthesized, coherent response.
        """
        if not self.server.is_ready():
            logger.error("Cannot recall: server is not ready.")
            raise RuntimeError("Services not ready")

        try:
            validated_project_ids = None
            if project_ids:
                ids_to_check = [project_ids] if isinstance(project_ids, str) else project_ids
                all_projects = self.server.memory.list_projects()
                valid_id_set = {p.id for p in all_projects}
                
                validated_project_ids = [pid for pid in ids_to_check if pid in valid_id_set]
                
                if not validated_project_ids:
                    return {"success": False, "error": "No valid project IDs provided.", "message": "Recall requires at least one valid project_id."}

            result = await self.server.middleware.process_recall(query, validated_project_ids, focus, raw_fragments)
            return result
        except Exception as e:
            logger.error(f"Error in recall: {e}", exc_info=True)
            return {"success": False, "error": str(e), "message": "Failed to recall memories"}

    def _is_valid_uuid(self, uuid_string: str) -> bool:
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    async def create_project(self, name: str, description: str) -> Optional[str]:
        """Create a new project via the memory service."""
        result = await self.server.memory.create_project(name, description)
        return result

    async def list_projects(self) -> List[Dict[str, str]]:
        """List all projects via the memory service."""
        try:
            projects = self.server.memory.list_projects()
            project_list = [{ "id": p.id, "name": p.name, "description": p.description } for p in projects]
            return project_list
        except Exception as e:
            logger.error(f"Error in list_projects: {e}", exc_info=True)
            return []

    async def get_project_summary(self, project_id: str) -> Optional[Dict[str, int]]:
        """Get a summary of counts for a project."""
        return self.server.memory.get_project_summary(project_id)

    async def list_contexts(self, project_id: str) -> List[Dict[str, Any]]:
        """List all contexts for a given project ID."""
        contexts = self.server.memory.list_contexts_by_project(project_id)
        return [{k: v for k, v in c.dict().items() if k != 'fragment_ids'} for c in contexts]

    async def list_fragments_by_context(self, project_id: str, context_id: str) -> List[Dict[str, Any]]:
        """Get all fragments belonging to a specific context in a project."""
        fragments = self.server.memory.get_fragments_by_context(project_id, context_id)
        return [f.dict() for f in fragments]

    async def get_contexts_for_fragment(self, fragment_id: str) -> List[Dict[str, Any]]:
        """Get all contexts that contain a specific fragment."""
        contexts = self.server.memory.get_contexts_by_fragment(fragment_id)
        return [{k: v for k, v in c.dict().items() if k != 'fragment_ids'} for c in contexts]

    async def delete_fragment(self, fragment_id: str) -> bool:
        """Delete a fragment by its ID."""
        return self.server.memory.delete_fragment(fragment_id)

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project by its ID."""
        return self.server.memory.delete_project(project_id)

    async def delete_context(self, project_id: str, context_id: str) -> bool:
        """Delete a context by its ID within a project."""
        return self.server.memory.delete_context(project_id, context_id)

    # ==================== TASK MANAGEMENT ====================

    async def create_task(self, project_id: str, title: str, description: str = "") -> Optional[str]:
        """Create a new task."""
        return self.server.memory.create_task(project_id, title, description)

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by its ID."""
        task = self.server.memory.get_task(task_id)
        return task.model_dump(mode='json') if task else None

    async def list_tasks(self, project_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks for a project."""
        tasks = self.server.memory.list_tasks(project_id, status)
        return [t.model_dump(mode='json') for t in tasks]

    async def update_task(self, task_id: str, title: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None) -> bool:
        """Update a task."""
        return self.server.memory.update_task(task_id, title, description, status)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        return self.server.memory.delete_task(task_id)
