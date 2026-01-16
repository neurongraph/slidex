# Slidex

Slidex is a single-user Python application for managing PowerPoint slides with semantic search capabilities. It uses LightRAG, a graph-based retrieval system, to provide advanced semantic search with entity extraction and relationship mapping across slides. You can ask a query, get relevant slides with their thumbnail previews and assemble a new deck from the slides you select. The output is both in pptx and pdf formats

## Features

- **LightRAG Integration**: Graph-based RAG with entity extraction and relationship discovery
- **Ingest PowerPoint files**: Single files or entire folders (recursive)
- **Advanced semantic search**: Find slides using natural language with context awareness
- **Slide preview**: Thumbnails and summaries for each slide
- **Slide assembly**: Create new presentations from search results
- **Local models**: Uses Ollama for embeddings and summarization (no cloud APIs), and vLLM based Reranking model
- **Audit logging**: All LLM interactions logged to SQLite for full auditability
- **Web UI**: Simple FastAPI-based interface for search and browsing
- **CLI**: Command-line interface for batch operations

## Prerequisites

- Python 3.9+
- PostgreSQL (for metadata storage)
- Ollama (running locally for embeddings and LLM)
- vLLM
- LibreOffice
- uv (Python package manager)

### Required Ollama Models

Download the required models before using Slidex:

```bash
ollama pull nomic-embed-text
ollama pull granite4:tiny-h
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd slidex
```

2. Run the complete setup:
```bash
# This will create venv, install dependencies, create .env, and init database
just setup
```

3. Activate the virtual environment:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

4. Pull required Ollama models:
```bash
just pull-models
# Or manually:
# ollama pull nomic-embed-text
# ollama pull granite4:tiny-h
```

**Note**: For full PDF processing capabilities, install LibreOffice:
```bash
brew install libreoffice
```

# Initialize database
just init-db
```

## Configuration

The application uses Pydantic settings for configuration. You can set configuration values via:

1. Environment variables
2. A `config/dev.yaml` file (see `config/dev.yaml.example`)
3. Default values in the code



### vLLM Reranker Configuration

To enable vLLM-based reranker for LightRAG:

1. Set `VLLM_RERANKER_ENABLED=true`
2. Set `VLLM_RERANKER_URL` to your vLLM service URL (default: `http://localhost:8182`)
3. Set `VLLM_RERANKER_MODEL` to your reranker model name (default: `bge-reranker-v2-m3`)

Example configuration in `.env`:
```
VLLM_RERANKER_ENABLED=true
VLLM_RERANKER_URL=http://localhost:8182
VLLM_RERANKER_MODEL=bge-reranker-v2-m3
```


## Configuration

Configuration is managed via `slidex/config.py` using Pydantic Settings. You can override defaults using environment variables or a `.env` file.

Key settings:
- `DATABASE_URL`: PostgreSQL connection URL
- `OLLAMA_HOST` / `OLLAMA_PORT`: Ollama server location
- `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: `nomic-embed-text`)
- `OLLAMA_SUMMARY_MODEL`: Summary model (default: `granite4:tiny-h`)
- `STORAGE_ROOT`: Base directory for thumbnails and exports
- `LIGHTRAG_WORKING_DIR`: LightRAG storage directory (default: `storage/lightrag`)
- `LIGHTRAG_ENABLED`: Enable LightRAG (default: `True`)
- `LIGHTRAG_LLM_CONTEXT_SIZE`: Context size for LightRAG LLM (default: `32768`)
- `FAISS_INDEX_PATH`: Path to FAISS index file (legacy, used when LightRAG is disabled)
- `TOP_K_RESULTS`: Default number of search results (default: 10)

## Usage

### CLI Commands

#### Ingest Files

**Option 1: Using just commands (easiest, no venv activation needed)**
```bash
# Ingest a single file
just ingest-file /path/to/presentation.pptx

# Ingest a folder (recursive)
just ingest-folder /path/to/folder

# Ingest a folder (non-recursive)
just ingest-folder /path/to/folder false
```

**Option 2: Using the slidex CLI (requires venv activation)**
```bash
# First activate the virtual environment
source .venv/bin/activate

# Ingest a single file
slidex ingest file /path/to/presentation.pptx

# Ingest a folder (recursive)
slidex ingest folder /path/to/folder --recursive

# Ingest with uploader name
slidex ingest file /path/to/file.pptx --uploader "John Doe"
```

### Web UI

Start the FastAPI development server:

```bash
just run
# Or manually:
uv run python -m slidex.api.app
```

Then open your browser to http://localhost:5000

**Pages:**
- `/` - Search interface
- `/ingest` - Ingestion instructions
- `/decks` - View all ingested decks

### REST API

The FastAPI app exposes a REST API for programmatic access:

#### Ingest File
```bash
curl -X POST http://localhost:5000/api/ingest/file \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/file.pptx"}'
```

#### Ingest Folder
```bash
curl -X POST http://localhost:5000/api/ingest/folder \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/folder", "recursive": true}'
```

#### Search
```bash
# Basic search with default hybrid mode
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "data science", "top_k": 10}'

# Search with specific LightRAG mode
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 10, "mode": "global"}'
```

#### Assemble
```bash
curl -X POST http://localhost:5000/api/assemble \
  -H "Content-Type: application/json" \
  -d '{"slide_ids": ["uuid1", "uuid2"], "preserve_order": true}'
```

#### Download
```bash
curl -O http://localhost:5000/api/download/assembled_20241212_123456.pptx
```

## Project Structure

```
slidex/
├── slidex/
│   ├── __init__.py
│   ├── config.py              # Central configuration
│   ├── logging_config.py      # Loguru setup
│   ├── api/
│   │   ├── __init__.py
│   │   └── app.py            # FastAPI application
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py           # Typer CLI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── audit_logger.py   # SQLite audit logging
│   │   ├── database.py       # PostgreSQL operations
│   │   ├── ollama_client.py  # Ollama integration
│   │   ├── lightrag_client.py # LightRAG wrapper
│   │   ├── slide_processor.py # Text extraction & thumbnails
│   │   ├── vector_index.py   # FAISS index (legacy)
│   │   ├── ingest.py         # Ingestion engine
│   │   ├── search.py         # Search engine
│   │   └── assembler.py      # Presentation assembly
│   └── templates/            # Jinja2 templates
├── migrations/               # SQL schema migrations
├── storage/                  # Local storage
│   ├── lightrag/            # LightRAG graph storage
│   ├── thumbnails/          # Slide thumbnails
│   ├── exports/             # Assembled presentations
│   ├── logs/                # Application logs
│   └── audit.db             # LLM audit log
├── scripts/
│   └── init_db.py           # Database initialization
├── tests/                   # Test suite
├── justfile                 # Just commands
├── pyproject.toml          # Project dependencies
└── README.md               # This file
```

## Development

### Common Commands (using Just)

```bash
just              # Show all available commands
just setup        # Complete development setup
just pull-models  # Pull required Ollama models
just check        # Check system requirements
just install      # Install dependencies
just run          # Run Flask dev server
just test         # Run tests
just init-db      # Initialize database
just clean        # Clean generated files
just clean-all    # Deep clean (remove venv, storage, .env)
just logs         # View application logs
just audit-logs   # View LLM audit logs
just db-stats     # Show database statistics
just index-stats  # Show FAISS index statistics
just clean-data   # Clean all data (database, FAISS, LightRAG)
```

### Running Tests

```bash
just test
# Or manually:
pytest tests/ -v
```

## How It Works

### LightRAG Architecture

Slidex now uses **LightRAG**, a graph-based RAG system that provides more sophisticated retrieval than traditional vector search:

1. **Ingestion**:
   - PowerPoint files are parsed using `python-pptx`
   - Text is extracted from slides and thumbnails are generated
   - Summaries are created using Ollama's LLM
   - Slide content is inserted into LightRAG with metadata (deck name, slide index, etc.)
   - LightRAG automatically extracts entities and relationships between slides
   - A knowledge graph is built to capture semantic connections

2. **Entity & Relationship Extraction**:
   - LightRAG uses the configured LLM to identify key entities (concepts, topics, names)
   - Relationships between entities are discovered across slides
   - This enables contextual retrieval beyond simple keyword matching

3. **Search with Multiple Modes**:
   - **Naive**: Simple semantic search without graph traversal
   - **Local**: Retrieves contextually related information from nearby graph nodes
   - **Global**: Utilizes global knowledge across the entire knowledge graph
   - **Hybrid**: Combines local and global strategies for best results (recommended)
   - Query results include synthesized answers with references to relevant slides

4. **Assembly**: Selected slides are copied from original presentations into a new PowerPoint file, preserving formatting where possible.

5. **Audit**: All LLM interactions (embeddings, entity extraction, queries) are logged to a SQLite database for full auditability.

### Starting Fresh with LightRAG

If you're upgrading from a previous version or want to start with a clean slate:

```bash
# Clean all existing data (database, FAISS, LightRAG)
just clean-data

# Re-initialize database
just init-db

# Re-ingest your PowerPoint files
just ingest-folder /path/to/your/slides
```

All slides will be indexed into LightRAG's knowledge graph automatically during ingestion.

## Limitations

- **Dev mode only**: No authentication, single-user, no containerization
- **Slide copying**: Best-effort formatting preservation (complex slides may lose some formatting)
- **Local only**: Designed for local development, not production deployment

## Thumbnails

Slidex uses a hybrid thumbnail generation approach:

1. **LibreOffice (Best)**: If installed, LibreOffice renders actual slide visuals
2. **Pillow (Fallback)**: Enhanced rendering of slide shapes, colors, and text

For best results, install LibreOffice:
```bash
brew install --cask libreoffice
```

## Troubleshooting

### Ollama connection errors
- Ensure Ollama is running: `ollama serve`
- Check that models are downloaded: `ollama list`
- Verify connection: `curl http://localhost:11434/api/tags`

### Database connection errors
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in config
- Initialize database: `just init-db`

### Import errors
- Ensure virtual environment is activated
- Reinstall dependencies: `just install`

## License

MIT License

## Contributing

This is a development project. Feel free to fork and modify for your needs.
