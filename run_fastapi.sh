#!/bin/bash
# Run Slidex with FastAPI and Uvicorn

echo "Starting Slidex with FastAPI..."
echo "API will be available at http://localhost:5001"
echo "Docs available at http://localhost:5001/docs"
echo ""

cd "$(dirname "$0")"
uv run uvicorn slidex.api.app:app --host 0.0.0.0 --port 5001 --reload
