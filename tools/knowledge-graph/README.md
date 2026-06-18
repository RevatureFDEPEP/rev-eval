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

# Layer 2 — semantic Q&A (use a venv; required on PEP-668 / Arch systems):
python -m venv .venv && source .venv/bin/activate
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
- **`python kg.py down` is the hard "free all RAM now" switch** — it removes the
  container, so the model and its memory go with it. Pulled models persist in the
  `ollama-models` volume, so re-`up` is fast (no re-download).
- While the container is *up*, `OLLAMA_KEEP_ALIVE` (default `5m`, set in
  `docker-compose.kg.yml`) keeps the model warm during active use and **auto-unloads
  it after 5 min idle** → RAM frees itself when you stop querying. The idle container
  with no model loaded is tiny.
- Why not unload after *every* request (`KG_KEEP_ALIVE=0`)? A single `ingest` makes
  hundreds of embed/LLM calls; reloading the model each time is cripplingly slow and
  causes reload-contention errors. `0` is available via `KG_KEEP_ALIVE=0` for a
  pure-idle/zero-RAM stance, but don't use it while ingesting.

## GPU (optional, much faster ingest)

CPU-only by default so `up` works anywhere. CPU ingest of all of `docs/` with a 7B
model is very slow (hours → ~10h). On an NVIDIA GPU the same ingest runs in ~1.5h.

1. Install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
   on the host and wire it into Docker:
   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
   docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi -L   # verify
   ```
2. Run with `KG_GPU=1`, which layers `docker-compose.kg.gpu.yml` onto the base
   compose (the base stays CPU-only):
   ```bash
   KG_GPU=1 python kg.py up
   python kg.py ingest          # talks to the same Ollama; no flag needed
   KG_GPU=1 python kg.py down
   ```

By default the whole model packs onto the **single GPU with the most free VRAM**
(no cross-GPU layer split — best for one fast card, or mixed-speed multi-GPU
where splitting would let the slowest card bottleneck every token). GPU-mode env
knobs: `KG_NUM_PARALLEL` (concurrent slots, default 4), `KG_SCHED_SPREAD`
(`true` splits one model across all GPUs — only for matched cards),
`KG_GPU_COUNT` (`all` or an integer). A smaller `KG_LLM_MODEL` also cuts time.

> **Known issue — `query` synthesis with LightRAG 1.5.3.** `ingest` and
> retrieval work, but the final natural-language answer from `kg.py query` can
> come back as a single token. Verified it is *not* the model (direct Ollama
> generation is fine), nor cache, nor `num_ctx` (tunable via `KG_NUM_CTX`,
> default 16384) — it is LightRAG's query-synthesis path. Structural Layer 1
> (`structure`/`export`) and Layer 2 retrieval are unaffected; pin/patch
> LightRAG to restore synthesis.

## Config (env overrides)

| Var | Default | Meaning |
|---|---|---|
| `KG_OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `KG_LLM_MODEL` | `qwen2.5:7b-instruct` | extraction / answer model |
| `KG_EMBED_MODEL` | `nomic-embed-text` | embedding model |
| `KG_EMBED_DIM` | `768` | embedding dim (must match the embed model) |
| `KG_KEEP_ALIVE` | `5m` | model idle-unload window; `0` = unload every request (slow) |
| `KG_NUM_CTX` | `16384` | LLM context window (must hold the query-synthesis context) |
| `KG_GPU` | _(unset)_ | set to any value to layer the GPU override onto `up`/`down` |
| `KG_NUM_PARALLEL` | `4` | (GPU) concurrent Ollama slots |
| `KG_SCHED_SPREAD` | `false` | (GPU) `true` splits one model across all GPUs |
| `KG_GPU_COUNT` | `all` | (GPU) number of GPUs to expose (`all` or an int) |

## Layout

```
kg.py                     CLI entrypoint (argparse dispatch)
docker-compose.kg.yml     Ollama service, kg profile, idle-unload keep-alive
docker-compose.kg.gpu.yml GPU override (layered on when KG_GPU is set)
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
