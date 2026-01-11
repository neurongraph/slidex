#!/bin/bash
# Development setup script for Slidex

set -e  # Exit on error

echo "🚀 Setting up Slidex development environment..."

# Check Python version
echo "Checking Python version..."
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
    python_version=$(python3 --version 2>&1)
    echo "❌ Error: Python 3.9+ is required (found $python_version)"
    exit 1
fi
echo "✓ Python version OK: $(python3 --version)"

# Check if PostgreSQL is running
echo "Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "⚠️  Warning: psql not found. Make sure PostgreSQL is installed and running."
else
    echo "✓ PostgreSQL client found"
fi

# Check if Ollama is running
echo "Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "❌ Error: Ollama not found. Please install Ollama first."
    echo "   Visit: https://ollama.ai"
    exit 1
fi
echo "✓ Ollama found"

# Check if Ollama is serving
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Warning: Ollama doesn't seem to be running. Start it with: ollama serve"
else
    echo "✓ Ollama is running"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    pip install uv
    echo "✓ uv installed"
else
    echo "✓ uv found"
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -e .
echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cat > .env << 'EOF'
DATABASE_URL=postgresql://localhost:5432/slidex
OLLAMA_HOST=http://localhost
OLLAMA_PORT=11434
LOG_LEVEL=DEBUG
EOF
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
if python scripts/init_db.py; then
    echo "✓ Database initialized"
else
    echo "⚠️  Warning: Database initialization failed. You may need to create the database manually."
fi

# Check for required Ollama models
echo "Checking Ollama models..."
if ollama list | grep -q "nomic-embed-text"; then
    echo "✓ nomic-embed-text model found"
else
    echo "⚠️  Warning: nomic-embed-text model not found"
    echo "   Pull it with: ollama pull nomic-embed-text"
fi

if ollama list | grep -q "granite4:tiny-h"; then
    echo "✓ granite4:tiny-h model found"
else
    echo "⚠️  Warning: granite4:tiny-h model not found"
    echo "   Pull it with: ollama pull granite4:tiny-h"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source .venv/bin/activate"
echo "2. Make sure Ollama is running: ollama serve"
echo "3. Pull required models:"
echo "   - ollama pull nomic-embed-text"
echo "   - ollama pull granite4:tiny-h"
echo "4. Start the Flask server: just run"
echo "5. Or use the CLI: slidex --help"
