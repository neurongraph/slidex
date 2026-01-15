# vLLM Reranker Setup Guide

This document explains how to set up a vLLM service for reranking with the `bge-reranker-v2-m3` model.

## Prerequisites

- Python 3.11+
- pip
- Docker (optional, for containerized deployment)

## Installation

### Option 1: Install vLLM directly

```bash
pip install vllm
```

### Option 2: Use Docker

```bash
docker pull vllm/vllm-openai:latest
```

## Running the vLLM Reranker Service

### Using vLLM directly

To run the vLLM service with the `bge-reranker-v2-m3` model:

```bash
python -m vllm.entrypoints.api_server \
    --host 0.0.0.0 \
    --port 8182 \
    --model BAAI/bge-reranker-v2-m3 \
    --tensor-parallel-size 1 \
    --disable-log-requests
```

### Using Docker

```bash
docker run -d \
    --name vllm-reranker \
    --gpus all \
    -p 8182:8182 \
    vllm/vllm-openai:latest \
    --host 0.0.0.0 \
    --port 8182 \
    --model BAAI/bge-reranker-v2-m3 \
    --tensor-parallel-size 1 \
    --disable-log-requests
```

## Model Information

The `bge-reranker-v2-m3` model is a reranker model from BAAI (Beijing Academy of Artificial Intelligence) that is optimized for reranking tasks. It's designed to provide better relevance scores for search results.

## Configuration in Slidex

Once the vLLM service is running, enable it in Slidex by setting:

```
VLLM_RERANKER_ENABLED=true
VLLM_RERANKER_URL=http://localhost:8182
VLLM_RERANKER_MODEL=bge-reranker-v2-m3
```

## Testing the Service

You can test if the service is running correctly by sending a request:

```bash
curl http://localhost:8182/v1/models
```

Or test the reranking endpoint:

```bash
curl -X POST http://localhost:8182/v1/rerank \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the capital of France?",
    "documents": ["Paris is the capital of France.", "Berlin is the capital of Germany."],
    "top_n": 2
  }'
```