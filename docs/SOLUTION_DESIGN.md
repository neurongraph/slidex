# Slidex Solution Design

## Overview

Slidex is a single-user Python application for managing PowerPoint slides with semantic search capabilities. It uses LightRAG, a graph-based retrieval system, to provide advanced semantic search with entity extraction and relationship mapping across slides.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Interface│    │   CLI Interface │    │   REST API      │
│   (Web UI)      │    │   (Command Line)│    │   (FastAPI)     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   Core Application      │
                    │   (slidex/core/)        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   Data Processing       │
                    │   (Ingest, Search,     │
                    │    Assemble)           │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │   Data Storage          │
                    │   (PostgreSQL,          │
                    │    LightRAG)           │
                    └─────────────────────────┘
```

### Component Breakdown

#### 1. User Interface Layer
- **Web UI**: FastAPI-based interface with Jinja2 templates
- **CLI**: Typer-based command-line interface
- **REST API**: Programmatic access to core functionality

#### 2. Core Application Layer
- **Configuration Management**: `slidex/config.py` using Pydantic Settings
- **Logging**: Loguru for structured logging
- **Database Operations**: PostgreSQL integration via psycopg2
- **Ollama Integration**: Client for local LLM operations
- **LightRAG Integration**: Wrapper for graph-based retrieval
- **PDF Processing**: Component for converting between PPTX and PDF formats

#### 3. Data Processing Layer
- **Ingestion Engine**: `slidex/core/ingest.py`
- **Slide Processing**: `slidex/core/slide_processor.py`
- **Search Engine**: `slidex/core/search.py`
- **Assembly Engine**: `slidex/core/assembler.py`
- **PDF Assembly**: `slidex/core/pdf_assembler.py`
- **Audit Logging**: `slidex/core/audit_logger.py`

#### 4. Data Storage Layer
- **Metadata Storage**: PostgreSQL database
- **LightRAG Storage**: Graph-based knowledge store for semantic search
- **Local Storage**: Thumbnails, exports, logs

## Key Features Implementation

### 1. Ingestion Pipeline

**Process Flow:**
1. **File Discovery**: Recursively discover `.pptx` files
2. **Duplicate Detection**: SHA256 hash + file size + mtime comparison
3. **Slide Processing**: Text extraction, thumbnail generation, summary creation
4. **Individual Slide Files**: Each slide saved as standalone `.pptx` file
5. **PDF Conversion**: Full deck converted to PDF (if LibreOffice available)
6. **Embedding Generation**: Ollama-based embeddings for semantic search
7. **LightRAG Indexing**: Content inserted into knowledge graph
8. **Metadata Persistence**: Store slide metadata in PostgreSQL

**Duplicate Avoidance:**
- Compute deterministic fingerprint: SHA256(file bytes) + file size + mtime
- Check `decks.file_hash` in database before ingestion
- Skip if already ingested

**Individual Slide Files:**
- Each slide saved as `storage/slides/{slide_id}.pptx`
- Benefits:
  - Direct inspection in PowerPoint for debugging
  - RAG integration with individual files
  - No dependency on original file paths
  - Simplified assembly process
- Trade-offs:
  - More disk space usage
  - No deduplication of images across slides

### 2. Search Engine

**LightRAG-Based Search:**
- **Naive Mode**: Simple semantic search without graph traversal
- **Local Mode**: Retrieves contextually related information from nearby graph nodes
- **Global Mode**: Utilizes global knowledge across entire knowledge graph
- **Hybrid Mode**: Combines local and global strategies (recommended)

**vLLM Reranker Integration:**
- Optional reranking using vLLM service
- Enhances search result quality with better relevance scoring
- Requires separate vLLM service running with `BAAI/bge-reranker-v2-m3` model
- Default URL: `http://localhost:8182/v1/rerank`

### 3. Assembly Engine

**Process:**
1. **Slide Selection**: Multi-select from search results
2. **File Loading**: Load individual slide files (preferred) or extract from original decks
3. **Presentation Creation**: Assemble using python-pptx
4. **Formatting Preservation**: Best-effort XML deep-copying
5. **Dual Format Export**: Save as both PPTX and PDF (if enabled)

**Formatting Preservation:**
- Uses XML deep-copying for slide shapes
- Preserves layouts, colors, fonts where possible
- Complex elements (SmartArt, charts) may lose some formatting

### 4. PDF Processing

**Full Deck to PDF:**
- Converts entire PowerPoint to PDF using LibreOffice
- Ensures visual consistency
- Preserves complex slide elements

**Individual Slide Extraction:**
- Each slide extracted as separate PDF page
- Used for thumbnail generation
- Maintains visual fidelity

**PDF Assembly:**
- Assembled presentations can be exported as PDF
- Uses PyMuPDF for PDF manipulation
- Combines individual slide PDFs into single document

### 5. Audit System

**LLM Interaction Logging:**
- All Ollama API calls logged to SQLite (`storage/audit.db`)
- Tracks embeddings, summaries, entity extraction
- Records input, output, timing, model used
- Provides full auditability for compliance

**Audit Database Schema:**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    operation TEXT,
    model TEXT,
    input_text TEXT,
    output_text TEXT,
    duration_ms REAL,
    session_id TEXT
);
```

## Data Flow

### Ingestion Flow

```
PowerPoint File
    ↓
File Hash Check (Deduplication)
    ↓
Slide Extraction (python-pptx)
    ↓
├─→ Text Extraction
├─→ Individual Slide File Creation
├─→ Thumbnail Generation (LibreOffice/Pillow)
├─→ Summary Generation (Ollama LLM)
└─→ PDF Conversion (LibreOffice)
    ↓
Embedding Generation (Ollama)
    ↓
└─→ LightRAG Indexing (Knowledge Graph)
    ↓
Metadata Storage (PostgreSQL)
```

### Search Flow

```
User Query
    ↓
Query Embedding (Ollama)
    ↓
LightRAG Search (Graph Traversal)
    ↓
├─→ Entity Extraction
├─→ Relationship Discovery
└─→ Context-Aware Retrieval
    ↓
Optional Reranking (vLLM)
    ↓
Metadata Enrichment (PostgreSQL)
    ↓
Results with Thumbnails & Summaries
```

### Assembly Flow

```
Selected Slide IDs
    ↓
Database Metadata Lookup
    ↓
Individual Slide File Loading
    ↓
New Presentation Creation (python-pptx)
    ↓
├─→ PPTX Export
└─→ PDF Export (if enabled)
    ↓
Download/Storage
```

## Technology Stack

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI (Web UI), Typer (CLI)
- **Database**: PostgreSQL (metadata), SQLite (audit)
- **Graph RAG**: LightRAG (lightrag-hku) for semantic search
- **LLM Integration**: Ollama (local models)
- **File Processing**: python-pptx, Pillow, PyMuPDF, LibreOffice

### Frontend
- **Templates**: Jinja2
- **UI Components**: HTML/CSS/JavaScript (minimal)

### Development Tools
- **Package Management**: uv
- **Build System**: Poetry
- **Task Runner**: Just
- **Testing**: pytest

## Configuration Management

### Pydantic Settings

All configuration managed through `slidex/config.py`:

```python
class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://localhost:5432/slidex"
    
    # Ollama
    OLLAMA_HOST: str = "http://localhost"
    OLLAMA_PORT: int = 11434
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_SUMMARY_MODEL: str = "granite4:tiny-h"
    
    # LightRAG
    LIGHTRAG_ENABLED: bool = True
    LIGHTRAG_WORKING_DIR: str = "storage/lightrag"
    LIGHTRAG_LLM_CONTEXT_SIZE: int = 32768
    
    # vLLM Reranker
    VLLM_RERANKER_ENABLED: bool = True
    VLLM_RERANKER_URL: str = "http://localhost:8182/v1/rerank"
    VLLM_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    
    # PDF Processing
    PDF_CONVERSION_ENABLED: bool = True
    LIBREOFFICE_PATH: str = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    PDF_DPI: int = 150
    
    # Storage
    STORAGE_ROOT: str = "storage"
    
    # Search
    TOP_K_RESULTS: int = 10
    
    # Server (FastAPI/Uvicorn)
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 5001
    SERVER_DEBUG: bool = True
```

### Environment Variables

Configuration can be overridden via:
1. `.env` file in project root
2. Environment variables

**Note:** The application uses Pydantic Settings with `.env` file support. YAML configuration is not currently implemented.

## Database Schema

### Decks Table
```sql
CREATE TABLE decks (
    deck_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_hash TEXT NOT NULL UNIQUE,
    original_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    uploader TEXT,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    slide_count INTEGER NOT NULL DEFAULT 0,
    notes JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Slides Table
```sql
CREATE TABLE slides (
    slide_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    deck_id UUID NOT NULL REFERENCES decks(deck_id) ON DELETE CASCADE,
    slide_index INTEGER NOT NULL,
    title_header TEXT,
    plain_text TEXT,
    summary_10_20_words TEXT,
    thumbnail_path TEXT,
    slide_file_path TEXT,
    slide_pdf_path TEXT,
    requires_pdf BOOLEAN DEFAULT FALSE,
    complexity_score INTEGER DEFAULT 0,
    original_slide_position INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(deck_id, slide_index)
);
```


## Global Singleton Instances

The codebase uses singleton pattern for core components:

```python
# Configuration
from slidex.config import settings

# Logging
from slidex.logging_config import logger

# Database
from slidex.core.database import db

# Vector Index
from slidex.core.vector_index import vector_index

# Ollama Client
from slidex.core.ollama_client import ollama_client

# LightRAG Client
from slidex.core.lightrag_client import lightrag_client

# Audit Logger
from slidex.core.audit_logger import audit_logger

# Processing Engines
from slidex.core.ingest import ingest_engine
from slidex.core.search import search_engine
from slidex.core.slide_processor import slide_processor
from slidex.core.assembler import slide_assembler
```

## Storage Structure

```
storage/
├── slides/              # Individual slide files ({slide_id}.pptx)
├── slides_pdf/          # Individual slide PDFs ({slide_id}.pdf)
├── thumbnails/          # Slide thumbnails (organized by deck_id)
├── exports/             # Assembled presentations
├── logs/                # Application logs
├── lightrag/            # LightRAG knowledge graph
└── audit.db             # LLM audit database
```

## Security Considerations

### Single-User Design
- No authentication or authorization
- No containerization (explicitly no Docker)
- No enterprise-grade features in this release

### Data Handling
- All data stored locally
- No cloud APIs or external services
- Local model usage (Ollama) for all processing
- Audit logging for full traceability

## Performance Considerations

### Indexing
- LightRAG for graph-based semantic search
- PostgreSQL indexing for metadata queries
- LightRAG graph for semantic relationships

### Memory Usage
- Local processing with minimal memory footprint
- Efficient vector storage and retrieval
- Caching strategies for frequently accessed data

### Scalability
- Designed for single-user local use
- Not optimized for large-scale deployment
- Suitable for personal slide libraries (thousands of slides)

## Development Workflow

### Setup Process
1. Prerequisites check (Python 3.12+, PostgreSQL, Ollama)
2. Virtual environment creation
3. Dependency installation with uv
4. Database initialization
5. Model pulling from Ollama

### Development Commands
```bash
just setup          # Complete development setup
just run            # Start FastAPI development server
just test           # Run test suite
just ingest-file    # Ingest single file
just ingest-folder  # Ingest folder recursively
just pull-models    # Pull required Ollama models
just clean-data     # Clean all data and restart fresh
```

## Testing Strategy

### Unit Tests
- Individual component testing
- Mocked external dependencies (Ollama, PostgreSQL)
- Database interaction testing

### Integration Tests
- End-to-end ingestion workflow
- Search and retrieval functionality
- Assembly and export processes

### Test Coverage
- Run with: `just test-coverage`
- HTML report generated in `htmlcov/`

## Error Handling

### Common Error Types
- Database connection failures
- Ollama connection errors
- File access issues
- Model not found errors
- Memory constraints
- LibreOffice not available (PDF processing)

### Recovery Strategies
- Graceful degradation (PDF processing optional)
- Retry mechanisms for transient failures
- Clear error messages with actionable guidance
- Comprehensive logging for debugging

## Deployment Model

### Development Mode
- Single-user local application
- No containerization
- Local database and storage
- Development server with FastAPI

### Production Considerations
- Not designed for production deployment
- Single-user focus
- No scalability features
- No authentication/authorization

## Future Enhancements

### Planned Improvements
1. Enhanced search capabilities with more sophisticated RAG
2. Improved UI/UX with modern web frameworks
3. Multi-user support and authentication
4. Containerization for easier deployment
5. Advanced formatting preservation in assembly
6. Cloud integration options
7. Batch processing optimizations
8. Enhanced graph visualization

## API Reference

### REST API Endpoints

**Ingestion:**
- `POST /api/ingest/file` - Ingest single file
- `POST /api/ingest/folder` - Ingest folder (recursive option)

**Search:**
- `POST /api/search` - Semantic search with LightRAG
  - Parameters: `query`, `top_k`, `mode` (naive/local/global/hybrid)

**Assembly:**
- `POST /api/assemble` - Assemble selected slides
  - Parameters: `slide_ids`, `preserve_order`

**Download:**
- `GET /api/download/{filename}` - Download assembled presentation

**Metadata:**
- `GET /api/decks` - List all decks
- `GET /api/deck/{deck_id}` - Get deck details
- `GET /api/slide/{slide_id}` - Get slide details

### CLI Commands

**Ingestion:**
```bash
slidex ingest file <path>
slidex ingest folder <path> --recursive
```

**Search:**
```bash
slidex search "query" --top-k 10 --mode hybrid
```

**Assembly:**
```bash
slidex assemble --slide-ids "id1,id2" --output "result.pptx"
```

## Troubleshooting Guide

### Common Issues

**1. Command not found: slidex**
- Solution: Activate virtual environment or use `just` commands

**2. Ollama connection errors**
- Check Ollama is running: `ollama serve`
- Verify models: `ollama list`

**3. Database connection errors**
- Check PostgreSQL is running
- Verify DATABASE_URL in config
- Run: `just init-db`

**4. PDF processing disabled**
- Install LibreOffice: `brew install libreoffice`
- Enable: `just enable-pdf`

**5. Import errors**
- Activate venv: `source .venv/bin/activate`
- Reinstall: `just install`

## Monitoring and Debugging

### Logging
- Application logs: `storage/logs/slidex.log`
- View live: `just logs`
- Log level controlled by `LOG_LEVEL` env var

### Audit Logs
- LLM interactions: `storage/audit.db`
- View recent: `just audit-logs`
- Query with SQLite: `sqlite3 storage/audit.db`

### Database Statistics
- View stats: `just db-stats`
- Shows deck count, slide count, index size

### LightRAG Statistics
- View graph statistics and knowledge base info

## Best Practices

### Ingestion
- Use `just ingest-folder` for batch processing
- Monitor logs during large ingestions
- Clean data before re-ingesting: `just clean-data`

### Search
- Use hybrid mode for best results
- Adjust `top_k` based on needs
- Enable vLLM reranker for enhanced quality

### Assembly
- Preview slides before assembling
- Use `preserve_order` for specific ordering
- Check both PPTX and PDF outputs

### Maintenance
- Regular database backups
- Monitor storage usage
- Clean old exports periodically
- Review audit logs for LLM usage

---

*End of Solution Design Document*