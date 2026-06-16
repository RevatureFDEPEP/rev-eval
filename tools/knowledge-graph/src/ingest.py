"""Layer 2 ingest — seed the structural graph, then LightRAG-index doc prose.

Scope (cost control, see plan):
  - ALL of docs/ (~50 files)            : always.
  - source files referenced as evidence : always (small, high-signal set).
  - ALL source (~16k files)             : only with --include-source.
Dropped scope is logged — no silent caps.
"""
from __future__ import annotations

import asyncio

from src import _lightrag, config, structural


def _docs() -> list[tuple[str, str]]:
    out = []
    for f in sorted(config.DOCS_DIR.rglob("*.md")):
        out.append((str(f.relative_to(config.REPO_ROOT)),
                    f.read_text(encoding="utf-8", errors="replace")))
    return out


def _evidence_sources(g: structural.Graph) -> list[str]:
    return sorted({n.path for n in g.nodes.values()
                   if n.type == "code" and n.exists and n.path})


def _all_sources() -> list[str]:
    exts = (".py", ".ts", ".tsx", ".js", ".jsx", ".sql")
    return sorted(f for f in structural._tracked_files() if f.endswith(exts))


def _read(relpath: str) -> str | None:
    p = config.REPO_ROOT / relpath
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


async def _ingest_async(include_source: bool) -> int:
    _lightrag.check_ollama()
    g = structural.build_graph()

    rag = _lightrag.make_rag()
    await _lightrag.init_rag(rag)

    # 1. Seed deterministic Layer 1 edges into the shared graph.
    print(f"seeding structural graph: {len(g.nodes)} nodes, {len(g.edges)} edges")
    await rag.ainsert_custom_kg(_lightrag.graph_as_custom_kg(g))

    # 2. Collect prose to index.
    texts, ids = [], []
    for relpath, body in _docs():
        texts.append(f"# FILE: {relpath}\n\n{body}")
        ids.append(relpath)

    src = _evidence_sources(g)
    if include_source:
        allsrc = _all_sources()
        print(f"--include-source: indexing all {len(allsrc)} tracked source files "
              f"(was {len(src)} evidence files)")
        src = allsrc
    else:
        print(f"indexing {len(src)} evidence-referenced source files "
              f"(use --include-source for all ~{len(_all_sources())})")

    for relpath in src:
        body = _read(relpath)
        if body is not None:
            texts.append(f"# FILE: {relpath}\n\n{body}")
            ids.append(relpath)

    # 3. Index. LightRAG runs LLM entity extraction per chunk (the slow part).
    print(f"indexing {len(texts)} documents via {config.LLM_MODEL} "
          f"(LLM extraction — this is the slow step)…")
    await rag.ainsert(texts, ids=ids)
    await rag.finalize_storages()
    print(f"done. graph + vectors in {config.STORAGE_DIR}")
    return 0


def run_ingest(include_source: bool = False) -> int:
    return asyncio.run(_ingest_async(include_source))
