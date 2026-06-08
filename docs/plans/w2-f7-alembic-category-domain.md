# W2-F7 — Alembic Migrations & Category Domain

## Context

W2-F7 (`docs/features/w2-f7-alembic-category-domain.md`, spec `days_6_10_features.md` §7, Day 10) brings test-management-service's relational schema under Alembic and adds a Category domain (M2M with Skill). Currently no `alembic/` exists anywhere; tables are made by SQLAlchemy `create_all` on every boot (`start.sh` + app startup), which can only create missing tables — never evolve them. W2-F7 unblocks W3-F1 (sessions migration) and W2-M10 (reporting Alembic pattern).

**User decisions (locked):**
1. **Baseline + categories revisions** — 0001 baseline of existing schema, 0002 categories; `alembic stamp` for legacy volumes.
2. **Remove `create_all` entirely** — Alembic is the only path for structure **and seeding**. (`init_db()` becomes a connectivity check; SQLAlchemy ORM/engine/sessions remain — Alembic itself is built on SQLAlchemy, only the schema-creation role is removed.)
3. **Users seeding moves to user-service** — `users` belongs to user-service; test-management migrations must not touch it.

**Key constraint:** shared Postgres DB `eval_ai_dev` — `users` table is owned by user-service and is NOT in this service's metadata. Alembic autogenerate must ignore it (`include_object` filter in env.py + manual review).

**Ordering guarantee (already exists):** `docker-compose.yml:159-163` — test-management `depends_on: user-service: condition: service_healthy`. If user-service seeds users during its FastAPI startup (before /health responds), users exist before test-management's migrations run. Seed migration fails hard if no trainer user → failure is NOT recorded by Alembic → container restart (`unless-stopped`) retries → self-healing.

## Migration chain

| Rev | Name | Contents |
|---|---|---|
| 0001 | baseline existing schema | create_table for `tests`, `skills`, `test_skills`, `test_submissions` (autogen vs empty DB, scrubbed of anything touching `users`) |
| 0002 | add categories and skills relationship | `categories` table + `category_skills` association (unique on category_id+skill_id) |
| 0003 | seed demo data | data migration: skills, tests, test_submissions, demo categories ("Python", "Docker", "Algorithms") + skill links. Idempotent guards (skip table if count>0 — protects already-seeded legacy DBs). Queries `users` for trainer/participant ids; **raises if no trainer found** (retry-on-restart semantics). Port logic from `seed_db.py` using `op.get_bind()` + SQLAlchemy core inserts. |

Use readable revision ids (`0001`, `0002`, `0003` via `alembic revision --rev-id`).

**Legacy volume adoption (in start.sh):** if `alembic_version` absent AND `skills` exists → `alembic stamp 0001`, then `alembic upgrade head` (applies 0002+0003; 0003 guards skip existing data). Fresh volume: upgrade runs all three.

## Implementation steps

### 0. Branch & commit workflow
- **`git fetch && git pull origin richardh`** (update local `richardh`), then **create feature branch `richardh-feat-alembic` from `richardh`** before any code change.
- **First commit: save this plan to `docs/plans/w2-f7-alembic-category-domain.md`** (version-controlled plans convention).
- **Commit regularly** — one commit per logical chunk, roughly per lettered section below (user-service seed move; Category domain; gateway route; Alembic init + migrations; startup rewiring; tests; docs). Conventional Commits style as in repo history.

### A. user-service: own its users seeding
1. **Create `services/user-service/src/db/seed.py`** — idempotent `seed_users()`: skip if `SELECT COUNT(*) FROM users` > 0; else insert the 7 demo users (2 trainers, 5 participants, bcrypt `password123`) — port from `services/test-management-service/seed_db.py:33-75`, but async via the service's own session/models (it has a User model + passlib already).
2. **Call it from user-service startup** (its `main.py` startup event, after `init_db()`). Healthcheck `/health` only passes after startup completes → downstream ordering holds.

### B. test-management-service: Category domain (mirror Skill slice)
3. **`src/models/category.py`** — `Category` (`id`, `name` String unique not null, `description` Text nullable); plain `Table("category_skills", Base.metadata, ...)` association (FKs → categories.id / skills.id, UniqueConstraint) + `skills = relationship("Skill", secondary=category_skills)`. Plain Table (not assoc model) — link carries no metadata, simpler than `test_skill.py` pattern.
4. **`src/models/skill.py`** — add `categories = relationship("Category", secondary="category_skills", viewonly=True)` (category side owns writes).
5. **`src/schemas/category_schema.py`** — `CategoryBase/Create/Update/Out`; `CategoryOut` includes `skills: list[SkillOut] = []`, `from_attributes`. Reuse `SkillOut` from `skill_schema.py`.
6. **`src/repositories/category_repository.py`** — async static methods like `skill_repository.py`: `get_by_id` (with `selectinload(Category.skills)` — required, lazy-load under async raises MissingGreenlet), `list_all`, `create`, `update`, `delete`, `link_skill`, `unlink_skill`.
7. **`src/services/category_service.py`** — mirror `skill_service.py`; `link_skill/unlink_skill` resolve both ids (reuse `SkillRepository.get_by_id`), ValueError on missing. Use `model_validate` (not deprecated `from_orm`).
8. **`src/v1/routes/category_route.py`** — `prefix="/categories"`, trailing-slash style matching `skill_route.py`:
   - `POST /` 201, `GET /`, `GET /{id}/`, `PUT /{id}/`, `DELETE /{id}/` 204
   - `POST /{id}/skills/{skill_id}/` 201 link (idempotent on duplicate), `DELETE /{id}/skills/{skill_id}/` 204 unlink, `GET /{id}/skills/` list
   - ValueError → 404.
9. **`main.py`** — `app.include_router(category_router, prefix="/v1/api")`.

### C. Gateway
10. **`services/api-gateway-service/main.py` ROUTES (~line 55)** — add `{"pattern": r"^/v1/api/categories(/.*)?$", "service": "test-management-service"}`.

### D. Alembic
11. **`alembic init -t async alembic`** from `services/test-management-service/` → `alembic.ini`, `alembic/env.py`, `alembic/versions/`.
12. **`alembic/env.py`** — import Base + all 5 models; `target_metadata = Base.metadata`; URL at runtime: `os.getenv("DATABASE_URL") or settings.SQLALCHEMY_DATABASE_URL`, force `postgresql+asyncpg://` (same conversion as `src/db/session.py:20-25`); `compare_type=True`; **`include_object` filter: skip tables not in `Base.metadata.tables`** (excludes `users` from autogen). `alembic.ini`: `prepend_sys_path = .`, blank `sqlalchemy.url`.
13. **Generate 0001** (`--autogenerate --rev-id 0001` vs scratch DB) — review/scrub. **0002** (`--rev-id 0002 -m "Add categories and skills relationship"` per spec wording). **0003** hand-written data migration (see chain table); downgrade = delete seeded rows (best-effort) or `pass` with comment.

### E. Startup rewiring (test-management-service)
14. **`start.sh`** — keep Postgres wait-loop; replace init_db + seed_db.py blocks with:
    ```bash
    # adopt-or-migrate: stamp baseline on DBs that predate alembic
    if [ tables exist but no alembic_version ]; then alembic stamp 0001; fi
    alembic upgrade head || exit 1   # fail → container restarts → retry
    exec python main.py
    ```
    (table checks = small psycopg2 one-liners like existing readiness check, query `information_schema.tables`.)
15. **`src/db/session.py` `init_db()`** — remove `create_all`; keep model imports (relationship registration) + `SELECT 1` check. Update docstring.
16. **Delete `seed_db.py`** — users logic → user-service (step 1), rest → migration 0003.

### F. Tests
17. **`tests/test_category_service.py`** — mock-based (AsyncMock repo patches): CRUD returns `CategoryOut`, missing-id raises ValueError, link/unlink missing category/skill raises. Mirrors question-service unit-test style.
18. **Schema tests** (extend `tests/test_smoke.py` or new file) — `CategoryCreate` requires name; `CategoryUpdate` all-optional; `CategoryOut.model_validate` with nested skills.
19. **user-service test** for `seed_users` idempotency (it has tests/ + conftest already).

### G. Docs (same PR — tracker convention)
20. **`docs/FEATURE_STATUS.md`** — W2-F7 row → ✅/🟡, update "Last assessed".
21. **`docs/features/w2-f7-alembic-category-domain.md`** — check off steps, evidence (paths, rev ids, PR), record decisions (create_all removed; Alembic owns structure+seed; users seeding moved to user-service) under Notes.
22. **`rev-eval/CLAUDE.md`** — update seed command line (`seed_db.py` gone; seeding now via migrations / user-service startup).
23. ~~`docs/plans/w2-f7-alembic-category-domain.md`~~ — saved in step 0 (first commit on the branch).

## Verification

1. **Fresh stack:** `docker compose down -v && docker compose up --build` — logs show user-service seeding users, then test-management `alembic upgrade head` applying 0001→0003; `alembic_version`=0003; `\dt` shows `categories`, `category_skills`; login as trainer1@revature.com/password123 works.
2. **Legacy volume sim:** start once on old code's volume (or restore), then new code — logs show `stamp 0001` + upgrade applying only 0002/0003; no duplicate-table errors; no duplicate seed rows.
3. **API through gateway:** create category, link skill, fetch with nested skills, unlink, delete (curl per route list above); 404s on bad ids; gateway routes `/v1/api/categories` correctly.
4. **`pytest --cov`** in test-management-service and user-service; **`ruff check`** clean (W2-F4 CI gates).
5. **Migration chain:** `alembic history` shows 0001→0002→0003; `alembic downgrade 0002 && alembic upgrade head` round-trips.

## Risks / watch-items

- Autogen trying to drop `users` → mitigated by `include_object` + manual scrub (load-bearing review).
- 0003 needs trainer user id → guaranteed in compose by existing healthy-dependency; bare-metal failure is loud and retryable (not recorded as applied).
- Nested skills serialization → `selectinload` mandatory in repo reads.
- `%` in DB password breaks ini interpolation → set URL via `config.set_main_option` with escaping or `config.attributes`.
- Frontend/dashboards don't consume seed data shapes differently — seed contents unchanged, only delivery mechanism.
