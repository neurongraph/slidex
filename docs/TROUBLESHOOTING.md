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
Run `just setup` to create the virtual environment.

## PDF Conversion Issues

**Problem:**
PDF conversion is failing or disabled.

**Solution:**
1. Check if LibreOffice is installed:
```bash
brew install libreoffice
```

2. Verify LibreOffice is in PATH:
```bash
which soffice
```

3. Enable PDF processing:
```bash
just enable-pdf
```

4. Restart the application to apply changes.

## Missing PDF Processing Features

**Problem:**
PDF processing features are not available even though LibreOffice is installed.

**Solution:**
1. Check if PDF processing is enabled in settings:
```bash
just check-pdf
```

2. If disabled, enable it:
```bash
just enable-pdf
```

3. Restart the application.
