# Slidex

Slidex is a single-user Python application for managing PowerPoint slides with semantic search capabilities. It ingests PowerPoint presentations, generates embeddings using local Ollama models, stores them in a FAISS vector index, and enables semantic search and assembly of slides into new presentations.

## Features

- **Ingest PowerPoint files**: Single files or entire folders (recursive)
- **Deduplication**: Automatic detection and skipping of duplicate files
- **Semantic search**: Find slides using natural language queries
- **Slide preview**: Thumbnails and summaries for each slide
- **Slide assembly**: Create new presentations from search results
- **Local models**: Uses Ollama for embeddings and summarization (no cloud APIs)
- **Audit logging**: All LLM interactions logged to SQLite for full auditability
- **Web UI**: Simple Flask-based interface for search and browsing
- **CLI**: Command-line interface for batch operations

## Prerequisites

- Python 3.12+
- PostgreSQL (for metadata storage)
- Ollama (running locally for embeddings and LLM)
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

**Alternative: Manual Setup**

If you prefer manual setup:
```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://localhost:5432/slidex
OLLAMA_HOST=http://localhost
OLLAMA_PORT=11434
LOG_LEVEL=INFO
EOF

# Initialize database
just init-db
```

## Configuration

Configuration is managed via `slidex/config.py` using Pydantic Settings. You can override defaults using environment variables or a `.env` file.

Key settings:
- `DATABASE_URL`: PostgreSQL connection URL
- `OLLAMA_HOST` / `OLLAMA_PORT`: Ollama server location
- `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: `nomic-embed-text`)
- `OLLAMA_SUMMARY_MODEL`: Summary model (default: `granite4:tiny-h`)
- `STORAGE_ROOT`: Base directory for thumbnails and exports
- `FAISS_INDEX_PATH`: Path to FAISS index file
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

#### Search

```bash
# Basic search
slidex search "machine learning algorithms"

# Search with custom result count
slidex search "data visualization" --top-k 20

# JSON output (for scripting)
slidex search "cloud architecture" --json
```

#### Assemble Presentations

```bash
# Assemble slides by ID
slidex assemble --slide-ids "uuid1,uuid2,uuid3" --output "my_presentation.pptx"

# Preserve slide order as provided
slidex assemble --slide-ids "uuid1,uuid2,uuid3" --preserve-order
```

### Web UI

Start the Flask development server:

```bash
just run
# Or manually:
FLASK_APP=slidex.api.app:app flask run
```

Then open your browser to http://localhost:5000

**Pages:**
- `/` - Search interface
- `/ingest` - Ingestion instructions
- `/decks` - View all ingested decks

### REST API

The Flask app exposes a REST API for programmatic access:

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
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "data science", "top_k": 10}'
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
│   │   └── app.py            # Flask application
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py           # Typer CLI
│   ├── core/
│   │   ├── __init__.py
│   │   ├── audit_logger.py   # SQLite audit logging
│   │   ├── database.py       # PostgreSQL operations
│   │   ├── ollama_client.py  # Ollama integration
│   │   ├── slide_processor.py # Text extraction & thumbnails
│   │   ├── vector_index.py   # FAISS index management
│   │   ├── ingest.py         # Ingestion engine
│   │   ├── search.py         # Search engine
│   │   └── assembler.py      # Presentation assembly
│   └── templates/            # Jinja2 templates
├── migrations/               # SQL schema migrations
├── storage/                  # Local storage
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
```

### Running Tests

```bash
just test
# Or manually:
pytest tests/ -v
```

## How It Works

1. **Ingestion**: PowerPoint files are parsed using `python-pptx`. Text is extracted from slides, thumbnails are generated with Pillow, and summaries are created using Ollama.

2. **Embeddings**: Text content is embedded using Ollama's `nomic-embed-text` model. Vectors are stored in a local FAISS index.

3. **Search**: Query text is embedded and compared against the FAISS index using cosine similarity. Results are ranked by similarity score.

4. **Assembly**: Selected slides are copied from original presentations into a new PowerPoint file, preserving formatting where possible.

5. **Audit**: All LLM interactions (embeddings and summaries) are logged to a SQLite database for full auditability.

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
