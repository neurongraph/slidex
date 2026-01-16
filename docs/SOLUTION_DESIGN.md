# Slidex Solution Design

## Overview

Slidex is a single-user Python application for managing PowerPoint slides with semantic search capabilities. It uses LightRAG, a graph-based retrieval system, to provide advanced semantic search with entity extraction and relationship mapping across slides.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Interface│    │   CLI Interface │    │   REST API      │
│   (Web UI)      │    │   (Command Line)│    │   (Flask)       │
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
                    │   (PostgreSQL, FAISS,   │
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
- **Audit Logging**: `slidex/core/audit_logger.py`

#### 4. Data Storage Layer
- **Metadata Storage**: PostgreSQL database
- **Vector Index**: FAISS for semantic search
- **LightRAG Storage**: Graph-based knowledge store
- **Local Storage**: Thumbnails, exports, logs

## Key Features Implementation

### 1. Ingestion Pipeline
- **File Discovery**: Recursively discover `.pptx` files
- **Duplicate Detection**: SHA256 hash + file size + mtime comparison
- **Slide Processing**: Text extraction, thumbnail generation, summary creation
- **Embedding Generation**: Ollama-based embeddings for semantic search
- **Metadata Persistence**: Store slide metadata in PostgreSQL

### 2. Search Engine
- **LightRAG Integration**: Graph-based retrieval with entity extraction
- **Multiple Query Modes**: naive, local, global, and hybrid search strategies
- **Semantic Search**: FAISS vector search combined with LightRAG graph traversal
- **Result Presentation**: Rich metadata display with previews

### 3. Assembly Engine
- **Slide Selection**: Multi-select from search results
- **Presentation Creation**: PowerPoint file assembly using python-pptx
- **Formatting Preservation**: Best-effort preservation of original formatting
- **Export Management**: Save assembled presentations to storage

### 4. Audit System
- **LLM Interaction Logging**: All LLM operations logged to SQLite
- **Full Auditability**: Complete trace of all operations for compliance
- **Debugging Support**: Detailed logs for troubleshooting

## Data Flow

The core data flow in Slidex is as follows:

1. **Ingestion**: PowerPoint files are ingested, with each slide saved as a separate file
2. **Text Extraction**: Slide content is extracted and processed
3. **PDF Conversion**: Full deck is converted to PDF for visual fidelity
4. **Individual Slide Processing**: Each slide is processed individually
5. **Embedding Generation**: Text is converted to embeddings using Ollama
6. **Storage**: Metadata and embeddings are stored in PostgreSQL and FAISS
7. **Search**: Users can search using natural language queries
8. **Assembly**: Selected slides can be assembled into new presentations (both PPTX and PDF)

### PDF Processing Flow

The PDF processing component provides enhanced visual fidelity by implementing a multi-stage conversion process:

1. **Full Deck to PDF**: When a PowerPoint presentation is ingested, the entire deck is converted to a PDF using LibreOffice. This ensures visual consistency and preserves complex slide elements.

2. **Individual Slide Extraction**: Each slide from the PDF is extracted as a separate PDF page, allowing for:
   - Thumbnail generation from PDF pages
   - Individual slide processing for search
   - Preservation of visual elements that might be lost in direct PPTX processing

3. **Slide Assembly**: When assembling new presentations, slides can be:
   - Assembled as PPTX files (using original slide data)
   - Assembled as PDF files (using extracted PDF pages)

This dual approach ensures that both semantic search capabilities and visual fidelity are maintained throughout the application.

## Technology Stack

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI (Web UI), Typer (CLI)
- **Database**: PostgreSQL (metadata), FAISS (vector search), SQLite (audit)
- **Vector Search**: FAISS (faiss-cpu)
- **Graph RAG**: LightRAG (lightrag-hku)
- **LLM Integration**: Ollama (local models)
- **File Processing**: python-pptx, Pillow, PyMuPDF

### Frontend
- **Templates**: Jinja2
- **UI Components**: HTML/CSS/JavaScript (minimal)

### Development Tools
- **Package Management**: uv
- **Build System**: Poetry
- **Task Runner**: Just
- **Testing**: pytest

## Configuration Management

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection URL
- `OLLAMA_HOST` / `OLLAMA_PORT`: Ollama server location
- `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: `nomic-embed-text`)
- `OLLAMA_SUMMARY_MODEL`: Summary model (default: `granite4:tiny-h`)
- `STORAGE_ROOT`: Base directory for thumbnails and exports
- `LIGHTRAG_WORKING_DIR`: LightRAG storage directory
- `LIGHTRAG_ENABLED`: Enable LightRAG (default: `True`)
- `LIGHTRAG_LLM_CONTEXT_SIZE`: Context size for LightRAG LLM (default: `32768`)
- `FAISS_INDEX_PATH`: Path to FAISS index file
- `TOP_K_RESULTS`: Default number of search results (default: 10)

## Security Considerations

### Single-User Design
- No authentication or authorization (single-user local app)
- No containerization (explicitly no Docker)
- No enterprise-grade features in this release

### Data Handling
- All data stored locally
- No cloud APIs or external services
- Local model usage (Ollama) for all processing
- Audit logging for full traceability

## Performance Considerations

### Indexing
- FAISS for fast vector search
- PostgreSQL indexing for metadata queries
- LightRAG graph for semantic relationships

### Memory Usage
- Local processing with minimal memory footprint
- Efficient vector storage and retrieval
- Caching strategies for frequently accessed data

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

## Future Enhancements

### Planned Improvements
1. Enhanced search capabilities with more sophisticated RAG
2. Improved UI/UX with modern web frameworks
3. Multi-user support and authentication
4. Containerization for easier deployment
5. Advanced formatting preservation in assembly
6. Export to other formats (PDF, etc.)
7. Cloud integration options

## Development Workflow

### Setup Process
1. Prerequisites check (Python 3.12+, PostgreSQL, Ollama)
2. Virtual environment creation
3. Dependency installation with uv
4. Database initialization
5. Model pulling from Ollama

### Development Commands
- `just setup`: Complete development setup
- `just run`: Start FastAPI development server
- `just test`: Run test suite
- `just ingest-file`: Ingest single file
- `just ingest-folder`: Ingest folder recursively
- `just pull-models`: Pull required Ollama models

## Testing Strategy

### Unit Tests
- Individual component testing
- Mocked external dependencies
- Database interaction testing

### Integration Tests
- End-to-end ingestion workflow
- Search and retrieval functionality
- Assembly and export processes

### System Tests
- Complete workflow testing
- Performance benchmarking
- Edge case handling

## Error Handling

### Common Error Types
- Database connection failures
- Ollama connection errors
- File access issues
- Model not found errors
- Memory constraints

### Recovery Strategies
- Graceful degradation
- Retry mechanisms
- Clear error messages
- Logging for debugging