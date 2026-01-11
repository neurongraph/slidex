#!/usr/bin/env bash
# Development setup script for Slidex

set -e  # Exit on error

echo "🚀 Setting up Slidex development environment..."

# Check Python version
echo "Checking Python version..."
# Try python3 command
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    echo "❌ Error: Python 3 not found"
    exit 1
fi

python_version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
if ! $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    echo "❌ Error: Python 3.9+ is required (found $python_version)"
    echo "   Install with: brew install python@3.9 or use pyenv"
    exit 1
fi
echo "✓ Python version OK: $python_version ($PYTHON_CMD)"

# Check PostgreSQL
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  Warning: psql not found. Make sure PostgreSQL is installed."
else
    echo "✓ PostgreSQL client found"
fi

# Check Ollama
echo "Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "❌ Error: Ollama not found. Install from https://ollama.ai"
    exit 1
fi
echo "✓ Ollama found"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Warning: Ollama not running. Start with: ollama serve"
else
    echo "✓ Ollama is running"
fi

# Check if uv is installed
echo "Checking uv..."
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv not found. Install with: pip install uv"
    exit 1
fi
echo "✓ uv found"

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Install dependencies using uv sync
echo "Installing dependencies with uv sync..."
uv sync
echo "✓ Dependencies installed"

# Create .env if needed
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'ENVEOF'
DATABASE_URL=postgresql://localhost:5432/slidex
OLLAMA_HOST=http://localhost
OLLAMA_PORT=11434
LOG_LEVEL=DEBUG
ENVEOF
    echo "✓ .env file created"
else
    echo "✓ .env file exists"
fi

# Create storage directories
echo "Creating storage directories..."
mkdir -p storage/{thumbnails,exports,logs}
echo "✓ Storage directories created"

# Initialize database
echo "Initializing database..."
if uv run scripts/init_db.py; then
    echo "✓ Database initialized"
else
    echo "⚠️  Warning: Database initialization failed"
    echo "   Make sure PostgreSQL is running and create the database:"
    echo "   createdb slidex"
fi

# Check Ollama models
echo "Checking Ollama models..."
if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "✓ nomic-embed-text model found"
else
    echo "⚠️  Missing: nomic-embed-text"
    echo "   Run: ollama pull nomic-embed-text"
fi

if ollama list 2>/dev/null | grep -q "granite4:tiny-h"; then
    echo "✓ granite4:tiny-h model found"
else
    echo "⚠️  Missing: granite4:tiny-h"
    echo "   Run: ollama pull granite4:tiny-h"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate environment: source .venv/bin/activate"
echo "  2. Pull Ollama models (if needed): just pull-models"
echo "  3. Start server: just run"
echo "  4. Or use CLI: slidex --help"
