# Tool — Knowledge Graph over rev-eval (local dev tool)

> **Out-of-catalog.** This is a personal developer tool, not a W#-F# candidate
> feature. There is no `docs/features/` detail doc or `days_*_features.md` spec, and
> no `FEATURE_STATUS.md` row. **This plan is the source of truth / acceptance
> checklist.** Branch/commit workflow still follows the `/implement` conventions,
> adapted below.

## Context

Goal: a knowledge graph over the rev-eval **codebase and especially `docs/`** (plans,
feature specs, ADRs), for navigation / Q&A — "which ADR backs W4-F1?", "what code does
the scoring engine touch?", "what's blocked by W3-F2?".

Hard constraints (from the user):
- **Local-only, free.** No paid LLM/API/SaaS.
- **Containerized model**, switchable on/off, **near-zero idle RAM** when off.
- **Local dev tool only** — NOT a deployed service. Stays out of `docker-compose.yml`
  and the gateway `ROUTES`. Lives in its own `tools/knowledge-graph/` dir.

Why this fits: the repo has **zero existing AI/vector/graph infra** (confirmed — the
only "RAG" is exam *content* in `seed_rag_context_questions.py`), so it's a clean slate.
And `docs/` already encodes an explicit link graph: ADRs (`docs/adr/NNNN-*.md`), feature
specs (`docs/features/w#-f#-*.md`), plans (`docs/plans/w#-f#-*.md`), cross-referenced by
`W#-F#` IDs, relative `[..](adr/..)` links, and `file:line` code evidence. That
structural graph can be built **deterministically, no model required**.

## Tech selection (and why, vs. alternatives)

- **Framework: LightRAG** (`pip install lightrag-hku`). Lightweight, native Ollama
  support, tolerates small local models, file-based storage by default (no extra DB
  containers). Chosen over **Cognee** (benchmarks show heavy reliance on structured
  output → underperforms with small local models, the user's exact constraint),
  **MS GraphRAG** (one LLM call per chunk; too slow/expensive locally), **Graphiti**
  (built for temporal agent memory; overkill for static docs).
- **Graph + vector store: LightRAG defaults** — NetworkX graph (JSON on disk) +
  nano-vectordb. Zero extra containers. (Upgrade path: Neo4j/Kuzu for Cypher later.)
- **Model runtime: Ollama in a container**, profile-gated.
  - Extraction/query LLM: `qwen2.5:7b-instruct` (~5GB loaded; good small-model
    structured output).
  - Embeddings: `nomic-embed-text` (~275MB).
- **Toggle / memory control:**
  - Own compose file `tools/knowledge-graph/docker-compose.kg.yml`, Ollama on a **`kg`
    profile** → not started by the main stack; `up`/`down` = on/off.
  - `OLLAMA_KEEP_ALIVE=0` → model unloaded from RAM immediately after each request
    (cold-start next call, ~0 idle footprint). Idle container itself is tiny.
  - `docker compose -f ... down` frees everything.

## Two-layer graph design

**Layer 1 — deterministic structural graph (no model).** Parser walks `docs/`, builds
typed edges from known conventions:
- Nodes: `Feature(W#-F#)`, `ADR(NNNN)`, `Plan`, `CodeFile`.
- Edges: `feature -DOCUMENTED_BY-> plan`, `feature -DECIDED_BY-> adr`,
  `feature -EVIDENCED_BY-> codefile`, `adr -RELATES_TO-> adr`, `feature -BLOCKS-> feature`
  (from Deps/Unblocks lists), `doc -LINKS_TO-> doc` (relative md links).
- Extraction = regex over `W#-F#`, ADR link paths, `file/path.py(:line)?` strings.
  Runs in seconds; **always available even with the model off**. Exported to
  JSON + Mermaid/Graphviz.

**Layer 2 — semantic graph + RAG (Ollama-backed, toggleable).** LightRAG ingests the
**prose** of `docs/` (and optionally selected source) for entity/relation extraction +
embeddings → NL queries. Requires `kg` profile up. Layer 1 edges seeded into LightRAG so
structural + semantic share one graph.

Ingestion scope (cost control): **all of `docs/` (~50 files) always**; **source files
referenced as evidence** by default; full source (~16k files) behind explicit
`--include-source` flag. Log what's skipped; no silent caps.

## Deliverables (all under `tools/knowledge-graph/`)

```
tools/knowledge-graph/
  README.md                  # on/off, run, memory notes
  docker-compose.kg.yml      # Ollama service, profile: kg, KEEP_ALIVE=0, model volume
  requirements.txt           # lightrag-hku, networkx, etc.
  kg.py                      # CLI entrypoint
  src/
    structural.py            # Layer 1: deterministic doc-graph parser
    ingest.py                # Layer 2: LightRAG ingest (docs + optional source)
    query.py                 # NL query against LightRAG
    export.py                # graph -> JSON / Mermaid / Graphviz
  .gitignore                 # exclude ./storage (graph + vectors), model cache
```

CLI: `kg.py up|down`, `ingest [--include-source]`, `query "..."`,
`structure "W4-F1"` (Layer-1, works model-off), `export --format mermaid`.

## Git branching & workflow

### Step 0 — Branch & commit workflow (do first)
- Branch off the latest `richardh` tip.
- Create feature branch **`richardh-feat-kg-tool`** before any code change.
  *(Deviation from `richardh-feat-W#F#`: out-of-catalog tool, no feature number.)*
- **First commit on the branch = this plan file** at `docs/plans/tool-knowledge-graph.md`.
- One commit per milestone, Conventional Commits, matching repo history.

### Milestones (ordered; each ends in a commit)
1. **`docs(tool-kg): implementation plan`** — save this plan to
   `docs/plans/tool-knowledge-graph.md`. *(first commit)*
2. **`feat(tool-kg): scaffold + Ollama compose profile`** — `tools/knowledge-graph/`
   dir, `requirements.txt`, `docker-compose.kg.yml` (Ollama, `kg` profile,
   `OLLAMA_KEEP_ALIVE=0`, model volume), `.gitignore`, `kg.py up/down`. Touches:
   new files only.
3. **`feat(tool-kg): deterministic structural doc-graph (Layer 1)`** — `src/structural.py`
   + `kg.py structure`. Parses `docs/`, emits nodes/edges. Works model-off.
4. **`feat(tool-kg): graph export (JSON / Mermaid)`** — `src/export.py` + `kg.py export`.
5. **`feat(tool-kg): LightRAG semantic ingest + query (Layer 2)`** — `src/ingest.py`,
   `src/query.py`, `kg.py ingest|query`; seed Layer 1 edges into LightRAG.
6. **`docs(tool-kg): README + usage/memory notes`** — `README.md`.
7. **Requirements review** (below) — commit any doc/checklist updates.

## Testing & validation

No catalog spec; validate against this plan's acceptance. Pass bar = all of:
1. **Layer 1 model-off:** `python kg.py structure "W4-F1"` with Ollama **down** returns
   ADR 0001 + plan + evidence files. Proves Layer 1 needs no model.
2. **Toggle + memory:** `python kg.py up` → `docker ps` shows Ollama; `docker stats`
   ~0 model RAM idle. First `query` loads model; after response `docker stats` shows RAM
   drop (KEEP_ALIVE=0 confirmed). `python kg.py down` → `docker ps` empty, host RAM
   back to baseline.
3. **Semantic query:** after `ingest`, `query "Why was Jaccard chosen for multi-select
   scoring?"` returns an answer grounded in ADR 0002.
4. **Export:** `export --format mermaid` renders the feature/ADR/plan graph.
5. **Lint:** `python -m py_compile` / `ruff` clean on `tools/knowledge-graph/`.
6. **No deployed-stack impact:** `docker compose config` (root) unchanged; gateway
   `ROUTES` untouched; `git diff` touches only `tools/` + `docs/plans/`.

## Requirements review (final milestone)
Re-read this plan's Deliverables + Testing sections; confirm each against the actual
diff, citing evidence (file:line, commit). Confirm the out-of-catalog scope held (no
`services/`, `docker-compose.yml`, or `ROUTES` changes). No `FEATURE_STATUS.md` row
(not a catalog feature).

## Push gate
Push `richardh-feat-kg-tool` to origin **only if** all Testing checks pass **and** the
requirements review confirms every deliverable is met. Otherwise stop, leave the branch
local, report what's outstanding.

## Open upgrade paths (not in v1)
- Swap NetworkX → Neo4j/Kuzu for Cypher querying.
- Ingest `FDE_PEP_Content/` curriculum for a concept map.
- Tiny local web UI for graph browsing.
