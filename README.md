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

The main entry point for the MCP server is `run.py`. It is typically integrated and launched via a client application.

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

### Note for WSL Users

To use Memoire seamlessly across both Windows and WSL (Windows Subsystem for Linux), you can configure the data directory to point to a shared location. Edit `config.json` and set the `storage.data_dir` to a path accessible by both, such as a directory on your mounted C: drive:

```json
{
  "storage": {
    "data_dir": "/mnt/c/Users/YourUser/Documents/memoire_data"
  }
}
```

## Command-Line Interface (CLI) Tools

Memoire provides a rich set of tools for direct interaction and management.

-   `create_project(name, description)`
-   `list_projects()`
-   `get_project_summary(project_id)`
-   `delete_project(project_id)`
-   `remember(project_id, content)`
-   `recall(project_id, query, ...)`
-   `delete_fragment(fragment_id)`
-   `list_contexts(project_id)`
-   `list_fragments_by_context(project_id, context_id)`
-   `get_contexts_for_fragment(fragment_id)`
-   `delete_context(project_id, context_id)`
-   `create_task(project_id, title, description)`
-   `list_tasks(project_id, status)`
-   `get_task(task_id)`
-   `update_task(task_id, ...)`
-   `delete_task(task_id)`

## Architecture & Advanced Details

### Core Components

*   **`src/core`**: Foundational layer for storage (`Qdrant` + `SQLite`), embedding, and memory operations.
*   **`src/mcp/intelligence`**: The "brain" of the system, featuring the `IngestionCurator` and `MemorySynthesizer`.

### Advanced Gemini Implementation

This project leverages several advanced features of the Gemini API to achieve its results:

-   **Structured Output (JSON Mode)**: The `IngestionCurator` uses Gemini's JSON mode to force the model to return a structured decision schema (`{ "fragments_to_create": [], "ids_to_delete": [] }`). This makes the output predictable and reliable, eliminating the need for fragile string parsing.
-   **Task-Specific Embeddings**: The system uses specialized embedding models depending on the task. For instance, `SEMANTIC_SIMILARITY` is used during ingestion to find related documents, while `RETRIEVAL_QUERY` could be used for recall, optimizing the vectors for their specific purpose.
-   **Configurable Models**: While the system defaults to `gemini-2.5-flash-lite` for the fast curation task, the models are configurable in `config.json`. You can easily swap in more powerful models like `gemini-2.5-pro` for synthesis or curation, balancing cost, speed, and capability.

## Roadmap & Future Directions

Memoire is an active experiment. Here are some of the planned improvements and research areas:

-   **GUI Enhancements**: The current GUI is functional for monitoring but needs to be updated and tested to fully support all the new backend features, such as task and context management.
-   **Publish to PyPI**: To simplify distribution, the project will be packaged and published to PyPI, allowing for a simple `pip install memoire-mcp` setup.
-   **Expanded CLI Tools**: Introduce more granular tools for advanced memory management, such as directly merging fragments or managing context hierarchies.
-   **Performance Optimization**: Analyze and optimize the recall process to reduce latency.
-   **Memory Visualization**: Implement a 3D force-directed graph or similar visualization in the GUI to explore the semantic relationships between memory fragments and contexts.

---

*This is experimental software. Use for learning and exploration, not for production systems.*