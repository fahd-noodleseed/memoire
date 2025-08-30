# Memoire 🧠

**Experimental Semantic Memory System for Large Language Models**

> ⚠️ **Experimental Project**: Memoire is a vibe-coded exploration into semantic memory for LLMs. Built through AI-assisted development, it embodies the same cognitive augmentation principles it attempts to solve. Expect rough edges, unconventional patterns, and iterative improvements.

## What is Memoire?

Memoire is an experimental **MCP (Model Context Protocol) server** that tackles one of the fundamental limitations of LLM interactions: **the lack of persistent memory across conversations**. Instead of simple storage, Memoire implements a semantic memory that intelligently chunks, contextualizes, and curates information for natural language retrieval across conversation boundaries.

## Key Features

-   **🧠 Intelligent Ingestion**: New information is not just stored; it's analyzed against existing memories. An LLM decides whether to create new entries, merge them, or delete obsolete information to avoid redundancy.
-   **🗂️ Automatic Contextualization**: The system automatically identifies and creates thematic contexts for new information, grouping related ideas without manual intervention.
-   **🔍 Semantic Recall**: Ask questions in natural language. The system finds the most relevant memory fragments and uses an LLM to synthesize a coherent, context-aware answer.
-   **📋 Task Management**: A complete to-do system is built into the memory, allowing you to create, update, list, and delete tasks within any project.
-   **🧩 Project Segregation**: Keep memories for different topics completely separate using projects.
-   **💻 CLI & MCP Interface**: Interact with the memory through a comprehensive set of command-line tools or transparently via an integrated MCP server like Claude Desktop.

## Architecture Overview

Memoire employs a sophisticated, multi-step process for managing memory.

*   **`src/core`**: The foundational layer providing services for storage (`Qdrant` + `SQLite`), embedding generation, and basic memory operations (CRUD).
*   **`src/mcp`**: The main application logic, including the MCP server and the intelligence layer.
*   **`src/mcp/intelligence`**: The "brain" of the system.
    *   **`IngestionCurator`**: Drives the `remember` process. It analyzes new information against existing memories, uses an LLM to decide what to create, merge, or delete, and dynamically creates new contexts. It ensures that relationships between fragments and contexts are correctly maintained.
    *   **`MemorySynthesizer`**: Generates coherent, synthesized responses for `recall` operations.

### Technical Stack

-   **Language**: Python 3.11+
-   **Vector Database**: Qdrant for semantic search
-   **Metadata Store**: SQLite for structured data
-   **Cognitive Processing**:
    -   `gemini-embedding-001` for vectorization.
    -   `gemini-2.5-flash` for recall and synthesis.
    -   `gemini-2.5-flash-lite` for ingestion curation.

## Installation & Setup

### Prerequisites
-   Python 3.11+
-   A Google AI API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation Steps

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/ThePartyAcolyte/memoire
    cd memoire
    ```
2.  **Create and activate a Python virtual environment**:
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

The main entry point for the MCP server is `run.py`. It is typically integrated and launched via a client application like Claude Desktop.

**Example Claude Desktop Configuration (`claude_desktop_config.json`):**
```json
{
  "mcpServers": {
    "memoire": {
      "command": "/full/path/to/memoire/venv/bin/python",
      "args": ["/full/path/to/memoire/run.py"],
      "env": {
        "GOOGLE_API_KEY": "your-google-ai-api-key"
      }
    }
  }
}
```
*Note: On Windows, the command path would be `...\venv\Scripts\python.exe`.*

## Command-Line Interface (CLI) Tools

Memoire provides a rich set of tools for direct interaction and management.

### Project Management
-   `create_project(name, description)`: Creates a new memory project.
-   `list_projects()`: Lists all available projects.
-   `get_project_summary(project_id)`: Shows statistics for a project (fragment, context, and task counts).
-   `delete_project(project_id)`: Deletes an entire project and all its data.

### Memory Operations
-   `remember(project_id, content)`: Stores information in the memory, triggering the intelligent curation process.
-   `recall(project_id, query, ...)`: Retrieves and synthesizes information based on a natural language query.
-   `delete_fragment(fragment_id)`: Deletes a specific piece of information.

### Context Management
-   `list_contexts(project_id)`: Lists all thematic contexts in a project.
-   `list_fragments_by_context(project_id, context_id)`: Shows all memory fragments within a specific context.
-   `get_contexts_for_fragment(fragment_id)`: Finds which contexts a fragment belongs to.
-   `delete_context(project_id, context_id)`: Deletes a context and all its associated fragments.

### Task Management
-   `create_task(project_id, title, description)`: Creates a new to-do item.
-   `list_tasks(project_id, status)`: Lists tasks, optionally filtering by status (`pending`, `in_progress`, `completed`).
-   `get_task(task_id)`: Retrieves the details of a single task.
-   `update_task(task_id, ...)`: Updates a task's title, description, or status.
-   `delete_task(task_id)`: Deletes a task.

## Development

-   **Vibe-Coded**: This project is built through AI-assisted development. Expect experimental and iterative approaches.
-   **Local-first**: Data is stored locally in the `data/` directory. No cloud dependencies.
-   **Testing**: To run the test suite, use `pytest tests/`.

---

*This is experimental software. Use for learning and exploration, not for production systems.*
