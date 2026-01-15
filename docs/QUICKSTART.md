# Slidex - Quick Start Guide

This guide will get you up and running with Slidex in minutes.

## Prerequisites

Before starting, make sure you have:
- Python 3.12+
- PostgreSQL installed and running
- Ollama installed
- LibreOffice (for full PDF processing capabilities, optional but recommended)

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

**Note**: For full PDF processing capabilities, install LibreOffice:
```bash
brew install libreoffice
```

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

## Step 3: Configure vLLM Reranker (Optional)

If you want to use vLLM-based reranking for enhanced search results:

1. Start your vLLM service with the `bge-reranker-v2-m3` model on port 8182
2. Update your `.env` file to enable the reranker:
   ```
   VLLM_RERANKER_ENABLED=true
   ```

## Step 4: Activate Environment

```bash
source .venv/bin/activate
```

## Step 5: Choose Your Interface

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

## Step 6: Ingest Data

To ingest a single PowerPoint file:
```bash
just ingest-file path/to/your/presentation.pptx
```

To ingest all PowerPoint files in a folder recursively:
```bash
just ingest-folder path/to/your/presentation/folder
```

## Step 7: Search and Preview

Start the web UI:
```bash
just run
```

Visit `http://localhost:5000` to search and preview slides.

## Step 8: Assemble Selected Slides

Select slides from the search results and click "Assemble" to create a new PowerPoint presentation.

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
```

# 4. Your new presentation is in storage/exports/
ls storage/exports/

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

## Troubleshooting

If you encounter issues:
- Check that Ollama is running: `ollama serve`
- Verify that required models are pulled: `ollama list`
- Check the logs in `storage/logs/`
- Run `just setup` to reinitialize the environment

Happy slide management! 🎉
