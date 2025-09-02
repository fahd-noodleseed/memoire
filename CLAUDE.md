# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Memoire is an experimental semantic memory system for LLMs implemented as an MCP (Model Context Protocol) server. It provides persistent memory across conversations through intelligent chunking, contextualization, and semantic search capabilities.

## Development Commands

### Running the Application
```bash
python run.py
```

### Testing
```bash
pytest
# Run async tests
pytest -v tests/
```

### Dependencies
```bash
pip install -r requirements.txt
# Or for development dependencies
pip install -e ".[dev]"
```

### pipx Installation
```bash
# Install locally from source
pipx install .

# Install from GitHub
pipx install git+https://github.com/fahd-noodleseed/memoire

# Run the installed command
memoire
```

### Environment Setup
- Requires Python 3.11+
- Requires `GOOGLE_API_KEY` environment variable for Gemini API
- Set `ENABLE_GUI=false` for headless mode (default in WSL)

## Architecture Overview

### Core Components
- **`src/core/`**: Foundation layer containing storage (Qdrant + SQLite), embedding services, and memory operations
- **`src/mcp/`**: MCP server implementation and intelligence processing
  - **`intelligence/`**: Contains `IngestionCurator` (decides what to create/merge/delete) and `MemorySynthesizer` (generates coherent responses)
  - **`server/`**: MCP protocol implementation
- **`src/models/`**: Data models for projects, fragments, contexts, tasks, and anchors
- **`src/config/`**: Configuration management
- **`src/gui/`**: CustomTkinter-based desktop GUI
- **`src/tray/`**: System tray interface

### Key Data Models
- **Project**: Top-level container for memory segregation
- **MemoryFragment**: Individual pieces of stored information
- **MemoryContext**: Thematic groupings of related fragments
- **Task**: Built-in task management system
- **CognitiveAnchor**: Conceptual anchors for memory organization

### Storage Architecture
- **Vector Store**: Qdrant (local file-based) for semantic embeddings
- **Metadata Store**: SQLite for relational data and full-text search
- **Embeddings**: Google Gemini `gemini-embedding-001` (3072 dimensions)

### Intelligence Processing
- **Curation**: Uses `gemini-2.5-flash-lite` for fast ingestion decisions
- **Synthesis**: Uses `gemini-2.5-flash` for generating coherent recall responses
- **Structured Output**: Leverages Gemini's JSON mode for reliable parsing

## Configuration

Configuration is managed through `config.json` with the following key sections:
- `embedding`: Model settings and caching configuration
- `processing`: LLM models and parameters
- `storage`: Data directory and Qdrant settings
- `intelligence`: Curation thresholds and similarity settings

## Entry Points

- **`run.py`**: Main application launcher (MCP server + GUI + system tray)
- **MCP Integration**: Designed to run as MCP server in Claude Desktop or similar clients

## Development Notes

- The codebase uses async/await patterns extensively
- GUI components are optional and disabled in headless environments
- All file operations use pathlib for cross-platform compatibility
- Logging is centralized through `src/logging_config.py`
- No traditional test suite found - testing appears to be done through integration