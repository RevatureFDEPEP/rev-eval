"""Shared configuration for the knowledge-graph dev tool.

Single source of truth for paths and model names so every subcommand
(structural, export, ingest, query) agrees on where things live.
"""
from __future__ import annotations

import os
from pathlib import Path

# tools/knowledge-graph/src/config.py -> parents[2] == repo root (holds docs/, services/).
TOOL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = REPO_ROOT / "docs"

# LightRAG working dir (graph json, vectors, kv, cache). Gitignored.
STORAGE_DIR = TOOL_DIR / "storage"

# Containerized Ollama (see docker-compose.kg.yml). Override host via env for non-local.
OLLAMA_HOST = os.environ.get("KG_OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.environ.get("KG_LLM_MODEL", "qwen2.5:7b-instruct")
EMBED_MODEL = os.environ.get("KG_EMBED_MODEL", "nomic-embed-text")
EMBED_DIM = int(os.environ.get("KG_EMBED_DIM", "768"))  # nomic-embed-text = 768

# Models pulled on first `kg.py up`.
PULL_MODELS = (LLM_MODEL, EMBED_MODEL)
