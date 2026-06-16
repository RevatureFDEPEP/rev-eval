"""Shared LightRAG + Ollama wiring for Layer 2 (semantic ingest + query).

Isolated here so `ingest` and `query` agree on the model config, and so the
heavy `lightrag` import + the Ollama connectivity check live in one place.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request

from src import config, structural


def check_ollama() -> None:
    """Fail fast with a friendly message if the model runtime isn't up."""
    try:
        urllib.request.urlopen(config.OLLAMA_HOST + "/api/tags", timeout=3)
    except (urllib.error.URLError, OSError):
        sys.exit(
            f"Ollama not reachable at {config.OLLAMA_HOST}.\n"
            "Start the model runtime first:  python kg.py up"
        )


def make_rag():
    """Construct a LightRAG instance pointed at the containerized Ollama."""
    try:
        from lightrag import LightRAG
        from lightrag.llm.ollama import ollama_embed, ollama_model_complete
        from lightrag.utils import EmbeddingFunc
    except ImportError:
        sys.exit(
            "lightrag not installed. From tools/knowledge-graph/:\n"
            "  pip install -r requirements.txt"
        )

    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return LightRAG(
        working_dir=str(config.STORAGE_DIR),
        llm_model_func=ollama_model_complete,
        llm_model_name=config.LLM_MODEL,
        llm_model_kwargs={"host": config.OLLAMA_HOST, "options": {"num_ctx": 8192}},
        embedding_func=EmbeddingFunc(
            embedding_dim=config.EMBED_DIM,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts, embed_model=config.EMBED_MODEL, host=config.OLLAMA_HOST
            ),
        ),
    )


async def init_rag(rag) -> None:
    """Required post-construction async init in modern LightRAG."""
    from lightrag.kg.shared_storage import initialize_pipeline_status

    await rag.initialize_storages()
    await initialize_pipeline_status()


def graph_as_custom_kg(g: structural.Graph) -> dict:
    """Convert the Layer 1 structural graph into LightRAG's custom-KG schema,
    so deterministic structure and LLM-extracted semantics share one graph."""
    entities = [
        {
            "entity_name": n.id,
            "entity_type": n.type,
            "description": n.label or n.id,
            "source_id": "layer1-structural",
        }
        for n in g.nodes.values()
    ]
    relationships = [
        {
            "src_id": e.src,
            "tgt_id": e.dst,
            "description": e.rel,
            "keywords": e.rel,
            "weight": 1.0,
            "source_id": "layer1-structural",
        }
        for e in g.edges
    ]
    return {"entities": entities, "relationships": relationships, "chunks": []}
