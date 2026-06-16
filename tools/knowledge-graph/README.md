# Knowledge Graph (local dev tool)

A local, free knowledge graph over the rev-eval **codebase + `docs/`** (plans,
feature specs, ADRs) for navigation and Q&A. **Not part of the deployed stack** —
it lives here, stays out of the root `docker-compose.yml` and the gateway `ROUTES`,
and reads the repo read-only.

Full design + rationale: [`docs/plans/tool-knowledge-graph.md`](../../docs/plans/tool-knowledge-graph.md).

## Two layers

| Layer | What | Needs a model? |
|---|---|---|
| **1 — structural** | Deterministic graph from doc conventions (feature ↔ ADR ↔ plan ↔ code edges). `structure`, `export`. | **No.** Pure stdlib, works offline. |
| **2 — semantic** | LightRAG entity/relation extraction + embeddings over prose → natural-language Q&A. `ingest`, `query`. | Yes — containerized Ollama. |

## Quick start

```bash
cd tools/knowledge-graph

# Layer 1 — no install, no model needed:
python kg.py structure W4-F1            # show a node's edges
python kg.py structure ADR-0001
python kg.py export --format mermaid --out graph.mmd
python kg.py export --format json --out graph.json

# Layer 2 — semantic Q&A:
pip install -r requirements.txt
python kg.py up                          # start Ollama + pull models (first run ~5GB)
python kg.py ingest                      # index docs/ (+ evidence source files)
python kg.py query "Why was Jaccard chosen for multi-select scoring?"
python kg.py down                        # stop Ollama, free all model RAM
```

## Commands

- `up` / `down` — start / stop the containerized Ollama (the `kg` compose profile).
- `structure <node>` — Layer 1 lookup. Accepts `W4-F1`, `ADR-0001`, `0001`, a
  doc/code path, or a label substring. Works with the model **down**.
- `export --format {mermaid,json,dot} [--out FILE] [--include-code]` — dump the
  structural graph. Diagrams drop the ~190 code-evidence nodes for readability
  unless `--include-code`; JSON always includes them.
- `ingest [--include-source]` — build the LightRAG index. Always indexes all of
  `docs/` plus source files cited as evidence; `--include-source` adds **all** tracked
  source (~16k files — slow). Re-seeds the Layer 1 edges each run.
- `query "<question>" [--mode {naive,local,global,hybrid,mix}]` — natural-language
  query (default `hybrid`). Needs `up` + a prior `ingest`.

## Memory & toggling (the "turn it off" requirement)

- Ollama runs as **one container** behind the `kg` Docker Compose profile, so the
  root `docker compose up` never starts it. `python kg.py up`/`down` is the switch.
- `OLLAMA_KEEP_ALIVE=0` (set in `docker-compose.kg.yml`) unloads the model from RAM
  **immediately after each request** → ~zero idle footprint while the container
  idles. Trade-off: a cold-start reload (a few seconds) on the next call.
- `python kg.py down` removes the container entirely — host RAM back to baseline.
  Pulled models persist in the `ollama-models` volume, so re-`up` is fast.

## Config (env overrides)

| Var | Default | Meaning |
|---|---|---|
| `KG_OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `KG_LLM_MODEL` | `qwen2.5:7b-instruct` | extraction / answer model |
| `KG_EMBED_MODEL` | `nomic-embed-text` | embedding model |
| `KG_EMBED_DIM` | `768` | embedding dim (must match the embed model) |

## Layout

```
kg.py                     CLI entrypoint (argparse dispatch)
docker-compose.kg.yml     Ollama service, kg profile, KEEP_ALIVE=0
requirements.txt          Layer 2 deps (Layer 1 needs none)
src/config.py             paths + model config
src/structural.py         Layer 1 parser + `structure`
src/export.py             JSON / Mermaid / DOT export
src/_lightrag.py          LightRAG + Ollama wiring, Layer 1 → custom-KG
src/ingest.py             Layer 2 ingest
src/query.py              Layer 2 query
storage/                  LightRAG graph + vectors (gitignored)
```

## Notes & limits

- Code-evidence paths in docs are cited relative to a service dir; they resolve via
  **unique-suffix match** over `git ls-files`. Ambiguous names (bare `main.py`,
  `src/db/session.py` present in several services) stay unresolved and are shown
  `(MISSING)` rather than guessed.
- Cognee was evaluated and rejected: it leans on structured output and underperforms
  with small local models. LightRAG tolerates them. See the plan for the comparison.
- Upgrade paths (not built): swap NetworkX → Neo4j/Kuzu for Cypher; ingest
  `FDE_PEP_Content/`; a small graph-browsing web UI.
