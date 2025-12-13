# Slidex - Quick Start Guide

This guide will get you up and running with Slidex in minutes.

## Prerequisites

Before starting, make sure you have:
- Python 3.12+
- PostgreSQL installed and running
- Ollama installed

## Step 1: Install and Setup

Run the automated setup:

```bash
just setup
```

This will:
- Check prerequisites (Python 3.12+, PostgreSQL, Ollama)
- Create a virtual environment
- Install dependencies with uv
- Create .env configuration file
- Initialize the database
- Create necessary directories

## Step 2: Start Ollama and Pull Models

If not already running, start Ollama:

```bash
ollama serve
```

In another terminal, pull the required models:

```bash
just pull-models
```

Or manually:
```bash
ollama pull nomic-embed-text
ollama pull granite4:tiny-h
```

## Step 3: Activate Environment

```bash
source .venv/bin/activate
```

## Step 4: Choose Your Interface

### Option A: Web Interface

Start the Flask server:

```bash
just run
```

Open your browser to: http://localhost:5000

### Option B: Command Line

Use the CLI directly:

```bash
# Get help
slidex --help

# Ingest a presentation
slidex ingest file /path/to/presentation.pptx

# Search for slides
slidex search "machine learning"

# Assemble slides
slidex assemble --slide-ids "uuid1,uuid2" --output "new_deck.pptx"
```

## Example Workflow

Here's a complete example workflow:

```bash
# 1. Ingest some presentations
slidex ingest folder ~/Documents/Presentations --recursive

# 2. Search for relevant slides
slidex search "data visualization techniques" --top-k 10

# 3. Note the slide IDs from search results, then assemble
slidex assemble \
  --slide-ids "abc123,def456,ghi789" \
  --output "data_viz_compilation.pptx" \
  --preserve-order

# 4. Your new presentation is in storage/exports/
ls storage/exports/
```

## Web UI Workflow

1. Navigate to http://localhost:5000
2. Go to **Ingest** page for instructions on ingesting files
3. Go to **Search** page
4. Enter a search query (e.g., "cloud architecture")
5. Select slides by clicking checkboxes
6. Click "Assemble Presentation"
7. Download your new presentation

## Troubleshooting

### "Database connection failed"
```bash
# Check PostgreSQL is running
pg_isready

# Re-initialize database
just init-db
```

### "Ollama connection refused"
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### "Model not found"
```bash
# Pull required models
ollama pull nomic-embed-text
ollama pull granite4:tiny-h
```

### "Command not found: slidex"
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Reinstall
just install
```

## What's Next?

- Read the full [README.md](README.md) for detailed documentation
- Check configuration options in `slidex/config.py`
- View audit logs: `sqlite3 storage/audit.db "SELECT * FROM llm_audit_log LIMIT 10;"`
- Browse ingested decks at http://localhost:5000/decks

## Common Commands

```bash
# Show all available commands
just

# Complete setup from scratch
just setup

# Pull Ollama models
just pull-models

# Check system requirements
just check

# Run Flask server
just run

# Run tests
just test

# View application logs
just logs

# View LLM audit logs
just audit-logs

# Show database stats
just db-stats

# Show FAISS index stats
just index-stats

# Clean generated files
just clean

# Deep clean (remove everything)
just clean-all
```

Happy slide management! 🎉
