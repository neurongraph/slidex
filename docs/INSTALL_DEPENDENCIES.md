# Installing Dependencies for Slidex

This guide helps you install the required dependencies for Slidex on macOS.

## Check Current Status

First, check what you need to install:

```bash
just check
```

## Install Python 3.12

Slidex requires Python 3.12 or higher. Install using Homebrew:

```bash
# Install Python 3.12
brew install python@3.12

# Verify installation
python3.13 --version
```

**Expected output:** `Python 3.12.x`

### Alternative: Using pyenv

If you prefer managing Python versions with pyenv:

```bash
# Install pyenv if not already installed
brew install pyenv

# Install Python 3.12
pyenv install 3.13.1

# Set it as global or local version
pyenv global 3.13.1
# or for this directory only
pyenv local 3.13.1
```

## Install PostgreSQL

Slidex uses PostgreSQL for metadata storage.

### Option 1: Homebrew (Recommended)

```bash
# Install PostgreSQL
brew install postgresql@16

# Start PostgreSQL service
brew services start postgresql@16

# Verify it's running
psql --version
```

### Option 2: Postgres.app

Download and install from: https://postgresapp.com/

This provides a GUI and includes command-line tools.

### Create Database

After PostgreSQL is installed:

```bash
# Create the slidex database
createdb slidex

# Or if that doesn't work:
psql postgres -c "CREATE DATABASE slidex;"
```

## Install Ollama

Ollama is required for local LLM operations.

```bash
# Install Ollama
brew install ollama

# Start Ollama service
brew services start ollama
```

## Install LibreOffice (Optional but Recommended)

For full PDF processing capabilities, install LibreOffice:

```bash
brew install libreoffice
```

Once Ollama is running:

```bash
# Pull embedding model (required)
ollama pull nomic-embed-text

# Pull LLM model for summaries (required)
ollama pull granite4:tiny-h
```

Or use the just command:

```bash
just pull-models
```

## Verify Everything

After installing all dependencies:

```bash
just check
```

You should see all checkmarks (✓):

```
Checking system requirements...
✓ Python 3.12 found: Python 3.12.x
✓ PostgreSQL found
✓ Ollama found
✓ Ollama running
⚠️  Virtual environment not found (this is OK before setup)
```

## Run Setup

Once all dependencies are installed:

```bash
just setup
```

This will:
- Create virtual environment
- Install Python packages
- Initialize database schema
- Create storage directories

## Activate Environment

After setup:

```bash
source .venv/bin/activate
```

## Start Slidex

```bash
just run
```

Visit http://localhost:5000

## Troubleshooting

### "command not found: just"

Install Just command runner:

```bash
brew install just
```

### "command not found: brew"

Install Homebrew first:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Python 3.12 installed but still shows 3.9

Make sure Python 3.12 is in your PATH. Add to your `~/.zshrc`:

```bash
# Add Homebrew Python to PATH
export PATH="/opt/homebrew/opt/python@3.12/bin:$PATH"
```

Then reload:

```bash
source ~/.zshrc
```

### PostgreSQL connection errors

Check if PostgreSQL is running:

```bash
brew services list | grep postgresql
```

If not running:

```bash
brew services start postgresql@16
```

### Ollama not responding

Restart Ollama:

```bash
# If running in terminal, Ctrl+C to stop, then:
ollama serve

# If running as service:
brew services restart ollama
```

## Summary of Commands

```bash
# 1. Install dependencies
brew install python@3.12 postgresql@16 ollama just

# 2. Start services
brew services start postgresql@16
brew services start ollama

# 3. Create database
createdb slidex

# 4. Pull Ollama models
ollama pull nomic-embed-text
ollama pull granite4:tiny-h

# 5. Setup Slidex
just setup

# 6. Activate environment
source .venv/bin/activate

# 7. Run Slidex
just run
```
