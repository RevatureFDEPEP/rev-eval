---
name: implement
description: >-
  Plan and implement a new feature for the rev-eval platform end to end. Use when
  the user wants to build, implement, or work on a numbered feature (W#-F# / W#-M#)
  from the FDE PEP catalog. Reads the feature detail doc + FEATURE_STATUS.md, writes
  a milestone plan to docs/plans/, presents it for approval, then executes on a fresh
  feature branch (richardh-feat-W#F#) committing per milestone, runs tests + a
  requirements review, and pushes to origin only when both pass.
---

# Implement a Feature

Drive a rev-eval feature from spec to pushed branch. Two phases with a hard gate
between them: **plan (analysis → written plan → user approval)**, then
**execute (branch → milestones+commits → test → requirements review → push)**.

Work happens inside `rev-eval/` (the git repo). Resolve the repo root as the
directory containing `docker-compose.yml` and `docs/features/`; if the cwd isn't
it, `cd` there or ask.

## Phase 1 — Analyze & plan

### 1. Identify the target feature
- If the user named a feature (`W3-F1`, "quiz session backend", etc.), use it.
  Otherwise read `docs/FEATURE_STATUS.md` and propose the next sensible target
  from the "Suggested order of attack", then confirm before planning.
- Note the status. If it's already ✅ Completed, stop and confirm with the user
  before redoing it.

### 2. Read the inputs (these are the source of truth)
1. The feature detail doc `docs/features/w#-f#-<name>.md` — its **Steps**,
   **Depends on**, **Unblocks**, and **Notes**. This is the acceptance checklist.
2. `docs/FEATURE_STATUS.md` — the status row and dependency ordering.
3. The upstream spec the detail doc cites (the `days_*_features.md` section, one
   level above the repo root) — read its Implementation Details for anything the
   detail doc compresses.
4. Any **Depends on** features — confirm they're done, or surface the gap. Do not
   plan on top of an unmet prerequisite without flagging it.
5. An existing plan in `docs/plans/` for this feature, if present — extend it
   rather than starting over.
6. **Knowledge graph (Layer 1 — structural, no model needed).** From
   `tools/knowledge-graph/`, run `python kg.py structure W#-F#` for the target
   feature. This is fast, offline, and deterministic — no Ollama, no install.
   Use its edges to ground the plan:
   - `DEPENDS_ON` / `UNBLOCKS` — cross-check the detail doc's prerequisites and
     downstream impact; surface any dep the doc omits.
   - `DECIDED_BY` (ADR) / `SPECIFIED_BY` (spec) / `DOCUMENTED_BY` (plan) — pull
     the governing decisions and docs into the plan's Context.
   - `EVIDENCED_BY` (code paths) — the files prior docs cite for this area; use
     as a starting touchpoint list. Also run `python kg.py structure <file>` on
     any file you intend to change to see which other features/ADRs cite it
     (impact check) before planning the change.
   If the structural lookup contradicts the detail doc (extra/missing deps,
   stale code evidence), flag it in the plan rather than silently trusting one.

### 3. Write the plan
Save to `docs/plans/w#-f#-<name>.md`, matching the slug of the feature detail
doc. Match the structure of existing plans (see `w2-f7-alembic-category-domain.md`
as the reference shape). The plan **must** contain:

- **Header** — feature id + title, link to the detail doc and spec, `Depends on`
  / `Unblocks`, and any locked user decisions.
- **Context** — what exists now, what changes, key constraints/gotchas pulled
  from CLAUDE.md and the codebase.
- **Step 0 — Branch & commit workflow** (always first, verbatim intent):
  - `git fetch && git pull origin richardh` to update local `richardh`.
  - Create the feature branch **`richardh-feat-W#F#`** (e.g. `richardh-feat-W3F1`)
    **off `richardh`** before any code change.
  - **First commit on the branch = this plan file** (version-controlled plans).
  - One commit per milestone (Conventional Commits, matching repo history).
- **Milestones** — the implementation broken into ordered, logically-scoped
  chunks. Each milestone names the files it touches and **ends with a commit** to
  the local feature branch. Derive milestones from the detail doc's Steps; don't
  invent scope beyond the spec.
- **Testing & validation** — explicit: which tests run and how (per-service
  `pytest --cov` from `services/<svc>/`, `pnpm lint`/`build` for frontend,
  `docker compose up --build` + the relevant smoke check). State the pass bar.
- **Requirements review** — a final milestone that re-reads the feature detail
  doc Steps + spec acceptance criteria and confirms each is satisfied, citing
  evidence (file:line, commit). Also update the detail doc (check off steps, add
  evidence) and the `FEATURE_STATUS.md` row in the same branch.
- **Push gate** — push `richardh-feat-W#F#` to origin **only if** all tests pass
  **and** the requirements review confirms every Step is met. Otherwise stop and
  report what's outstanding.

### 4. Present for approval (hard gate)
Present the plan for review and **wait for explicit approval before executing**.
Use EnterPlanMode/ExitPlanMode for the approval handshake. Do not create the
branch or write code until approved. Apply any edits the user requests to the
plan file first.

## Phase 2 — Execute (only after approval)

Follow the plan in order. Specifically:

1. **Branch.** `git fetch`, `git pull origin richardh`, then create
   `richardh-feat-W#F#` off `richardh`. Confirm you're on it (`git branch
   --show-current`) before editing.
2. **Commit the plan first**, then implement milestone by milestone, committing
   after each per the plan. Keep commits scoped and conventional.
3. **Test & validate** per the plan's testing section. Run the tests; capture
   real output. If something fails, fix it (or surface it) — never report a green
   bar you didn't see.
4. **Requirements review.** Re-read the feature detail doc Steps + spec; verify
   each against the actual diff. Update the detail doc (✅ steps + evidence) and
   the `FEATURE_STATUS.md` status row; commit those doc updates.
5. **Push gate.** Only when tests pass **and** every requirement is confirmed:
   `git push -u origin richardh-feat-W#F#`. Report the branch + a summary. If the
   gate isn't met, stop, leave the branch local, and report exactly what's
   outstanding.
6. **Re-ingest into the knowledge graph.** After the push, fold the feature's new
   docs (the plan, updated detail doc, any new ADR, FEATURE_STATUS row) into the
   KG so future planning sees them. From `tools/knowledge-graph/`:
   - Layer 1 is automatic — it reads the repo live, so new docs already resolve in
     `kg.py structure`/`export` with no action.
   - Layer 2 (semantic index) needs an explicit re-ingest:
     ```bash
     cd tools/knowledge-graph
     python kg.py up          # start containerized Ollama (skips re-pull if models cached)
     python kg.py ingest      # re-index docs/ (also re-seeds Layer 1 edges)
     python kg.py down        # free model RAM
     ```
   - This is **best-effort, not a gate**: it needs Docker + the ~5GB models. If
     Ollama can't start or models aren't pulled, skip it and note in the summary
     that Layer 2 re-ingest was deferred — the push already succeeded and Layer 1
     is current regardless.

## Rules & conventions
- Branch naming is **`richardh-feat-W#F#`** — concatenated, no dash between W and
  F numbers (e.g. `richardh-feat-W2F4`, `richardh-feat-W3F1`).
- All feature branches base off **`richardh`**, never `main`.
- Plans live in `docs/plans/` and are version-controlled (committed on the
  feature branch). The detail doc + FEATURE_STATUS.md are updated in the same
  branch as the code.
- `docker-compose.yml` is authoritative for what runs; ignore `start.sh` /
  `test-services.sh`. test-management-service schema changes go through Alembic
  (`alembic revision --autogenerate`), not `create_all`.
- New routable endpoints need their pattern added to `ROUTES` in
  `services/api-gateway-service/main.py` — services aren't auto-discovered.
- Commit and push only as the plan specifies; the push is the final gated step,
  not something to do early.
- Do not expand scope past the feature's spec. If you discover adjacent
  defects/work, note them for a separate feature rather than bundling.
- The knowledge graph lives at `tools/knowledge-graph/` (run `kg.py` from that
  dir). It is a local dev tool, **not** part of the deployed stack — never add it
  to `docker-compose.yml` or the gateway `ROUTES`. Layer 1 (`structure`/`export`)
  needs no model; Layer 2 (`ingest`/`query`) needs `kg.py up` first.
