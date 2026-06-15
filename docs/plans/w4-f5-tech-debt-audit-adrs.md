# Plan — W4-F5: Technical Debt Audit & ADR Documentation

- **Feature:** W4-F5 — Technical Debt Audit & ADR Documentation (Day 20 capstone)
- **Detail doc:** [`docs/features/w4-f5-tech-debt-audit-adrs.md`](../features/w4-f5-tech-debt-audit-adrs.md)
- **Spec:** `days_16_20_features.md` §5 (Day 20), "Technical Debt Audit and ADR Documentation"
- **Depends on:** W4-F1 (cross-service data-access ADR — **already written** as `docs/adr/0001-...md`), W3-F2 (multi-select scoring ADR — to write), plus a substantially complete codebase (all prior W2/W3/W4 features ✅).
- **Unblocks:** — (capstone; reflective deliverable)

## Locked decisions

1. **This is a documentation/reflective feature.** The only *code* change is
   Step 4's inline AI-assistance annotations (comments only — no behaviour
   change). No new endpoints, no schema/migration, no `ROUTES` edit.
2. **ADR 0001 already exists** (cross-service data access, written during W4-F1).
   W4-F5 adds **ADR 0002** (multi-select scoring algorithm) and references 0001
   — it does not rewrite 0001. The spec requires "at least two"; we have two.
3. **AI-annotation scope (Step 4) is bounded, not repo-wide.** The entire repo
   was built with Claude Code, so annotating every file is unbounded and noise.
   We annotate a **representative set** of the most consequential AI-drafted
   sections — the two ADR subjects plus the two narrative features' core files —
   and record the verbal defence in `docs/ai-assistance.md`. The annotation
   convention is documented there so the practice is legible, not exhaustive.
4. **No scope expansion into *fixing* debt.** W4-F5 inventories and ranks debt;
   it does not repay it. Each debt item names a fix direction, but applying any
   fix is out of scope (would be its own feature).

## Context

- The codebase is feature-complete through W4-F4. W4-F5 is the reflective
  capstone: inventory shortcuts, rank them, write ADRs for the two pre-determined
  decisions, annotate AI-drafted code, and write a technical narrative.
- A thorough debt walkthrough has already been run (subagent sweep) and produced
  a grouped inventory — see Milestone 1 for the seed list. The W2-F8 defect log
  (`docs/features/w2-f8-pre-existing-defects.md`) and the W3-F6 true_false seed
  (in the detail doc Notes) are additional sources.
- ADR rationale for scoring already lives in the `partial_credit.py` module
  docstring (W3-F2 step 1 captured it deliberately). ADR 0002 lifts and expands
  that into the standard ADR structure; the docstring stays as the in-code
  pointer.
- ADR format to match: `docs/adr/0001-reporting-cross-service-data-access.md`
  (Status / Date / Feature / Deciders header; Context / Decision / Alternatives
  considered / Consequences sections).

## Step 0 — Branch & commit workflow

- `git fetch && git pull origin richardh` to update local `richardh`.
- Create feature branch **`richardh-feat-W4F5`** off `richardh` before any change.
- **First commit on the branch = this plan file.**
- One commit per milestone (Conventional Commits, matching repo history).
- Push `richardh-feat-W4F5` to origin **only** after the requirements review
  confirms every Step is met (no test suite runs for a docs-only feature beyond
  a `pnpm build`/`ruff` sanity check on the annotated files — see Testing).

## Milestones

### M1 — Debt inventory (`docs/technical-debt.md`) — Steps 1 & 2

Write `docs/technical-debt.md`. Intro paragraph (scope, "audit not repayment",
date, that current scale is local-first single-node dev). Then a table per
category, each row: **name · location (file:line) · condition under which it
matters · urgency (low/med/high vs. current scale)**. Seed content from the
completed walkthrough:

- **Unpaginated list endpoints** (high-fanout): `test_route.py` list_tests /
  created-by / submissions-by; `category_route.py` list_categories / skills;
  `skill_route.py` list_skills; `test_submission_route.py` (5 list endpoints);
  `question_routes.py` get_all_questions. Condition: fine at demo data, O(n)
  payload growth → slow/oversized responses at scale. Urgency: med (the W4
  reporting endpoints that *do* paginate show the intended pattern).
- **Missing input validation**: `question_routes.py` by-type / by-skill /
  by-difficulty / filter raw-string params (no enum), presigned content_type not
  enforced in signature. Urgency: low–med.
- **Hardcoded magic values / weak defaults**: `JWT_SECRET="change-me-in-production"`
  default (user + reporting settings, `.env.example`); CORS `allow_origins=["*"]`
  default (all 4 services); MinIO `minioadmin`/`minioadmin` defaults; presign
  expiry / page-size magic numbers repeated across endpoints. Urgency: **high**
  for the JWT default and CORS wildcard (security-relevant for any non-local
  deploy), low for the page-size numbers.
- **Schema not under migration**: user-service + question-service use
  `create_all`/Beanie init, not Alembic (only TMS is Alembic-owned). Condition:
  schema drift, no rollback story. Urgency: med.
- **Mocks where integration would help / missing test suites**: services with no
  `tests/` dir; idempotency replay not body-fingerprinted; QMS fetch under the
  `SELECT FOR UPDATE` lock (both W3-F7-noted). Urgency: low–med.
- **Auth boundary**: downstream services trust `X-User-*` headers without JWT
  re-verify (reporting is the lone exception, W4-F3). Condition: breaks if
  gateway is bypassed / service exposed directly. Urgency: med (architectural).
- **Legacy true_false rendering**: option-less true_false docs → "No options
  available" in `/take` (`SingleSelectQuestion.tsx`). Urgency: **low** (stale
  local volumes only; CI/fresh stacks never see them) — matches detail-doc seed.
- **Cruft**: checked-in `dev.db` SQLite; stale `start.sh`/`test-services.sh`
  referencing nonexistent services. Urgency: low.

Close with a **prioritized repayment backlog** (ordered high→low: JWT default &
CORS wildcard → migration coverage → pagination → header-trust hardening →
input validation → cruft removal → true_false widget).

*Files:* `docs/technical-debt.md` (new). **Commit:** `docs(w4-f5): technical-debt inventory + prioritized repayment backlog`.

### M2 — ADR 0002, scoring algorithm (`docs/adr/0002-...md`) — Step 3

Write `docs/adr/0002-multiselect-scoring-algorithm.md` matching the 0001 shape.
Content lifted/expanded from `partial_credit.py`:

- **Context:** multi-select (`multi`) questions need a fractional score that
  rewards partial knowledge; single-select uses exact set-equality
  (`exact_match.py`). Pure, deterministic, DB-free (W3-F2 step 1).
- **Decision:** **Jaccard index** `|correct ∩ submitted| / |correct ∪ submitted|`,
  bounded [0,1], symmetric (penalizes both missed-correct and spurious-wrong);
  `is_correct` reserved for exactly 1.0; empty correct-set → 0.0.
- **Alternatives considered:** all-or-nothing (discards partial signal);
  correct-minus-wrong (asymmetric, under-penalizes spurious picks, unbounded
  below before floor). Both quoted from the module docstring rationale.
- **Consequences:** simple/testable/order-independent; a candidate selecting all
  options gets a non-zero floor (`|correct|/|all|`) — accepted; free-text
  (`text`) scored 0.0 pending manual grading (out of scope, noted in W3-F2).
- Cross-link ADR 0001; note the in-code docstring is the canonical pointer.

*Files:* `docs/adr/0002-multiselect-scoring-algorithm.md` (new). **Commit:** `docs(w4-f5): ADR 0002 — multi-select Jaccard scoring`.

### M3 — AI-assistance annotations + verbal defence — Step 4

- Add `docs/ai-assistance.md`: states the whole repo was AI-assisted (Claude
  Code) under human review, documents the inline-annotation convention, and
  carries the **verbal defence** for the representative annotated sections (what
  the AI produced, what changed in review, why the final shape).
- Add concise inline annotations to the **representative** AI-drafted sections
  (comment-only; no behaviour change):
  - `services/test-management-service/src/scoring/partial_credit.py` (Jaccard) —
    already has a rich ADR docstring; add the standard AI-review annotation line.
  - `services/reporting-and-analytics-service/src/db/session.py` (read-only
    `tms_engine` / `get_tms_db` — the ADR-0001 cross-service seam).
  - `services/reporting-and-analytics-service/src/v1/dependencies/auth.py`
    (`require_trainer` JWT re-verify — W4-F3 defense-in-depth).
  - `frontend/src/lib/auth/access.ts` (`resolveAccess` shared RBAC resolver —
    W4-F4).
  Annotation convention (one comment block): *"AI-assisted (Claude Code);
  human-reviewed <area> — see docs/ai-assistance.md."*

*Files:* `docs/ai-assistance.md` (new) + 4 source files (comment-only). **Commit:** `docs(w4-f5): AI-assistance annotations + verbal defence`.

### M4 — Technical narrative (`docs/technical-narrative.md`) — Step 5

One page, two features (pick the two most interesting, each tied to a decision +
its ADR):

1. **Reporting cross-service data access (W4-F1)** → ADR 0001. What: read-heavy
   reporting service. Why: scores were visible nowhere; two-DB topology. How:
   read-only second engine over TMS Postgres, containment rules, projection as
   the documented evolution path.
2. **Scoring engine + attempt locking (W3-F2)** → ADR 0002. What: pure scoring +
   pessimistic lock + idempotency. Why: correctness under concurrent retries and
   fair partial credit. How: Jaccard pure functions, `SELECT FOR UPDATE`,
   idempotency-key dedup, state machine.

*Files:* `docs/technical-narrative.md` (new). **Commit:** `docs(w4-f5): technical narrative for reporting + scoring`.

### M5 — Requirements review + tracker updates

- Re-read the 5 detail-doc Steps + spec §5; confirm each satisfied, cite evidence
  (file path / commit). Check off the steps in
  `docs/features/w4-f5-tech-debt-audit-adrs.md`, add an Evidence section, set
  Status ✅.
- Update `docs/FEATURE_STATUS.md`: W4-F5 row → ✅ Completed; update the
  "Last assessed" narrative and the suggested-order item 12.
- **Commit:** `docs(w4-f5): requirements review — mark feature complete`.

## Testing & validation

Docs-only feature; no backend test suite is exercised by the content. Pass bar:

1. **Annotated source still parses/builds** — the only code touched is comments:
   - `ruff check services/test-management-service/src/scoring/partial_credit.py
     services/reporting-and-analytics-service/src/db/session.py
     services/reporting-and-analytics-service/src/v1/dependencies/auth.py`
     → clean.
   - `cd frontend && pnpm lint` → 0 errors (covers `access.ts`).
   - `cd frontend && pnpm build` → clean (sanity that the comment edit didn't
     break the TS build).
2. **Markdown sanity** — every new doc renders (links resolve, ADR 0002 follows
   the 0001 structure, technical-debt table columns consistent).
3. **No accidental behaviour change** — `git diff` on the 4 source files shows
   comment-only additions.

State the real output of each. Green bar = ruff clean + lint 0 + build clean +
comment-only diffs confirmed.

## Push gate

Push `richardh-feat-W4F5` to origin **only if** the validation bar above passes
**and** the requirements review confirms all 5 Steps met. Otherwise stop, leave
the branch local, report what's outstanding.
