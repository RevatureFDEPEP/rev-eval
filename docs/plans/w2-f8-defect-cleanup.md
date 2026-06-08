# W2-F8 — Pre-Existing Defect Cleanup (items 2–4)

## Context

`W2-F8` tracks defects that predate W2-F7, found while implementing the Alembic /
Category work. Item 1 (gateway 500 on 204 bodies) was already fixed inside W2-F7.
Items **2–4** remain — three independent, small-blast-radius bugs:

- **Item 2:** `GET /skills/{skill_id}/` always 500s — the route calls
  `SkillService.get_skill_by_id`, which is never defined (`AttributeError` at
  request time). The route has clearly never been exercised.
- **Item 3:** user-service carries two SQLAlchemy engines and a tangled
  `init_db.py` / `session.py` pair, with a circular `session ↔ user` import that
  only survives because `conftest.py` preloads `session` first.
- **Item 4:** Pydantic v1-style patterns deprecated for v3 are scattered across
  the backend (class `Config`, `.from_orm()`, `.copy()`, `.dict()`), warning on
  every pytest run.

Outcome: the skill GET route works (with a test), user-service has one clean db
module, and the backends are Pydantic-v2-clean. Detail file + status tracker
updated in the same branch.

Spec: `docs/features/w2-f8-pre-existing-defects.md`. **Item 4 scope: all backend
services** (per user decision), including `question-management-service`.

## Git workflow

- Branch from `richardh` → **`richardh-feat-w2f8`** (pattern `richardh-feat-w#f#`).
  ```bash
  git checkout richardh && git pull
  git checkout -b richardh-feat-w2f8
  ```
- **Commit at every milestone** (one commit per item, plus a docs commit). Commit
  messages end with the `Co-Authored-By: Claude` trailer per repo convention.
- Do not push / open PR unless explicitly asked.

---

## Milestone 1 — Item 2: `SkillService.get_skill_by_id` + test

Mirror `CategoryService.get_category_by_id` exactly (the route already does the
`ValueError → 404` mapping).

**`services/test-management-service/src/services/skill_service.py`** — add:
```python
@staticmethod
async def get_skill_by_id(db: AsyncSession, skill_id: int) -> SkillOut:
    skill = await SkillRepository.get_by_id(db, skill_id)
    if not skill:
        raise ValueError("Skill not found")
    return SkillOut.model_validate(skill)
```
- `SkillRepository.get_by_id` already exists (`skill_repository.py:11`).
- Use `model_validate` (not `from_orm`) so this folds into item 4; convert the
  other `SkillOut.from_orm(...)` calls in the same file (lines 13, 21, 33) while here.

**New test `services/test-management-service/tests/test_skill_service.py`** —
copy the structure of `tests/test_category_service.py`: `AsyncMock`-patch
`SkillRepository`, drive async methods with `asyncio.run()` (no DB, no
pytest-asyncio). Cover at minimum:
- `get_skill_by_id` returns `SkillOut` on hit;
- `get_skill_by_id` raises `ValueError("Skill not found")` on miss (`get_by_id → None`);
- a happy-path `create`/`list` for coverage.

**Sweep (spec note):** the route↔service-method audit was already run across all
`test-management-service` routes — `skill_route.get_skill` is the **only**
mismatch. No further missing methods. Note this in the detail file.

**Commit:** `fix(tms): add SkillService.get_skill_by_id so GET /skills/{id} returns 404 not 500`

---

## Milestone 2 — Item 3: collapse user-service db modules

Goal: one db module (`session.py`), one engine, no circular import, no dead code.

**`services/user-service/src/db/session.py`:**
- Add `Base = declarative_base()` locally; **remove** `from src.db.init_db import Base`.
- **Remove** the module-scope `from src.models.user import User` import.
- Inside `init_db()`, replace the empty `# Import all models here` comment with a
  **deferred** import so the model registers before `create_all` without a
  module-level cycle:
  ```python
  from src.models import user  # noqa: F401  (register tables before create_all)
  Base.metadata.create_all(bind=engine)
  ```
- Keep the single `engine` (`pool_pre_ping=True`), `SessionLocal`, `get_db`,
  `init_db` — these are the ones the app already uses.

**Delete `services/user-service/src/db/init_db.py`** — its `engine`/`SessionLocal`/
`get_db` are dead (only `Base` was ever imported, and only by `session.py`).

**`services/user-service/conftest.py`:**
- Change the fixture import `from src.db.init_db import Base` → `from src.db.session import Base` (line 41).
- Remove the now-obsolete circular-import workaround: the comment block (lines
  18–22) and `import src.db.session` (line 24). With the cycle gone, the preload
  is unnecessary. Keep the env-var defaults and `import pytest`.

**Unchanged (already import from `session.py`):** `models/user.py` (`Base`),
`db/seed.py` (`SessionLocal`), `utils/dependencies.py` + route files (`get_db`),
`main.py` (`init_db`). Blast radius confirmed: only `session.py` and `conftest.py`
referenced `init_db.py`.

**Verify:** `cd services/user-service && pytest` (cycle-free import in any order);
service boots and creates tables.

**Commit:** `refactor(user-service): collapse dual db engines into one session module`

---

## Milestone 3 — Item 4: Pydantic v2 migration (all backend services)

Mechanical, pattern-repeated across `user-service`, `test-management-service`,
`question-management-service`. Validators (`@field_validator`/`@model_validator`)
and `from_attributes` are already v2 — leave those.

**Pattern A — `class Config:` → `model_config = ConfigDict(...)`** (add
`from pydantic import ConfigDict`). Applies to every schema with
`from_attributes = True` and each `src/config/settings.py`:
- `from_attributes = True` → `model_config = ConfigDict(from_attributes=True)`
- settings `env_file=".env"` (and `case_sensitive`/`extra`) → `model_config = SettingsConfigDict(...)` (pydantic-settings) — keep the same keys.
- Representative files: `user-service/src/schemas/{auth,user}_schema.py`,
  `test-management-service/src/schemas/*.py` (test, test_submission, skill,
  test_skill, category), all three `src/config/settings.py`.

**Pattern B — `.from_orm(x)` → `.model_validate(x)`** (~20 sites):
`test_service.py`, `skill_service.py` (done in M1), `test_submission_service.py`.

**Pattern C — `.copy(update={...})` → `.model_copy(update={...})`** (6 sites,
all in `test_service.py`, chained off the `from_orm` calls).

**Pattern D — `.dict(...)` → `.model_dump(...)`; drop the `hasattr(x,'model_dump')`
shims** in `skill_repository.py`, `test_submission_repository.py`,
`test_skill_repository.py`, `test_repository.py`, `test_service.py` — models are
always v2 now, so collapse `... if hasattr(...) else ....dict()` to the
`model_dump` branch.

**Pattern E — question-management-service (higher care, Beanie/alias):**
- Beanie `Question` model `class Config: json_schema_extra={...}`
  (`src/models/question.py:100`) → `model_config = ConfigDict(json_schema_extra={...})`.
- `QuestionOut` `class Config` with `populate_by_name=True` + `json_encoders`
  (`src/schemas/question.py:313`) → `ConfigDict(populate_by_name=True, json_encoders={...})`.
  `json_encoders` is still accepted in v2 — keep it; verify serialization
  (`by_alias=True, mode='json'`) still round-trips (used at
  `question_routes.py:25`).

**Optional hardening:** pin `pydantic>=2,<3` and `pydantic-settings` in each
`requirements.txt` (currently unpinned) for reproducible builds. Confirm before
doing.

**Verify:** run pytest per service and grep that the patterns are gone:
```bash
grep -rn "class Config\|\.from_orm(\|\.copy(update\|\.dict(" services/*/src
```
(should return nothing meaningful) and confirm no `PydanticDeprecated` warnings
in pytest output.

**Commit:** `refactor(backends): migrate Pydantic v1 patterns to v2 API`
(or split user/tms vs question-service into two commits if the diff is large).

---

## Milestone 4 — Docs

- **`docs/features/w2-f8-pre-existing-defects.md`:** check off steps 2–4, add
  evidence (commit hashes, files, the route-sweep result), clear the
  **Remaining** section.
- **`docs/FEATURE_STATUS.md`:** flip W2-F8 row `🟡 In Progress` → `✅ Completed`;
  bump "Last assessed" line.
- This plan already lives here (`docs/plans/w2-f8-defect-cleanup.md`), version-controlled.

**Commit:** `docs: mark W2-F8 complete with evidence`

---

## End-to-end verification

```bash
# Per-service unit tests (CI mirror)
cd services/test-management-service && pytest -q          # incl. new test_skill_service.py
cd services/user-service && pytest -q                     # cycle-free imports
cd services/question-management-service && pytest -q       # if tests/ present

# Deprecation sweep (expect clean)
grep -rn "class Config\|\.from_orm(\|\.copy(update\|init_db" services/*/src

# Live: skill GET no longer 500s (the headline bug)
docker compose up --build -d
# create a skill, then:
curl -i http://localhost:8000/v1/api/skills/1/   # expect 200 (or 404 on miss), never 500
```

Acceptance: all three items closed, route returns 404/200 not 500, user-service
has one db module, pytest is deprecation-warning-free, docs updated.
