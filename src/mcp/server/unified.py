"""
Unified MCP Server that receives pre-initialized shared services.
No service initialization - uses shared instances from main process.
"""

import asyncio
import json
import logging
from src.logging_config import get_logger
import os
import sys
from typing import Dict, Any, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp.types import Tool, TextContent

from ..intelligence import IntelligentMiddleware
from .cognitive_engine import CognitiveEngine

logger = get_logger('memoire.mcp.unified')


class UnifiedMemoireServer:
    """MCP server that uses shared services from main process."""
    
    def __init__(self, storage, embedding, memory):
        # Use shared services directly
        self.storage = storage
        self.embedding = embedding
        self.memory = memory
        self.middleware = None
        self.cognitive_engine = None
        
        # Create MCP server
        self.server = Server("memoire")
        
        logger.info("Unified MCP server initialized with shared services")

    async def initialize(self) -> bool:
        """Initialize middleware and cognitive engine with shared services."""
        logger.debug("Entering initialize")
        try:
            logger.debug("Initializing IntelligentMiddleware")
            self.middleware = IntelligentMiddleware(self.memory)
            
            logger.debug("Initializing CognitiveEngine")
            self.cognitive_engine = CognitiveEngine(self)
            
            logger.debug("Registering MCP handlers")
            await self._register_handlers()
            
            logger.info("✅ Unified MCP Server initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize unified MCP server: {e}", exc_info=True)
            return False
    
    async def _register_handlers(self):
        """Register MCP protocol handlers."""
        logger.debug("Entering _register_handlers")

        # Import all tools unconditionally to ensure they are in scope for handlers
        from src.app import restart_server
        from src.mcp.server.tools import (
            RestartServerTool, GetProjectSummaryTool, ListContextsTool,
            ListFragmentsByContextTool, GetContextsForFragmentTool, DeleteFragmentTool, 
            DeleteContextTool, DeleteProjectTool, CreateTaskTool, GetTaskTool, 
            ListTasksTool, UpdateTaskTool, DeleteTaskTool
        )

        # Check for system tools
        system_tools_enabled = os.getenv('MEMOIRE_ENABLE_SYSTEM_Tools') == 'true'
        if system_tools_enabled:
            logger.warning("System tools are enabled. This is not recommended for production.")

        # Register tools list handler
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Return available tools."""
            logger.debug("Executing handle_list_tools")
            
            base_tools = [
                Tool(
                    name="remember",
                    description="Store information in semantic memory with project segregation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "What to remember - facts, decisions, code, anything"
                            },
                            "project_id": {
                                "type": "string",
                                "description": "Project to store in (use 'default' for general memory)"
                            },
                            "context": {
                                "type": "string", 
                                "description": "Optional context about this memory"
                            }
                        },
                        "required": ["content", "project_id"]
                    }
                ),
                Tool(
                    name="recall",
                    description="Search memory and get synthesized response",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "What you want to know - natural language question"
                            },
                            "project_id": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Project(s) to search in (use 'default' for general memory, or an array of project IDs for multi-project search). If omitted, searches all projects."
                            },
                            "focus": {
                                "type": "string",
                                "description": "Optional focus area"
                            },
                            "raw_fragments": {
                                "type": "boolean",
                                "description": "If true, return raw fragment data instead of a synthesized response."
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="create_project",
                    description="Create a new memory project for domain segregation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Project name"
                            },
                            "description": {
                                "type": "string",
                                "description": "Project description"
                            }
                        },
                        "required": ["name", "description"]
                    }
                ),
                Tool(
                    name="list_projects",
                    description="List all available memory projects",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]

            # Add new tools from models
            new_tool_models = {
                "get_project_summary": GetProjectSummaryTool,
                "list_contexts": ListContextsTool,
                "list_fragments_by_context": ListFragmentsByContextTool,
                "get_contexts_for_fragment": GetContextsForFragmentTool,
                "delete_fragment": DeleteFragmentTool,
                "delete_context": DeleteContextTool,
                "delete_project": DeleteProjectTool,
                "create_task": CreateTaskTool,
                "get_task": GetTaskTool,
                "list_tasks": ListTasksTool,
                "update_task": UpdateTaskTool,
                "delete_task": DeleteTaskTool
            }

            for name, model in new_tool_models.items():
                schema = model.model_json_schema()
                base_tools.append(Tool(
                    name=name,
                    description=schema.get('description', ''),
                    inputSchema={
                        "type": "object",
                        "properties": schema.get('properties', {}),
                        "required": schema.get('required', [])
                    }
                ))

            if system_tools_enabled:
                restart_tool_schema = RestartServerTool.model_json_schema()
                base_tools.append(Tool(
                    name="restart_server",
                    description=restart_tool_schema.get('description', 'Restarts the server.'),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ))

            return base_tools
        
        # Register tool call handler
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            logger.info(f"Received tool call: {name} with arguments: {arguments}")
            logger.debug(f"Executing handle_call_tool for tool: '{name}' with arguments: {arguments}")
            try:
                if name == "remember":
                    content = arguments.get("content")
                    project_id = arguments.get("project_id")
                    context = arguments.get("context")
                    result = await self.cognitive_engine.remember(content, project_id, context)
                    
                    response_text = result.get("message", "Memory stored successfully")
                    if not result.get("success", False):
                        response_text = f"❌ Error: {result.get('error', 'Unknown error')}"

                    return [TextContent(type="text", text=response_text)]
                    
                elif name == "recall":
                    query = arguments.get("query")
                    project_ids = arguments.get("project_id")
                    focus = arguments.get("focus")
                    raw_fragments = arguments.get("raw_fragments", False)
                    result = await self.cognitive_engine.recall(query, project_ids, focus, raw_fragments)
                    
                    if result.get("success", False):
                        if raw_fragments:
                            response_text = json.dumps(result.get("grouped_fragments", {}), indent=2)
                        else:
                            response_text = result.get("synthesized_response", "No information found")
                    else:
                        response_text = f"❌ Error: {result.get('error', 'Failed to recall information')}"

                    return [TextContent(type="text", text=response_text)]
                
                elif name == "create_project":
                    name_param = arguments.get("name")
                    description = arguments.get("description")
                    
                    if not name_param or not description:
                        return [TextContent(type="text", text="Error: name and description are required")]
                    
                    project_id = await self.cognitive_engine.create_project(name_param, description)
                    
                    if project_id:
                        response_text = f"✅ Created project '{name_param}' with ID: {project_id}"
                    else:
                        response_text = "❌ Failed to create project"
                    
                    return [TextContent(type="text", text=response_text)]
                
                elif name == "list_projects":
                    projects = await self.cognitive_engine.list_projects()
                    
                    if projects:
                        response_text = "📁 Available Projects:\n\n"
                        for project in projects:
                            response_text += f"• **{project['name']}** (`{project['id']}`)\n"
                            response_text += f"  {project['description']}\n\n"
                        response_text += "Use these project IDs in remember/recall operations."
                    else:
                        response_text = "No projects found. Create one with create_project()."
                    
                    return [TextContent(type="text", text=response_text)]

                elif name == "get_project_summary":
                    project_id = arguments.get("project_id")
                    summary = await self.cognitive_engine.get_project_summary(project_id)
                    if summary:
                        task_counts = summary.get('tasks', {})
                        response_text = (
                            f"📊 Summary for project '{project_id}':\n"
                            f"  - Contexts: {summary['contexts']} \n"
                            f"  - Fragments: {summary['fragments']} \n"
                            f"  - Tasks: {sum(task_counts.values())} "
                            f"({task_counts.get('pending', 0)} pending, "
                            f"{task_counts.get('in_progress', 0)} in_progress, "
                            f"{task_counts.get('completed', 0)} completed)"
                        )
                    else:
                        response_text = f"❌ Project with ID '{project_id}' not found."
                    return [TextContent(type="text", text=response_text)]

                elif name == "list_contexts":
                    project_id = arguments.get("project_id")
                    contexts = await self.cognitive_engine.list_contexts(project_id)
                    if contexts:
                        response_text = f"📚 Contexts in project '{project_id}':\n"
                        for ctx in contexts:
                            response_text += f"  - {ctx['name']} (`{ctx['id']}`)\n"
                    else:
                        response_text = f"No contexts found in project with ID '{project_id}'."
                    return [TextContent(type="text", text=response_text)]

                elif name == "list_fragments_by_context":
                    project_id = arguments.get("project_id")
                    context_id = arguments.get("context_id")
                    fragments = await self.cognitive_engine.list_fragments_by_context(project_id, context_id)
                    if fragments:
                        response_text = f"📄 Fragments in context '{context_id}':\n"
                        for frag in fragments:
                            response_text += f"  - `{frag['id']}`: {frag['content'][:80]}...\n"
                    else:
                        response_text = f"No fragments found in context '{context_id}'."
                    return [TextContent(type="text", text=response_text)]
                
                elif name == "get_contexts_for_fragment":
                    fragment_id = arguments.get("fragment_id")
                    contexts = await self.cognitive_engine.get_contexts_for_fragment(fragment_id)
                    if contexts:
                        response_text = f"📚 Contexts containing fragment '{fragment_id}':\n"
                        for ctx in contexts:
                            response_text += f"  - {ctx['name']} (`{ctx['id']}`)\n"
                    else:
                        response_text = f"No contexts found for fragment '{fragment_id}'."
                    return [TextContent(type="text", text=response_text)]

                elif name == "delete_fragment":
                    fragment_id = arguments.get("fragment_id")
                    success = await self.cognitive_engine.delete_fragment(fragment_id)
                    response_text = f"✅ Fragment '{fragment_id}' deleted." if success else f"❌ Failed to delete fragment '{fragment_id}'."
                    return [TextContent(type="text", text=response_text)]

                elif name == "delete_context":
                    project_id = arguments.get("project_id")
                    context_id = arguments.get("context_id")
                    success = await self.cognitive_engine.delete_context(project_id, context_id)
                    response_text = f"✅ Context '{context_id}' deleted." if success else f"❌ Failed to delete context '{context_id}'."
                    return [TextContent(type="text", text=response_text)]

                elif name == "delete_project":
                    project_id = arguments.get("project_id")
                    success = await self.cognitive_engine.delete_project(project_id)
                    response_text = f"✅ Project '{project_id}' deleted." if success else f"❌ Failed to delete project '{project_id}'."
                    return [TextContent(type="text", text=response_text)]

                elif name == "create_task":
                    project_id = arguments.get("project_id")
                    title = arguments.get("title")
                    description = arguments.get("description")
                    task_id = await self.cognitive_engine.create_task(project_id, title, description)
                    response_text = f"✅ Task created with ID: {task_id}" if task_id else "❌ Failed to create task."
                    return [TextContent(type="text", text=response_text)]

                elif name == "get_task":
                    task_id = arguments.get("task_id")
                    task = await self.cognitive_engine.get_task(task_id)
                    response_text = json.dumps(task, indent=2) if task else f"❌ Task '{task_id}' not found."
                    return [TextContent(type="text", text=response_text)]

                elif name == "list_tasks":
                    project_id = arguments.get("project_id")
                    status = arguments.get("status")
                    tasks = await self.cognitive_engine.list_tasks(project_id, status)
                    response_text = json.dumps(tasks, indent=2)
                    return [TextContent(type="text", text=response_text)]

                elif name == "update_task":
                    task_id = arguments.get("task_id")
                    title = arguments.get("title")
                    description = arguments.get("description")
                    status = arguments.get("status")
                    success = await self.cognitive_engine.update_task(task_id, title, description, status)
                    response_text = f"✅ Task '{task_id}' updated." if success else f"❌ Failed to update task '{task_id}'."
                    return [TextContent(type="text", text=response_text)]

                elif name == "delete_task":
                    task_id = arguments.get("task_id")
                    success = await self.cognitive_engine.delete_task(task_id)
                    response_text = f"✅ Task '{task_id}' deleted." if success else f"❌ Failed to delete task '{task_id}'."
                    return [TextContent(type="text", text=response_text)]

                elif name == "restart_server" and system_tools_enabled:
                    logger.warning("Executing restart_server tool.")
                    # Respond to the client FIRST, then restart.
                    # Add a small delay to ensure the message is sent before shutdown.
                    asyncio.create_task(self.schedule_restart(restart_server))
                    return [TextContent(type="text", text="✅ Server is restarting...")]

                else:
                    logger.warning(f"Unknown tool called: {name}")
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                logger.error(f"Error handling tool call '{name}': {e}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        logger.info("✅ Unified MCP handlers registered: list_tools, call_tool")
        logger.debug("Exiting _register_handlers")

    async def schedule_restart(self, restart_function):
        """Schedules the server restart after a short delay."""
        await asyncio.sleep(0.1)  # Delay to allow response to be sent
        restart_function()

    def is_ready(self) -> bool:
        """Check if all services are ready."""
        ready_status = all([
            self.storage, self.embedding, self.memory, 
            self.middleware, self.cognitive_engine
        ])
        return ready_status
    
    async def run(self):
        """Run the unified MCP server."""
        logger.info("🚀 Starting Unified Memoire MCP Server...")
        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("📞 Connected to stdio, running server loop.")
                await self.server.run(
                    read_stream, 
                    write_stream,
                    InitializationOptions(
                        server_name="memoire-unified",
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        except Exception as e:
            logger.critical(f"Fatal error running unified MCP server: {e}", exc_info=True)


    async def schedule_restart(self, restart_function):
        """Schedules the server restart after a short delay."""
        await asyncio.sleep(0.1)  # Delay to allow response to be sent
        restart_function()

    def is_ready(self) -> bool:
        """Check if all services are ready."""
        ready_status = all([
            self.storage, self.embedding, self.memory, 
            self.middleware, self.cognitive_engine
        ])
        return ready_status
    
    async def run(self):
        """Run the unified MCP server."""
        logger.info("🚀 Starting Unified Memoire MCP Server...")
        try:
            async with stdio_server() as (read_stream, write_stream):
                logger.info("📞 Connected to stdio, running server loop.")
                await self.server.run(
                    read_stream, 
                    write_stream,
                    InitializationOptions(
                        server_name="memoire-unified",
                        server_version="0.1.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
        except Exception as e:
            logger.critical(f"Fatal error running unified MCP server: {e}", exc_info=True)
