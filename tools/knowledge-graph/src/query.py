"""Layer 2 query — natural-language question against the LightRAG index.

Needs the model runtime up (`python kg.py up`) and a prior `kg.py ingest`.
"""
from __future__ import annotations

import asyncio

from src import _lightrag, config


async def _query_async(text: str, mode: str) -> int:
    _lightrag.check_ollama()
    if not (config.STORAGE_DIR / "graph_chunk_entity_relation.graphml").exists() \
            and not any(config.STORAGE_DIR.glob("*.json")):
        print("no index found — run `python kg.py ingest` first.")
        return 1

    from lightrag import QueryParam

    rag = _lightrag.make_rag()
    await _lightrag.init_rag(rag)
    answer = await rag.aquery(text, param=QueryParam(mode=mode))
    await rag.finalize_storages()
    print(answer)
    return 0


def run_query(text: str, mode: str = "hybrid") -> int:
    return asyncio.run(_query_async(text, mode))
