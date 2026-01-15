# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Commands

### Setup & Installation
```bash
# Complete environment setup (creates venv, installs deps, creates .env, initializes DB)
just setup

# Install/sync dependencies only
just install  # or: uv sync

# Initialize database schema
just init-db

# Pull required Ollama models
just pull-models
```

### Development
```bash
# Run Flask development server
just run

# Run all tests
just test

# Run tests with coverage
just test-coverage

# Lint code
just lint

# Format code
just format

# Check system requirements
just check

# Check PDF processing status
just check-pdf

# Enable PDF processing
just enable-pdf

# Disable PDF processing
just disable-pdf
```

### Testing
- Framework: pytest
- Run all tests: `just test` or `uv run pytest tests/ -v`
- Run with coverage: `just test-coverage`
- Test files are located in `tests/` directory

### Ingestion (CLI)
```bash
# Ingest single file (using just)
just ingest-file /path/to/file.pptx

# Ingest folder recursively (using just)
just ingest-folder /path/to/folder

# Using slidex CLI directly (requires venv activation)
slidex ingest file /path/to/file.pptx
slidex ingest folder /path/to/folder --recursive
```

### Search & Assembly (CLI)
```bash
# Search (requires venv activation)
slidex search "query text" --top-k 10
slidex search "query" --json  # JSON output

# Assemble slides (requires venv activation)
slidex assemble --slide-ids "id1,id2,id3" --output "output.pptx"
```

### Utilities
```bash
# View logs
just logs
just audit-logs

# Database & index stats
just db-stats
just index-stats

# Rebuild FAISS index from database
just rebuild-index

# Clean temporary files
just clean

# Deep clean (removes venv, storage, .env)
just clean-all
```

## Architecture Overview

### Core Data Flow
1. **Ingestion Pipeline**: PowerPoint files → Text extraction → **Individual slide file creation** → Thumbnail generation → LLM summarization → Embedding generation → FAISS index + PostgreSQL storage
2. **Search Pipeline**: Query text → Embedding generation → FAISS similarity search → Database metadata lookup → Ranked results
3. **Assembly Pipeline**: Slide IDs → Database lookup → **Individual slide file loading** → New PowerPoint creation

### Key Components

#### Configuration (\`slidex/config.py\`)
- Central Pydantic-based configuration system (global \`settings\` instance)
- All settings configurable via environment variables or \`.env\` file
- Key settings: \`DATABASE_URL\`, \`OLLAMA_HOST\`, \`OLLAMA_PORT\`, model names, storage paths
- Access via: \`from slidex.config import settings\`

#### Logging (\`slidex/logging_config.py\`)
- Centralized loguru setup (global \`logger\` instance)
- All modules use: \`from slidex.logging_config import logger\`
- Logs to both console and file (\`storage/logs/slidex.log\`)
- Log level controlled by \`LOG_LEVEL\` env var

#### Audit Logging (\`slidex/core/audit_logger.py\`)
- All LLM interactions logged to SQLite (\`storage/audit.db\`)
- Tracks embeddings and summaries with full input/output/timing
- Global instance: \`audit_logger\`
- Provides full auditability of LLM usage

#### Database (\`slidex/core/database.py\`)
- PostgreSQL for metadata storage
- Schema: \`decks\`, \`slides\`, \`faiss_index\` tables
- Context manager: \`get_db_connection()\` handles transactions
- Global instance: \`db\` with helper methods

#### Vector Index (\`slidex/core/vector_index.py\`)
- FAISS index for embeddings (IndexFlatL2 for exact search)
- Stored at \`storage/faiss_index.bin\` with metadata file
- Global instance: \`vector_index\`
- Syncs with database on load to prevent duplicate vector IDs

#### Ollama Client (\`slidex/core/ollama_client.py\`)
- Wrapper for Ollama API calls
- Two operations: \`generate_embedding()\` and \`generate_summary()\`
- Default models: \`nomic-embed-text\` (embeddings), \`granite4:tiny-h\` (summaries)
- All calls automatically audited via \`audit_logger\`
- Global instance: \`ollama_client\`

#### Ingestion Engine (\`slidex/core/ingest.py\`)
- File hash-based deduplication (SHA256 + file metadata)
- Processes: text extraction → **individual slide file creation** → thumbnail → summary → embedding → storage
- Each slide is saved as standalone .pptx file in \`storage/slides/{slide_id}.pptx\`
- Batch processing support for folders (recursive/non-recursive)
- Global instance: \`ingest_engine\`

#### Search Engine (\`slidex/core/search.py\`)
- Semantic search using FAISS + Ollama embeddings
- Converts FAISS distances to similarity scores
- Returns enriched results with slide metadata
- Global instance: \`search_engine\`

#### Slide Processor (\`slidex/core/slide_processor.py\`)
- Text extraction from PowerPoint slides using python-pptx
- Thumbnail generation (LibreOffice preferred, Pillow fallback)
- **Individual slide file creation**: \`save_slide_as_file()\` extracts single slides as standalone .pptx files
- Global instance: \`slide_processor\`

#### Assembler (\`slidex/core/assembler.py\`)
- Creates new PowerPoint from selected slides using python-pptx
- **Prefers individual slide files** (\`slide_file_path\`) when available, falls back to original deck files
- Preserves formatting using XML deep-copying
- Global instance: \`slide_assembler\`

### Interfaces

#### CLI (\`slidex/cli/main.py\`)
- Typer-based command-line interface
- Entry point: \`slidex\` command (defined in \`pyproject.toml\`)
- Commands: \`ingest\`, \`search\`, \`assemble\`, \`version\`

#### Web API (\`slidex/api/app.py\`)
- Flask-based REST API and web UI
- API endpoints: \`/api/ingest/file\`, \`/api/ingest/folder\`, \`/api/search\`, \`/api/assemble\`
- Web pages: \`/\` (search), \`/ingest\`, \`/decks\`
- Templates in \`slidex/templates/\`

### Global Singleton Instances
The codebase uses singleton pattern extensively. Key globals to import:
- \`settings\` from \`slidex.config\`
- \`logger\` from \`slidex.logging_config\`
- \`db\` from \`slidex.core.database\`
- \`vector_index\` from \`slidex.core.vector_index\`
- \`ollama_client\` from \`slidex.core.ollama_client\`
- \`audit_logger\` from \`slidex.core.audit_logger\`
- \`ingest_engine\` from \`slidex.core.ingest\`
- \`search_engine\` from \`slidex.core.search\`
- \`slide_processor\` from \`slidex.core.slide_processor\`
- \`slide_assembler\` from \`slidex.core.assembler\`

### Database Schema
Schema defined in \`migrations/001_initial_schema.sql\` and \`migrations/002_add_slide_files.sql\`:
- \`decks\` table: file_hash (unique), original_path, filename, slide_count, uploader
- \`slides\` table: references deck_id, stores text, summary, thumbnail_path, **slide_file_path** (path to individual slide .pptx)
- \`faiss_index\` table: maps slide_id to FAISS vector_id

## Development Notes

### Prerequisites
- Python 3.12+ (project uses 3.13.x virtual env per user rules)
- PostgreSQL running locally (default: \`postgresql://localhost:5432/slidex\`)
- Ollama running locally with models: \`nomic-embed-text\`, \`granite4:tiny-h\`
- uv package manager

### Environment Variables
Key variables in \`.env\`:
- \`DATABASE_URL\`: PostgreSQL connection string
- \`OLLAMA_HOST\`, \`OLLAMA_PORT\`: Ollama server location
- \`LOG_LEVEL\`: Logging verbosity (DEBUG, INFO, etc.)

### Storage Structure
```
storage/
├── slides/              # Individual slide files ({slide_id}.pptx)
├── thumbnails/          # Slide thumbnails (organized by deck_id)
├── exports/             # Assembled presentations
├── logs/                # Application logs
├── audit.db             # LLM audit database
└── faiss_index.bin      # FAISS vector index
```

### Testing Strategy
- Use pytest framework
- Tests should cover ingestion, search, and assembly workflows
- Mock Ollama calls in tests to avoid external dependencies

### Ollama Dependency
All semantic functionality requires Ollama running:
- Check with: \`curl http://localhost:11434/api/tags\`
- Start with: \`ollama serve\`
- Models must be pulled before use: \`just pull-models\`

### Individual Slide Files Feature
As of the latest refactoring, each slide is stored as a standalone .pptx file:

**Benefits:**
- **Debugging**: Each slide can be opened directly in PowerPoint for inspection
- **RAG Integration**: Individual files can be ingested into advanced RAG systems like LightRAG
- **Portability**: No dependency on original file paths; slides are self-contained
- **Simplicity**: Assembly is simpler (just concatenate single-slide files)

**Implementation:**
- During ingestion, each slide is extracted and saved as `storage/slides/{slide_id}.pptx`
- Database stores `slide_file_path` column for each slide
- Assembly prefers individual slide files when available, falls back to original files
- Backward compatible with existing data (NULL slide_file_path uses old method)

**Trade-offs:**
- More disk space (each slide is a full .pptx with embedded resources)
- Deduplication of images across slides is not possible
- Extra processing step during ingestion

### Deduplication
Files are deduplicated using SHA256 hash + file size + modification time. The same file moved or renamed will be treated as new unless content/size/mtime are identical.

### Adding New Features
When adding features that interact with LLMs:
1. Use \`ollama_client\` for all Ollama API calls
2. Pass \`session_id\` parameter for audit grouping
3. All calls are automatically logged to \`audit.db\`

When adding new configuration:
1. Add to \`Settings\` class in \`slidex/config.py\`
2. Document in docstrings with default values
3. Access via global \`settings\` instance

When adding new database tables/columns:
1. Create new migration SQL file in \`migrations/\`
2. Update \`scripts/init_db.py\` to run new migration
3. Add corresponding database methods in \`slidex/core/database.py\`
