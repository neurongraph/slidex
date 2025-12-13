# Just Commands Reference

Slidex uses [Just](https://github.com/casey/just) as a command runner for common development tasks. This provides a simpler and more consistent interface than remembering various shell commands.

## Quick Start

```bash
# Show all available commands
just

# Complete setup from scratch
just setup
```

## Setup & Installation

### `just setup`
Complete development environment setup. This command:
- Checks Python 3.13+ is installed
- Verifies PostgreSQL and Ollama are available
- Creates `.venv` virtual environment
- Installs uv package manager
- Installs all dependencies
- Creates `.env` configuration file
- Initializes storage directories
- Runs database migrations
- Checks for required Ollama models

**Usage:**
```bash
just setup
```

**After running:**
- Activate environment: `source .venv/bin/activate`
- Pull models: `just pull-models`
- Start server: `just run`

### `just install`
Install Python dependencies using uv. Use this after pulling new code or when dependencies change.

```bash
just install
```

### `just pull-models`
Download required Ollama models (nomic-embed-text and granite4:tiny-h).

```bash
just pull-models
```

## Running the Application

### `just run`
Start the Flask development server on http://localhost:5000

```bash
just run
```

### `just stop`
Stop any running Flask instances (if backgrounded).

```bash
just stop
```

## Database

### `just init-db`
Initialize or reset the PostgreSQL database schema. Runs migration scripts from `migrations/`.

```bash
just init-db
```

### `just db-stats`
Show database statistics (number of decks, slides, etc.).

```bash
just db-stats
```

## Testing

### `just test`
Run all tests with pytest.

```bash
just test
```

### `just test-coverage`
Run tests with coverage report (HTML and terminal output).

```bash
just test-coverage
```

## Monitoring & Debugging

### `just check`
Check system requirements and environment status:
- Python version
- PostgreSQL availability
- Ollama availability and running status
- Virtual environment existence

```bash
just check
```

### `just logs`
Tail application logs in real-time.

```bash
just logs
```

### `just audit-logs`
View recent LLM audit logs (last 20 interactions).

```bash
just audit-logs
```

### `just index-stats`
Show FAISS vector index statistics.

```bash
just index-stats
```

## Maintenance

### `just clean`
Clean generated files:
- Storage thumbnails and exports
- Python cache files (`__pycache__`)
- Pytest cache
- Egg-info directories

```bash
just clean
```

### `just clean-all`
Deep clean - removes everything including:
- Virtual environment (`.venv`)
- All storage files
- `.env` configuration

⚠️ **Warning:** This requires running `just setup` again.

```bash
just clean-all
```

## Code Quality

### `just format`
Format code using Black.

```bash
just format
```

### `just lint`
Lint code using Ruff.

```bash
just lint
```

## Common Workflows

### First-Time Setup
```bash
# 1. Clone and setup
git clone <repo-url>
cd slidex
just setup

# 2. Activate environment
source .venv/bin/activate

# 3. Pull Ollama models
just pull-models

# 4. Start developing
just run
```

### Daily Development
```bash
# Start your day
source .venv/bin/activate
just run

# In another terminal, tail logs
just logs

# Run tests before committing
just test
```

### Troubleshooting
```bash
# Check system status
just check

# View recent errors in logs
just logs

# Check database
just db-stats

# Rebuild from scratch if needed
just clean-all
just setup
```

### Testing Changes
```bash
# Format your code
just format

# Check for issues
just lint

# Run tests
just test

# Check test coverage
just test-coverage
```

## Environment Variables

The `just setup` command creates a `.env` file with defaults:

```env
DATABASE_URL=postgresql://localhost:5432/slidex
OLLAMA_HOST=http://localhost
OLLAMA_PORT=11434
LOG_LEVEL=DEBUG
```

You can manually edit `.env` to customize these settings.

## Tips

1. **List all commands**: Just run `just` with no arguments
2. **Command help**: Most commands are self-explanatory from their names
3. **Chaining commands**: Use shell operators like `just clean && just test`
4. **Background jobs**: Use `just run &` to run Flask in background
5. **Virtual environment**: Most commands expect you're in `.venv`, but `just setup` doesn't

## Comparison to Other Tools

| Task | Just Command | Alternative |
|------|-------------|-------------|
| Setup | `just setup` | `bash scripts/setup_dev.sh` |
| Install | `just install` | `uv pip install -e .` |
| Run server | `just run` | `FLASK_APP=slidex.api.app:app flask run` |
| Tests | `just test` | `pytest tests/ -v` |
| Init DB | `just init-db` | `python scripts/init_db.py` |
| Clean | `just clean` | `rm -rf storage/... __pycache__...` |

Just provides shorter, memorable commands and consistent behavior.
