"""
System-level tools for Memoire MCP server management.

This module defines the Pydantic models for all tools exposed by the Memoire MCP server.
These tools are the primary interface for clients (like Claude Desktop or a CLI) to interact
with the memory system.

Each tool is defined as a Pydantic BaseModel, which allows for automatic validation
and schema generation. The docstrings for each class and its fields are critical, as they
are displayed to the end-user in the client's tool selection interface (e.g., Ctrl+T).

The descriptions should be comprehensive, explaining:
- The tool's purpose and when to use it.
- A clear explanation of each parameter.
- What the tool returns or its side effects.
"""
from typing import Optional
from pydantic import BaseModel, Field

# ==================== SERVER MANAGEMENT TOOLS ====================

class RestartServerTool(BaseModel):
    """
    Triggers a graceful restart of the Memoire MCP server process.

    Use this tool to apply code changes in a development environment without needing
    to restart the parent client application (e.g., Claude Desktop). The server
    will attempt a graceful shutdown and then restart, preserving the client connection.

    This is a powerful administrative tool intended for development and should be
    used with caution in a production environment.
    """
    pass

# ==================== DATA QUERY TOOLS ====================

class GetProjectSummaryTool(BaseModel):
    """
    Retrieves a high-level summary of a specific project.

    This tool provides key statistics for a project, including the total number of
    memory fragments and cognitive contexts. It's useful for getting a quick
    overview of the memory space's size and scope.
    """
    project_id: str = Field(..., description="The unique ID of the project to summarize. Use `list_projects()` to find available project IDs.")

class ListContextsTool(BaseModel):
    """
    Lists all cognitive contexts available within a specific project.

    A context is a thematic grouping of related memory fragments. Use this tool to
    discover the main topics and categories that have been created in the memory.
    The returned context IDs can be used with other tools like `list_fragments_by_context`.
    """
    project_id: str = Field(..., description="The unique ID of the project from which to list contexts. Use `list_projects()` to find it.")

class ListFragmentsByContextTool(BaseModel):
    """
    Lists all memory fragments that belong to a specific cognitive context.

    This is the primary tool for exploring the contents of a known topic or category.
    It allows you to retrieve all the individual pieces of information (fragments)
    that have been grouped under a single context.
    """
    project_id: str = Field(..., description="The unique ID of the project. Use `list_projects()` to find it.")
    context_id: str = Field(..., description="The unique ID of the context to explore. Use `list_contexts()` to find it.")

class GetContextsForFragmentTool(BaseModel):
    """
    Finds and lists all cognitive contexts associated with a single memory fragment.

    This tool performs a reverse lookup. It answers the question: 'In which different
    topics or categories is this specific piece of information relevant?'. It's useful
    for understanding the relationships and multi-faceted nature of a memory fragment.
    """
    fragment_id: str = Field(..., description="The unique ID of the fragment for which to find parent contexts.")


# ==================== DATA MANAGEMENT TOOLS ====================

class DeleteFragmentTool(BaseModel):
    """
    Permanently deletes a specific memory fragment by its unique ID.

    This action is irreversible. Use this tool to remove incorrect, outdated, or
    redundant pieces of information from the memory. Be sure of the fragment ID
    before executing this command.
    """
    fragment_id: str = Field(..., description="The unique ID of the fragment to be permanently deleted.")

class DeleteContextTool(BaseModel):
    """
    Permanently deletes a cognitive context and ALL its associated fragments.

    This is a destructive and irreversible action. Deleting a context will also
    delete every fragment that is ONLY associated with this context. Use with extreme
    caution. It's useful for removing entire topics that are no longer relevant.
    """
    project_id: str = Field(..., description="The unique ID of the project containing the context. Use `list_projects()` to find it.")
    context_id: str = Field(..., description="The unique ID of the context to be permanently deleted. Use `list_contexts()` to find it.")

class DeleteProjectTool(BaseModel):
    """
    Permanently deletes an entire project and all its associated data.

    This action is final and irreversible. It will remove all contexts, fragments,
    and the underlying Qdrant vector collection for the specified project.
    This is the most destructive tool and should only be used when you are certain
    you want to erase an entire memory space.
    """
    project_id: str = Field(..., description="The unique ID of the project to be permanently deleted. Use `list_projects()` to find it.")

# ==================== TASK MANAGEMENT TOOLS ====================

class CreateTaskTool(BaseModel):
    """
    Creates a new task or to-do item within a specified project.

    Tasks are a special type of memory used for managing action items. This tool
    allows you to add a new task with a title and an optional description.
    """
    project_id: str = Field(..., description="The unique ID of the project to which the task will be added. Use `list_projects()` to find it.")
    title: str = Field(..., description="A concise title for the task (e.g., 'Write a summary of the meeting').")
    description: Optional[str] = Field("", description="An optional, more detailed description of the task and its requirements.")

class GetTaskTool(BaseModel):
    """
    Retrieves the details of a specific task by its unique ID.
    """
    task_id: str = Field(..., description="The unique ID of the task to retrieve.")

class ListTasksTool(BaseModel):
    """
    Lists tasks for a project, with an optional filter for status.

    Use this tool to see all tasks within a project or to check on tasks with a
    specific status (e.g., 'pending' or 'in_progress').
    """
    project_id: str = Field(..., description="The unique ID of the project whose tasks you want to list. Use `list_projects()` to find it.")
    status: Optional[str] = Field(None, description="Filter tasks by status. Can be 'pending', 'in_progress', or 'completed'.", pattern="^(pending|in_progress|completed)$")

class UpdateTaskTool(BaseModel):
    """
    Updates the title, description, or status of an existing task.

    Use this tool to modify a task. You can change its content or, most commonly,
    update its status from 'pending' to 'in_progress' or 'completed'.
    """
    task_id: str = Field(..., description="The unique ID of the task to update.")
    title: Optional[str] = Field(None, description="The new title for the task.")
    description: Optional[str] = Field(None, description="The new, updated description for the task.")
    status: Optional[str] = Field(None, description="The new status for the task. Must be 'pending', 'in_progress', or 'completed'.", pattern="^(pending|in_progress|completed)$")

class DeleteTaskTool(BaseModel):
    """
    Permanently deletes a task by its unique ID. This action is irreversible.
    """
    task_id: str = Field(..., description="The unique ID of the task to be permanently deleted.")
