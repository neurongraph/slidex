# Slidex

Slidex is a single-user Python application for managing PowerPoint slides with semantic search capabilities. It uses LightRAG, a graph-based retrieval system, to provide advanced semantic search with entity extraction and relationship mapping across slides. You can ask a query, get relevant slides with their thumbnail previews, and assemble a new deck from the slides you select. The output is available in both PPTX and PDF formats.

## Features

- **Google SSO Authentication**: Secure login via Google Workspace
- **Mandatory Login Enforcement**: Protected access for all web and API routes
- **LightRAG Integration**: Graph-based RAG with entity extraction and relationship discovery
- **Ingest PowerPoint files**: Single files or entire folders (recursive)
- **Advanced semantic search**: Find slides using natural language with context awareness
- **Slide preview**: Thumbnails and summaries for each slide
- **Slide assembly**: Create new presentations from search results
- **Local models**: Uses Ollama for embeddings and summarization (no cloud APIs), and vLLM-based reranking model
- **Audit logging**: All LLM interactions logged to SQLite for full auditability
- **Web UI**: Modern FastAPI-based interface for search and browsing
- **CLI**: Command-line interface for batch operations

## Prerequisites

- Python 3.9+
- PostgreSQL (for metadata storage)
- Ollama (running locally for embeddings and LLM)
- vLLM (optional, for reranking)
- LibreOffice (optional, for enhanced PDF processing)
- uv (Python package manager)

### Required Ollama Models

Download the required models before using Slidex:

```bash
ollama pull nomic-embed-text
ollama pull granite4:tiny-h
```

## Quick Start

### 1. Install Dependencies

**macOS:**
```bash
# Install core dependencies
brew install python@3.12 postgresql@16 ollama just libreoffice

# Start services
brew services start postgresql@16
brew services start ollama

# Create database
createdb slidex
```

### 2. Setup Slidex

```bash
# Clone repository
git clone <repository-url>
cd slidex

# Complete setup (creates venv, installs dependencies, creates .env, initializes database)
just setup

# Activate virtual environment
source .venv/bin/activate

# Pull required Ollama models
just pull-models
```

### 3. Start Using Slidex

**Web Interface:**
```bash
just run
# Open browser to http://localhost:5001 (authentication required)
```

**Command Line:**
```bash
# Ingest a presentation
just ingest-file /path/to/presentation.pptx

# Ingest a folder
just ingest-folder /path/to/folder

# Or use CLI directly (requires venv activation)
slidex ingest file /path/to/presentation.pptx
slidex search "machine learning"
```

## Configuration

The application uses Pydantic settings for configuration. You can set configuration values via:

1. Environment variables (or `.env` file)
2. Default values in the code

### Key Settings

- `DATABASE_URL`: PostgreSQL connection URL
- `OLLAMA_HOST` / `OLLAMA_PORT`: Ollama server location
- `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: `nomic-embed-text`)
- `OLLAMA_SUMMARY_MODEL`: Summary model (default: `granite4:tiny-h`)
- `STORAGE_ROOT`: Base directory for thumbnails and exports
- `LIGHTRAG_WORKING_DIR`: LightRAG storage directory (default: `storage/lightrag`)
- `LIGHTRAG_ENABLED`: Enable LightRAG (default: `True`)
- `LIGHTRAG_LLM_CONTEXT_SIZE`: Context size for LightRAG LLM (default: `32768`)
- `TOP_K_RESULTS`: Default number of search results (default: 10)
- `GOOGLE_CLIENT_ID`: Google OAuth 2.0 Client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth 2.0 Client Secret
- `SECRET_KEY`: Secret key for session encryption
- `SESSION_SECRET_KEY`: Secret key for signing session cookies

### vLLM Reranker Configuration (Optional)

To enable vLLM-based reranker for enhanced search results:

1. Set `VLLM_RERANKER_ENABLED=true`
2. Set `VLLM_RERANKER_URL` to your vLLM service URL (default: `http://localhost:8182`)
3. Set `VLLM_RERANKER_MODEL` to your reranker model name (default: `bge-reranker-v2-m3`)

Example configuration in `.env`:
```
VLLM_RERANKER_ENABLED=true
VLLM_RERANKER_URL=http://localhost:8182/v1/rerank
VLLM_RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

## Usage

### Web Interface

Start the FastAPI development server:

```bash
just run
```

Then open your browser to http://localhost:5001. You will be redirected to the Google login page.

**Pages:**
- `/` - Search interface
- `/ingest` - Ingestion instructions
- `/decks` - View all ingested decks
- `/graph` - Visualize knowledge graph

### Command Line Interface

**Ingest Files:**
```bash
# Using just commands (easiest, no venv activation needed)
just ingest-file /path/to/presentation.pptx
just ingest-folder /path/to/folder

# Using slidex CLI (requires venv activation)
slidex ingest file /path/to/presentation.pptx
slidex ingest folder /path/to/folder --recursive
```

**Search:**
```bash
slidex search "machine learning" --top-k 10
```

**Assemble:**
```bash
slidex assemble --slide-ids "uuid1,uuid2" --output "new_deck.pptx"
```

### REST API

The FastAPI app exposes a REST API for programmatic access:

**Note**: API requests require a valid `session_id` cookie. Use tools like `curl --cookie "session_id=..."`.

**Ingest File:**
```bash
curl -X POST http://localhost:5001/api/ingest/file \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/file.pptx"}'
```

**Search:**
```bash
curl -X POST http://localhost:5001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "data science", "top_k": 10, "mode": "hybrid"}'
```

**Assemble:**
```bash
curl -X POST http://localhost:5001/api/assemble \
  -H "Content-Type: application/json" \
  -d '{"slide_ids": ["uuid1", "uuid2"], "preserve_order": true}'
```

## Common Commands (Just)

```bash
just              # Show all available commands
just setup        # Complete development setup
just pull-models  # Pull required Ollama models
just check        # Check system requirements
just run          # Run FastAPI dev server
just test         # Run tests
just init-db      # Initialize database
just clean        # Clean generated files
just clean-all    # Deep clean (remove venv, storage, .env)
just logs         # View application logs
just audit-logs   # View LLM audit logs
just db-stats     # Show database statistics
just clean-data   # Clean all data (database and LightRAG)
```

## How It Works

### LightRAG Architecture

Slidex uses **LightRAG**, a graph-based RAG system that provides more sophisticated retrieval than traditional vector search:

1. **Ingestion**:
   - PowerPoint files are parsed using `python-pptx`
   - Text is extracted from slides and thumbnails are generated
   - Summaries are created using Ollama's LLM
   - Slide content is inserted into LightRAG with metadata
   - LightRAG automatically extracts entities and relationships
   - A knowledge graph is built to capture semantic connections

2. **Entity & Relationship Extraction**:
   - LightRAG uses the configured LLM to identify key entities
   - Relationships between entities are discovered across slides
   - This enables contextual retrieval beyond simple keyword matching

3. **Search with Multiple Modes**:
   - **Naive**: Simple semantic search without graph traversal
   - **Local**: Retrieves contextually related information from nearby graph nodes
   - **Global**: Utilizes global knowledge across the entire knowledge graph
   - **Hybrid**: Combines local and global strategies for best results (recommended)

4. **Assembly**: Selected slides are copied from original presentations into a new PowerPoint file, preserving formatting where possible.

5. **Audit**: All LLM interactions are logged to a SQLite database for full auditability.

### PDF Processing

Slidex includes optional PDF processing capabilities:

- **Full Deck Conversion**: PowerPoint presentations are converted to PDF using LibreOffice
- **Individual Slide Extraction**: Each slide is extracted as a separate PDF page
- **Dual Format Assembly**: Assembled presentations can be created as both PPTX and PDF files
- **Visual Fidelity**: Complex slide elements are preserved in PDF format

PDF processing requires LibreOffice to be installed. When disabled, core functionality remains intact.

## Project Structure

```
slidex/
├── slidex/
│   ├── config.py              # Central configuration
│   ├── logging_config.py      # Loguru setup
│   ├── api/
│   │   └── app.py            # FastAPI application
│   ├── cli/
│   │   └── main.py           # Typer CLI
│   ├── core/
│   │   ├── audit_logger.py   # SQLite audit logging
│   │   ├── database.py       # PostgreSQL operations
│   │   ├── ollama_client.py  # Ollama integration
│   │   ├── lightrag_client.py # LightRAG wrapper
│   │   ├── slide_processor.py # Text extraction & thumbnails
│   │   ├── ingest.py         # Ingestion engine
│   │   ├── search.py         # Search engine
│   │   ├── assembler.py      # Presentation assembly
│   │   ├── pdf_assembler.py  # PDF assembly
│   │   └── pdf_processor.py  # PDF processing
│   └── templates/            # Jinja2 templates
├── migrations/               # SQL schema migrations
├── storage/                  # Local storage
│   ├── lightrag/            # LightRAG graph storage
│   ├── thumbnails/          # Slide thumbnails
│   ├── exports/             # Assembled presentations
│   ├── logs/                # Application logs
│   └── audit.db             # LLM audit log
├── scripts/                 # Utility scripts
├── tests/                   # Test suite
├── justfile                 # Just commands
├── pyproject.toml          # Project dependencies
└── README.md               # This file
```

## Troubleshooting

### Command Not Found: slidex

The `slidex` CLI command is only available inside the virtual environment.

**Solution 1: Use just commands (no activation needed)**
```bash
just ingest-file /path/to/presentation.pptx
```

**Solution 2: Activate virtual environment**
```bash
source .venv/bin/activate
slidex ingest file /path/to/presentation.pptx
```

### Ollama Connection Errors

- Ensure Ollama is running: `ollama serve`
- Check that models are downloaded: `ollama list`
- Verify connection: `curl http://localhost:11434/api/tags`

### Database Connection Errors

- Ensure PostgreSQL is running: `brew services list | grep postgresql`
- Check `DATABASE_URL` in config
- Initialize database: `just init-db`

### PDF Processing Issues

1. Check if LibreOffice is installed:
```bash
brew install libreoffice
```

2. Verify LibreOffice is in PATH:
```bash
which soffice
```

3. Enable PDF processing:
```bash
just enable-pdf
```

### Import Errors

- Ensure virtual environment is activated
- Reinstall dependencies: `just install`

## Starting Fresh with LightRAG

If you're upgrading from a previous version or want to start with a clean slate:

```bash
# Clean all existing data (database and LightRAG)
just clean-data

# Re-initialize database
just init-db

# Re-ingest your PowerPoint files
just ingest-folder /path/to/your/slides
```

All slides will be indexed into LightRAG's knowledge graph automatically during ingestion.

## Limitations

- **Dev mode focus**: Designed for local development, not optimized for large-scale production
- **Slide copying**: Best-effort formatting preservation (complex slides may lose some formatting)

## License

MIT License

## Contributing

This is a development project. Feel free to fork and modify for your needs.
