# Slidex - justfile for common commands

# Show available commands
default:
    @just --list

# Complete development environment setup
setup:
    ./scripts/setup.sh

# Sync dependencies using uv
sync:
    uv sync

# Install dependencies (alias for sync)
install:
    uv sync

# Pull required Ollama models
pull-models:
    @echo "Pulling Ollama models..."
    ollama pull nomic-embed-text
    ollama pull granite4:tiny-h
    @echo "✓ Models ready"

# Run the Flask development server
run:
    FLASK_APP=slidex.api.app:app FLASK_ENV=development uv run flask run --host=0.0.0.0 --port=5001

# Stop any running Flask instances (if backgrounded)
stop:
    pkill -f "flask run" || true

# Run all tests
test:
    uv run pytest tests/ -v

# Run tests with coverage
test-coverage:
    uv run pytest tests/ --cov=slidex --cov-report=html --cov-report=term

# Initialize database schema
init-db:
    uv run python scripts/init_db.py

# Grant database permissions for external tools (like DBeaver)
grant-permissions:
    uv run python scripts/grant_permissions.py

# Ingest a PowerPoint file
ingest-file FILE:
    uv run python -c "from slidex.core.ingest import ingest_engine; ingest_engine.ingest_file('{{FILE}}')"

# Ingest a folder of PowerPoint files
ingest-folder FOLDER RECURSIVE="True":
    uv run python -c "from slidex.core.ingest import ingest_engine; ingest_engine.ingest_folder('{{FOLDER}}', recursive={{RECURSIVE}})"

# Check system requirements
check:
    #!/usr/bin/env bash
    set +e
    echo "Checking system requirements..."
    
    # Check Python
    if command -v python3.12 > /dev/null 2>&1; then
        echo "✓ Python 3.12 found: $(python3.12 --version)"
    elif command -v python3.13 > /dev/null 2>&1; then
        echo "✓ Python 3.13 found: $(python3.13 --version)"
    elif command -v python3 > /dev/null 2>&1; then
        py_version=$(python3 --version 2>&1)
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
            echo "✓ $py_version"
        else
            echo "❌ $py_version (3.12+ required)"
            echo "   Install: brew install python@3.12 or use pyenv"
        fi
    else
        echo "❌ Python not found"
    fi
    
    
    # Check PostgreSQL
    if command -v psql > /dev/null 2>&1; then
        echo "✓ PostgreSQL found"
    else
        echo "❌ PostgreSQL not found"
    fi
    
    # Check Ollama
    if command -v ollama > /dev/null 2>&1; then
        echo "✓ Ollama found"
    else
        echo "❌ Ollama not found"
    fi
    
    # Check if Ollama is running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama running"
    else
        echo "⚠️  Ollama not running"
    fi

    # Optional: check vLLM reranker if enabled in .env
    if [ -f .env ]; then
        # shellcheck disable=SC1091
        . .env
        if [ "${VLLM_RERANKER_ENABLED}" = "true" ] || [ "${VLLM_RERANKER_ENABLED}" = "True" ]; then
            echo "Checking vLLM reranker (VLLM_RERANKER_ENABLED=true)..."
            RERANK_URL="${VLLM_RERANKER_URL:-http://localhost:8182/v1/rerank}"
            RERANK_MODEL="${VLLM_RERANKER_MODEL:-bge-reranker-v2-m3}"
            if curl -sS -X POST "$RERANK_URL" \
                -H "Content-Type: application/json" \
                -d '{"model":"'"$RERANK_MODEL"'","query":"health check","documents":["test"],"top_n":1}' \
                > /dev/null 2>&1; then
                echo "✓ vLLM reranker reachable at $RERANK_URL (model=$RERANK_MODEL)"
            else
                echo "⚠️  vLLM reranker not reachable at $RERANK_URL"
            fi
        fi
    fi
    
    # Check virtual environment
    if [ -f .venv/bin/python ]; then
        echo "✓ Virtual environment exists"
    else
        echo "⚠️  Virtual environment not found"
    fi

# Clean generated files
clean:
    rm -rf storage/thumbnails/* storage/exports/*
    rm -rf __pycache__ **/__pycache__ .pytest_cache
    find . -type d -name "*.egg-info" -exec rm -rf {} + || true

# Deep clean (including virtual environment and storage)
clean-all: clean
    rm -rf .venv
    rm -rf storage/
    rm -f .env
    rm -f uv.lock

# Format code
format:
    black slidex/ tests/

# Lint code
lint:
    ruff check slidex/ tests/

# View application logs
logs:
    tail -f storage/logs/slidex.log

# View audit logs
audit-logs:
    @echo "Recent LLM audit logs:"
    @sqlite3 storage/audit.db "SELECT timestamp, model_name, operation_type, duration_ms FROM llm_audit_log ORDER BY timestamp DESC LIMIT 20;" || echo "No audit logs found"

# Show database stats
db-stats:
    @echo "Database statistics:"
    @uv run python -c "from slidex.core.database import db; decks = db.get_all_decks(); print(f'Total decks: {len(decks)}')" || echo "Error connecting to database"

# Show FAISS index stats
index-stats:
    @echo "FAISS index statistics:"
    @uv run python -c "from slidex.core.vector_index import vector_index; print(vector_index.get_stats())" || echo "Error loading index"

# Show LightRAG index stats
lightrag-stats:
    @echo "LightRAG index statistics:"
    @uv run python -c "from slidex.core.lightrag_client import lightrag_client; import json; print(json.dumps(lightrag_client.get_stats(), indent=2))" || echo "Error loading LightRAG"

# Rebuild FAISS index from database
rebuild-index:
    uv run python scripts/rebuild_index.py

# Clean all data from database, FAISS index, and LightRAG (keeps schema)
clean-data:
    uv run python scripts/clean_data.py
    @echo "Cleaning LightRAG storage..."
    rm -rf storage/lightrag/*
    @echo "✓ LightRAG storage cleaned"

# Clean all data without confirmation prompt (dangerous!)
clean-data-force:
    uv run python scripts/clean_data.py --yes

# Commit and push changes to remote repository
push MESSAGE BRANCH="main":
    git add .
    git commit -m "{{MESSAGE}}"
    git push origin {{BRANCH}}

# Push with tags
push-tags:
    git push --tags

# Create and push a new release tag
release VERSION:
    #!/usr/bin/env bash
    echo "Creating release {{VERSION}}..."
    git tag -a "v{{VERSION}}" -m "Release version {{VERSION}}"
    git push origin "v{{VERSION}}"
    echo "✓ Release v{{VERSION}} created and pushed"
