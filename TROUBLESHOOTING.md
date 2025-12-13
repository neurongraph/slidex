# Troubleshooting Guide

Common issues and solutions for Slidex.

## Command Not Found: slidex

**Problem:**
```bash
$ slidex ingest file presentation.pptx
zsh: command not found: slidex
```

**Solution:**
The `slidex` CLI command is only available inside the virtual environment. You have two options:

### Option 1: Use just commands (Recommended - No activation needed)
```bash
# Ingest a file
just ingest-file /path/to/presentation.pptx

# Ingest a folder
just ingest-folder /path/to/folder

# Search
# (requires activation - see Option 2 for search)
```

### Option 2: Activate the virtual environment
```bash
# Activate venv
source .venv/bin/activate

# Now slidex commands work
slidex ingest file /path/to/presentation.pptx
slidex search "your query"
slidex assemble --slide-ids "id1,id2" --output result.pptx

# Deactivate when done
deactivate
```

## Virtual Environment Not Found

**Problem:**
```bash
$ just ingest-file test.pptx
python: command not found
```

**Solution:**
Run setup first:
```bash
just setup
```

## PostgreSQL Connection Error

**Problem:**
```
Error: could not connect to server: Connection refused
```

**Solution:**
```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Start PostgreSQL
brew services start postgresql@16

# Create database if needed
createdb slidex

# Initialize schema
just init-db
```

## Ollama Connection Error

**Problem:**
```
Error: Failed to connect to Ollama at http://localhost:11434
```

**Solution:**
```bash
# Start Ollama
ollama serve

# Or start as a service
brew services start ollama

# Verify it's running
curl http://localhost:11434/api/tags
```

## Missing Ollama Models

**Problem:**
```
Error: model "nomic-embed-text" not found
```

**Solution:**
```bash
# Pull required models
just pull-models

# Or manually
ollama pull nomic-embed-text
ollama pull granite4:tiny-h
```

## Permission Denied Errors

**Problem:**
```bash
$ ./scripts/setup.sh
zsh: permission denied: ./scripts/setup.sh
```

**Solution:**
```bash
# Make script executable
chmod +x scripts/setup.sh

# Or use just
just setup
```

## Import Errors

**Problem:**
```
ModuleNotFoundError: No module named 'slidex'
```

**Solution:**
```bash
# Sync dependencies
just sync

# Or if that fails, clean and reinstall
just clean-all
just setup
```

## Database Already Exists Error

**Problem:**
```
ERROR: database "slidex" already exists
```

**Solution:**
This is usually fine - the database already exists. Just run:
```bash
just init-db
```

If you want to start fresh:
```bash
# Drop and recreate database
dropdb slidex
createdb slidex
just init-db
```

## Port Already in Use

**Problem:**
```
Error: Address already in use (port 5000)
```

**Solution:**
```bash
# Find and kill the process
lsof -ti:5000 | xargs kill -9

# Or use just stop
just stop

# Then start again
just run
```

## Python Version Mismatch

**Problem:**
```
Error: Python 3.12+ is required (found 3.9.6)
```

**Solution:**
```bash
# Install Python 3.12
brew install python@3.12

# Or use pyenv
pyenv install 3.12.9
pyenv local 3.12.9

# Verify
just check
```

## uv Not Found

**Problem:**
```
Error: uv: command not found
```

**Solution:**
```bash
# Install uv
pip install uv

# Or with pipx (recommended)
pipx install uv

# Verify
uv --version
```

## File Not Found During Ingestion

**Problem:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'presentation.pptx'
```

**Solution:**
Use absolute paths or verify the file exists:
```bash
# Use absolute path
just ingest-file /Users/yourname/Documents/presentation.pptx

# Or use pwd to get absolute path
just ingest-file $(pwd)/presentation.pptx

# Verify file exists
ls -la presentation.pptx
```

## Path Subpath Error During Ingestion

**Problem:**
```
Error: 'storage/thumbnails/...' is not in the subpath of '/Users/...'  
```

**Solution:**
This has been fixed in the latest version. If you still see this:
```bash
# Update your code
git pull  # or sync your changes

# Or reinstall
just sync
```

## Thumbnail Generation

### Basic Fallback (Always Works)
Thumbnails are generated automatically with text-based rendering. This always works but shows only text content.

### Improved Quality with LibreOffice
For high-quality visual thumbnails showing actual slide content, backgrounds, and formatting:

**Installation Options:**
```bash
# Option 1: Homebrew (automatic PATH setup)
brew install --cask libreoffice

# Option 2: Download from .dmg file
# Visit https://www.libreoffice.org/download/download/
# Install the .dmg file normally (drag to Applications)
```

Once installed:
- Slidex will automatically detect and use LibreOffice for thumbnail generation
- If LibreOffice is unavailable, enhanced Pillow rendering is used automatically
- No configuration needed - it's transparent
- Works with both Homebrew and .dmg installations

**Problem: LibreOffice not found despite being installed**

If you installed via .dmg and see debug logs about LibreOffice not being found:
```bash
# Verify LibreOffice is in Applications
ls -la /Applications/LibreOffice.app/Contents/MacOS/soffice

# If this returns "No such file", reinstall LibreOffice from:
# https://www.libreoffice.org/download/download/
```

The detection checks:
1. `libreoffice` in PATH (Homebrew installations)
2. `/Applications/LibreOffice.app/Contents/MacOS/soffice` (.dmg installations)
3. `soffice` in PATH (alternative name)

## Database Schema Out of Date

**Problem:**
```
ProgrammingError: column "new_column" does not exist
```

**Solution:**
```bash
# Reinitialize database schema
just init-db

# Or drop and recreate
dropdb slidex
createdb slidex
just init-db
```

## Permission Denied for Database Tables (DBeaver/External Tools)

**Problem:**
```
ERROR: permission denied for table slides
SQL Error [42501]
```

**Solution:**
The tables were created by your application user but your DBeaver connection uses a different user. Grant permissions:
```bash
# Grant permissions to all users
just grant-permissions

# Or manually run the script
python scripts/grant_permissions.py
```

After running this, refresh your connection in DBeaver and try again.

## Can't Find Ingested Files

**Problem:**
Ingested files but search returns no results.

**Solution:**
Check the FAISS index and database:
```bash
# Check index stats
just index-stats

# Check database stats
just db-stats

# View logs for errors
just logs
```

## Getting Help

If you're still stuck:

1. **Check the logs:**
   ```bash
   just logs
   ```

2. **Check system requirements:**
   ```bash
   just check
   ```

3. **View audit logs:**
   ```bash
   just audit-logs
   ```

4. **Start fresh:**
   ```bash
   just clean-all
   just setup
   just pull-models
   just run
   ```

## Quick Reference

| Problem | Command |
|---------|---------|
| Setup from scratch | `just setup` |
| Check requirements | `just check` |
| Start server | `just run` |
| View logs | `just logs` |
| Ingest file | `just ingest-file /path/to/file.pptx` |
| Pull models | `just pull-models` |
| Clean everything | `just clean-all` |
| Reinit database | `just init-db` |
