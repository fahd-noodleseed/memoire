# memoire - Gemini Context

This `GEMINI.md` file provides a concise overview of the memoire project, intended to serve as instructional context for the Gemini CLI agent.

## Project Overview

**memoire** is an experimental **Semantic Memory System for Large Language Models (LLMs)**, implemented as an **MCP (Model Context Protocol) server**. Its primary goal is to address the fundamental limitation of LLMs lacking persistent memory across conversations.

The system intelligently processes information by:
-   **Chunking & Curation**: The `IngestionCurator` analyzes new information against existing memories, uses an LLM to decide what to create, merge, or delete, and dynamically creates new contexts. It ensures the bidirectional relationship between contexts and fragments is maintained.
-   **Contextualization**: Automatically groups related information into thematic contexts.
-   **Vectorization**: Generates `gemini-embedding-001` embeddings for semantic search.
-   **Synthesis**: The `MemorySynthesizer` uses `gemini-2.5-flash` to generate coherent, synthesized responses for `recall` operations.
-   **Task Management**: A full to-do list system is integrated into the memory projects.

### Key Technologies:
-   **Language**: Python 3.11+
-   **Vector Database**: Qdrant (local file-based)
-   **Metadata Store**: SQLite (local file-based)
-   **Cognitive Processing**: Google Gemini models (`gemini-embedding-001`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`)

## CLI Tooling Reference

This is the primary interface for interacting with the memoire system.

### Project Management
-   `create_project(name: str, description: str)`: Creates a new memory project.
-   `list_projects()`: Lists all available projects.
-   `get_project_summary(project_id: str)`: Retrieves statistics for a project, including counts of contexts, fragments, and tasks (broken down by status).
-   `delete_project(project_id: str)`: Deletes an entire project and all its associated data.

### Memory Operations
-   `remember(project_id: str, content: str)`: Stores information in the memory. This triggers the full intelligent ingestion pipeline, which may result in creating, merging, or deleting fragments and contexts.
-   `recall(project_id: str | list[str], query: str, focus: str | None, raw_fragments: bool | None)`: Retrieves and synthesizes information. Can search in one or multiple projects. `raw_fragments=True` returns the direct data without LLM synthesis.
-   `delete_fragment(fragment_id: str)`: Deletes a specific memory fragment.

### Context & Fragment Exploration
-   `list_contexts(project_id: str)`: Lists all thematic contexts in a project.
-   `list_fragments_by_context(project_id: str, context_id: str)`: Shows all memory fragments within a specific context.
-   `get_contexts_for_fragment(fragment_id: str)`: Finds which contexts a specific fragment belongs to.
-   `delete_context(project_id: str, context_id: str)`: Deletes a context and ALL its associated fragments.

### Task Management
-   `create_task(project_id: str, title: str, description: str = "")`: Creates a new to-do item in a project.
-   `list_tasks(project_id: str, status: str | None)`: Lists tasks. `status` can be `pending`, `in_progress`, or `completed`.
-   `get_task(task_id: str)`: Retrieves the details of a single task.
-   `update_task(task_id: str, title: str | None, description: str | None, status: str | None)`: Updates a task's properties.
-   `delete_task(task_id: str)`: Deletes a task.

## Development Directives

-   As the Gemini CLI client for the memoire project, I need to be restarted for any code changes to take effect during testing.
-   The database is frequently wiped for testing. Always start from a clean slate by creating a project and populating it with data before running tests.
-   The core logic for ingestion is in `src/mcp/intelligence/ingestion_curator.py`. The data storage logic is in `src/core/storage/`.