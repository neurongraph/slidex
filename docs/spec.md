# Slidex — Specification (spec.md)

> **Purpose:** Slidex is a single-user Python application (dev-mode) that ingests PowerPoint (.pptx) decks (single files or recursively from folders), splits decks into per-slide records, generates local embeddings using installed Ollama models, stores embeddings in a local vector index (FAISS), persists slide metadata in PostgreSQL (without duplicating original files), enables semantic search and preview of relevant slides, and assembles chosen slides into a new PowerPoint.

---

## 1. Goals and Non-goals (updated)

### Goals (MVP)
- Ingest either an individual .pptx or all .pptx files found recursively under a specified folder.
- Do **not** duplicate storage of original files: metadata stores the absolute/or relative `original_path` reference to the original .pptx.
- For each slide, generate a small visual thumbnail (PNG) and store the thumbnail path in metadata, along with `title_header` and a short summary (10–20 words) extracted/generated from slide content.
- Create embeddings using local models served by **Ollama** and store them in a local FAISS index.
- Provide a simple Flask + Jinja web UI and a CLI for batch ingestion, search, preview, selection, and assemble.
- Assemble selected slides into a new .pptx preserving formatting as much as possible.

### Non-goals (dev release)
- No containerization (explicitly no Docker).  
- No authentication/authorization — single-user local app.  
- No enterprise-grade features (SSO, multi-tenant sharing, audit exports) in this stage.

---

## 2. Environment & Tooling
- **Language:** Python 3.11+.
- **Package & environment management:** Use **Poetry** for dependency management and a lightweight virtual environment (`venv`) for the developer environment. Provide a `pyproject.toml` and `poetry.lock`.
- **Run server:** Use **Flask** (development mode) with `flask run` or `gunicorn` for dev if desired. (No React — Jinja templates only.)
- **Local models:** Ollama (already installed) to host local embedding and LLM models for RAG (embedding + optional summarization).
- **Vector DB:** FAISS (local), persisted to disk; chosen for ease of local embedding and zero external dependencies.
- **Metadata DB:** PostgreSQL (user already has installed) — store slide and deck metadata, references to thumbnails and original file paths.
- **Slide processing:** `python-pptx` + `Pillow` (for thumbnail generation). Optionally `libreoffice --headless` can be used for higher-fidelity images and PDF conversion.

---

## 3. Ingest Modes & File Handling

**Modes**
- `ingest_file(path/to/file.pptx)` — ingest single file.
- `ingest_folder(path/to/folder, recursive=True)` — walk folder and sub-folders to discover `.pptx`.

**Duplicate avoidance**
- Before ingesting, compute a deterministic fingerprint for each file (e.g., SHA256 of the file bytes + file size + mtime). Use `decks.file_hash` in DB to detect existing ingestion. If the same file is already ingested (same hash), skip ingest.
- Store `original_path` (absolute or configured relative root) and `source_filename` in the `decks` table. Do **not** copy the original file into app storage.

**Slide assets**
- Thumbnails: generated small PNG (e.g., 320px width), saved under `storage/thumbnails/{deck_id}/{slide_index}.png`. The `slides` metadata will hold the thumbnail path.
- Single-slide pptx files: optional and only created if `create_single_slide_files=True`; otherwise not created to avoid duplication.

---

## 4. Metadata Schema (Postgres)

### `decks` table
- `deck_id` (UUID PK)
- `file_hash` (text)
- `original_path` (text) — location on disk
- `filename` (text)
- `uploader` (text) — optional local user name
- `uploaded_at` (timestamp)
- `slide_count` (int)
- `notes` (jsonb) — optional

### `slides` table
- `slide_id` (UUID PK)
- `deck_id` (FK)
- `slide_index` (int)
- `title_header` (text)
- `plain_text` (text)
- `summary_10_20_words` (text)
- `thumbnail_path` (text)
- `original_slide_position` (int)
- `created_at` (timestamp)

### `faiss_index` metadata table (optional)
- `slide_id` (UUID)
- `vector_id` (int) — the FAISS internal ID which maps to slide

Indexes: Create indices on `deck_id`, `file_hash`, and `slide_id` for performance.

---

## 5. Extraction & Embedding Pipeline (detailed)

1. **File discovery**: recursive walker discovers `.pptx`.
2. **Dedup check**: compute `file_hash`, check `decks` table; if new, insert deck record.
3. **Slide iteration** using `python-pptx`:
   - Extract text from shapes, tables, and speaker notes into `plain_text`.
   - Derive a `title_header`: prefer slide titles; fallback to first non-empty heading-like text.
   - Generate a short `summary_10_20_words` using Ollama LLM (prompt: "Summarize this slide in 10–20 words.").
   - Create a thumbnail via `Pillow` rendering of slide content (or using LibreOffice) and save path.
4. **Embedding input assembly**: `embedding_input = title_header + "
" + plain_text + "
" + summary`
   - Truncate intelligently to Ollama model limits.
5. **Embedding generation**: call Ollama embedding endpoint locally for chosen embedding model; receive vector.
6. **Store embedding**: insert vector into FAISS index and save mapping (slide_id <-> faiss vector id) to metadata table.
7. **Persist slide metadata**: insert into `slides` with thumbnail path and summary.

Batch ingestion will run synchronously in dev mode or in simple background threads if configured. Provide CLI flags for `--batch-size`, `--skip-ocr`, `--create-single-slide-files`.

---

## 6. Search, Preview & Assemble Flow

**Search**
- Query submitted via web UI or CLI.
- Convert query to vector using Ollama embedding model.
- Perform FAISS top-K search (configurable K, default 10).
- Retrieve slide metadata for results, return score and metadata (title_header, summary_10_20_words, thumbnail_path, deck filename, slide_index).

**Preview**
- Web UI shows thumbnail, title header, 10–20 word summary, and a short excerpt of plain_text.  
- Allow multi-select with checkboxes in results list.

**Assemble**
- Take selected `slide_ids` in either original deck order or user-specified order.
- Create a new `.pptx` by copying slide XML into a new Presentation object (attempt to preserve formatting). Use `python-pptx`'s slide cloning strategy or export/import slide shapes.
- Serve new `.pptx` for download from the Flask server; store in `storage/exports/{timestamp}_assembled.pptx`.

---

## 7. API & CLI (dev)

**CLI commands** (via `slidex` entrypoint):
- `slidex ingest file <path>`
- `slidex ingest folder <path> --recursive`
- `slidex search "query text" --top_k 10`
- `slidex assemble --slide-ids id1,id2,id3 --output out.pptx`

**Flask REST API (simple)**
- `POST /api/ingest/file` — body: `{ path: "/path/to/file.pptx" }`
- `POST /api/ingest/folder` — body: `{ path: "/path/to/folder", "recursive": true }`
- `POST /api/search` — `{ "query": "...", "top_k": 10 }` -> returns list of hits.
- `GET /api/slide/{slide_id}/preview` — returns thumbnail (static URL) + metadata.
- `POST /api/assemble` — `{ "slide_ids": [...], "order": [...] }` -> returns download URL.

Note: API is for local use only; no auth by design for the dev release.

---

## 8. Implementation Notes & Libraries
- `python-pptx` — slide parsing and assembly.
- `Pillow` — image processing (thumbnails).
- `faiss` (faiss-cpu) — vector index.
- `olllama` client or direct HTTP calls to Ollama local endpoint for embeddings and summarization. The models default to nomic-embed-text and granite4:tiny-h, but should be driven by config.py (configurable)
- `psycopg2` / `asyncpg` — Postgres client (sync mode is acceptable for dev).
- `Flask`, `Jinja2` — web UI.
- `click` or `typer` — CLI.

---

## 9. Dev Configuration (example)
- `config/dev.yaml` or environment variables for:
  - `DATABASE_URL` (postgres)
  - `OLLAMA_HOST` & `OLLAMA_PORT` (local Ollama)
  - `FAISS_INDEX_PATH` (disk path)
  - `STORAGE_ROOT` (base path for thumbnails & exports)
  - `BATCH_SIZE`
  - `LOG_LEVEL=DEBUG`

Provide a `scripts/setup_dev.sh` to create virtualenv, install via Poetry, initialize DB schema, and create a sample dataset.

---

## 10. Acceptance Criteria (revised)
- Ingest single file and folder recursively; skip duplicate files by hash.
- For each slide: title header, small thumbnail, and 10–20 words summary are present in metadata.
- Local Ollama embeddings are generated and stored in FAISS.
- Search returns relevant slides with preview; selected slides can be assembled into an exportable `.pptx`.
- App runs locally in dev without Docker using Poetry + venv.

---

## 11. Milestones (practical for dev)
1. Project skeleton, Poetry setup, dev config, DB migrations scripts.  
2. Implement file discovery and dedup logic.  
3. Implement slide splitting, text extraction, thumbnail creation, and metadata persistence.  
4. Integrate Ollama for summaries and embeddings and persist to FAISS.  
5. Implement search API/CLI and preview UI.  
6. Implement assemble/export.  
7. Polish UX and provide setup script and README for dev usage.

---

## 12. PDF Processing

Slidex includes optional PDF processing capabilities to enhance visual fidelity:

- **Full Deck Conversion**: PowerPoint presentations are converted to PDF using LibreOffice for consistent visual rendering
- **Individual Slide Extraction**: Each slide is extracted as a separate PDF page for thumbnail generation and search
- **Dual Format Assembly**: Assembled presentations can be created as both PPTX and PDF files
- **Visual Fidelity**: Complex slide elements like SmartArt diagrams and charts are preserved in PDF format

PDF processing is optional and requires LibreOffice to be installed on the system. When disabled, core functionality remains intact but visual fidelity may be reduced for complex slides.

---

## 4. Search & Retrieval

Slidex supports semantic search using two different approaches:

1. **FAISS-based search** - Uses local FAISS vector index with Ollama embeddings for fast retrieval
2. **LightRAG-based search** - Uses a knowledge graph built from slides with semantic search capabilities

### LightRAG Configuration

LightRAG is enabled by default and provides enhanced semantic search capabilities. It builds a knowledge graph from the slide content and can provide more context-aware search results.

### vLLM Reranker Integration

Slidex supports integration with vLLM-based rerankers for enhanced search results. When enabled, LightRAG will use the vLLM reranker to re-rank search results before returning them to the user.

To enable vLLM reranker:
1. Set `VLLM_RERANKER_ENABLED=true` in your configuration
2. Ensure your vLLM service is running on port 8182 with the `bge-reranker-v2-m3` model
3. The system will automatically use the reranker for LightRAG queries

This feature enhances the quality of search results by providing more accurate relevance scoring for retrieved documents.

---

*End of Slidex spec (dev).*

