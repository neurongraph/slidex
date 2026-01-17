# Database Migrations

## Current Schema

The database schema is now consolidated in `init_schema.sql`, which is idempotent and can be run multiple times safely.

To initialize the database, run:
```bash
just init-db
# or
python scripts/init_db.py
```

## Migration History

The following individual migration files have been consolidated into `init_schema.sql`:

- `001_initial_schema.sql` - Initial tables (decks, slides, faiss_index)
- `002_add_slide_files.sql` - Added slide_file_path column
- `003_add_pdf_support.sql` - Added PDF support columns

These files are kept for historical reference but are no longer used by the initialization script.

## Schema Overview

### Tables

**decks**
- Stores metadata about ingested PowerPoint presentations
- Tracks file hash for deduplication
- Stores original file path and uploader information

**slides**
- Stores metadata for individual slides
- Includes text content, summaries, and thumbnail paths
- Supports both PPTX and PDF formats for individual slides
- Tracks complexity score for determining PDF requirement

**faiss_index**
- Maps slide IDs to FAISS vector IDs for semantic search
- Used when LightRAG is disabled (legacy mode)

### Key Features

- **Idempotent**: Can be run multiple times without errors
- **UUID Support**: Uses PostgreSQL uuid-ossp extension
- **Automatic Timestamps**: created_at and updated_at managed by triggers
- **Cascading Deletes**: Slides and index entries deleted when deck is removed
- **Comprehensive Indexes**: Optimized for common query patterns