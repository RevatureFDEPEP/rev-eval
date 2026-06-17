# W2-F7 Implementation Plan — Alembic Migrations & Category Domain

**Status:** ✅ Completed  
**Tracker:** `docs/features/w2-f7-alembic-category-domain.md`  
**Spec:** `docs/feature_specs/w2-f7-alembic-category-domain.md`  
**Branch:** `tianyac-alembic-migrations`  
**Updated:** 2026-06-17

---

## Goal

Two deliverables:

1. **Category domain** in test-management-service — `Category` model with M:N relationship to `Test`, Alembic migration, full repository/service/router stack, exposed at `/v1/api/categories` through the gateway.
2. **Reporting service scaffold** — stand up `reporting-and-analytics-service` with its own Postgres container and Alembic baseline migration.

Plus three known defects to fix during verification.

---

## Baseline State

| Item | State before W2-F7 |
|---|---|
| Alembic in test-management-service | Initialized; head = `0004_add_quiz_sessions` (`down_revision=None`) |
| Category model | Does not exist |
| reporting-and-analytics-service | Directory exists, only a `README.md` |
| Gateway `/v1/api/categories` route | Not configured |
| `SkillService.get_skill_by_id` | Missing — route calls it, triggers 500 |
| user-service engines | Two separate engine instances (session.py + init_db.py) |

---

## Part 1 — Category Domain (test-management-service)

### Step 1 — SQLAlchemy Model

**Create:** `services/test-management-service/src/models/category.py`

```python
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship
from src.db.session import Base

test_categories = Table(
    "test_categories",
    Base.metadata,
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
    Column("test_id", Integer, ForeignKey("tests.id"), primary_key=True),
)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    tests = relationship("Test", secondary="test_categories", back_populates="categories")
```

**Modify:** `services/test-management-service/src/models/test.py` — add reverse relationship:

```python
categories = relationship("Category", secondary="test_categories", back_populates="tests")
```

> **Important:** `tests/conftest.py` must import `Category` so the `test_categories` Table is in `Base.metadata` before SQLAlchemy configures mappers. Without this, `secondary="test_categories"` raises `InvalidRequestError` in tests.

**Modify:** `services/test-management-service/tests/conftest.py`:

```python
from src.models.category import Category  # noqa: F401  ← add this line
```

### Step 2 — Alembic Migration

**Create:** `services/test-management-service/migrations/versions/0005_add_categories.py`

```python
revision: str = "0005"
down_revision: Union[str, None] = "0004"

def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "test_categories",
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("tests.id"), primary_key=True),
    )

def downgrade() -> None:
    op.drop_table("test_categories")
    op.drop_table("categories")
```

**Modify:** `services/test-management-service/migrations/env.py` — add import:

```python
import src.models.category  # noqa: F401, E402
```

**Run migration:**

```bash
cd services/test-management-service
alembic upgrade head
# → 0004 → 0005 (head)
```

### Step 3 — Pydantic Schemas

**Create:** `services/test-management-service/src/schemas/category_schema.py`

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase): pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CategoryOut(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
```

### Step 4 — Repository

**Create:** `services/test-management-service/src/repositories/category_repository.py`

Static async methods: `get_by_id`, `list_all`, `create`, `update`, `delete`. Pattern matches `skill_repository.py`.

### Step 5 — Service

**Create:** `services/test-management-service/src/services/category_service.py`

Methods: `get_category_by_id`, `list_categories`, `create_category`, `update_category`, `delete_category`. Raises `ValueError` for not-found; uses `CategoryOut.model_validate(obj)` (Pydantic v2).

### Step 6 — Router

**Create:** `services/test-management-service/src/v1/routes/category_route.py`

```python
router = APIRouter(prefix="/categories", tags=["Categories"])
# POST /          → 201
# GET /           → 200
# GET /{id}/      → 200 | 404
# PUT /{id}/      → 200 | 404
# DELETE /{id}/   → 204 | 404
```

Pattern matches `skill_route.py`.

### Step 7 — Wire Up

**Modify:** `services/test-management-service/main.py`:

```python
from src.v1.routes.category_route import router as category_router
...
app.include_router(category_router, prefix="/v1/api")
```

**Modify:** `services/test-management-service/src/db/session.py` — add to `init_db()`:

```python
from src.models import category, quiz_session  # noqa: F401
```

**Modify:** `services/api-gateway-service/main.py` — add to `ROUTES`:

```python
{"pattern": r"^/v1/api/categories(/.*)?$", "service": "test-management-service"},
```

---

## Part 2 — Reporting Service Scaffold

### Step 8 — FastAPI App

**Create:** `services/reporting-and-analytics-service/main.py`

```python
app = FastAPI(title="Reporting and Analytics Service", version="1.0.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

**Create:** `services/reporting-and-analytics-service/src/config/settings.py`

Pydantic `BaseSettings` with `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_NAME`, `PORT=8004`. Property `SQLALCHEMY_DATABASE_URL` returns `postgresql+psycopg2://...`.

**Create:** `services/reporting-and-analytics-service/requirements.txt`

```
fastapi
uvicorn[standard]
SQLAlchemy
pydantic
pydantic-settings
python-dotenv
alembic
psycopg2-binary
```

**Create:** `services/reporting-and-analytics-service/Dockerfile`

Based on `python:3.11-slim`, exposes port 8004, runs `python main.py`.

### Step 9 — Docker Compose

**Modify:** `docker-compose.yml` — add two new services:

```yaml
reporting-postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_USER: ${REPORTING_POSTGRES_USER:-reporting}
    POSTGRES_PASSWORD: ${REPORTING_POSTGRES_PASSWORD:-reporting}
    POSTGRES_DB: ${REPORTING_POSTGRES_DB:-reporting_dev}
  volumes:
    - reporting_postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${REPORTING_POSTGRES_USER:-reporting}"]

reporting-and-analytics-service:
  build:
    context: ./services/reporting-and-analytics-service
  environment:
    DB_HOST: reporting-postgres
    PORT: 8004
  ports:
    - "8004:8004"
  depends_on:
    reporting-postgres:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
```

Add `reporting_postgres_data:` to the top-level `volumes:` block.

### Step 10 — Alembic Baseline

```
services/reporting-and-analytics-service/
├── alembic.ini                          # script_location = migrations
├── migrations/
│   ├── env.py                           # sync engine (psycopg2), imports settings
│   ├── script.py.mako
│   └── versions/
│       └── 0001_baseline.py            # no-op upgrade/downgrade, down_revision=None
```

**Run in reporting service:**

```bash
cd services/reporting-and-analytics-service
alembic upgrade head
# → 0001 (head)
```

---

## Part 3 — Defect Fixes

### Defect A — skill-500

**Root cause:** `skill_route.py:22` calls `SkillService.get_skill_by_id(db, skill_id)` but that method did not exist → `AttributeError` → 500.

**Fix:** Add to `services/test-management-service/src/services/skill_service.py`:

```python
@staticmethod
async def get_skill_by_id(db: AsyncSession, skill_id: int) -> SkillOut:
    skill = await SkillRepository.get_by_id(db, skill_id)
    if not skill:
        raise ValueError("Skill not found")
    return SkillOut.from_orm(skill)
```

### Defect B — user-service dual-engine

**Root cause:** `session.py` imported `Base` from `init_db.py` but created its own `engine` and `SessionLocal`, resulting in two separate connection pools.

**Fix:** Modify `services/user-service/src/db/session.py` to import all three from `init_db`:

```python
from src.db.init_db import Base, SessionLocal, engine
```

Remove the duplicate `create_engine(...)` and `sessionmaker(...)` calls from `session.py`.

### Defect C — Pydantic v2

No `@validator` or `orm_mode = True` found in any service. All schemas already use `from_attributes = True`. No changes needed.

---

## Files Changed

| Action | Path |
|---|---|
| Create | `services/test-management-service/src/models/category.py` |
| Create | `services/test-management-service/src/schemas/category_schema.py` |
| Create | `services/test-management-service/src/repositories/category_repository.py` |
| Create | `services/test-management-service/src/services/category_service.py` |
| Create | `services/test-management-service/src/v1/routes/category_route.py` |
| Create | `services/test-management-service/migrations/versions/0005_add_categories.py` |
| Create | `services/reporting-and-analytics-service/main.py` |
| Create | `services/reporting-and-analytics-service/requirements.txt` |
| Create | `services/reporting-and-analytics-service/Dockerfile` |
| Create | `services/reporting-and-analytics-service/src/config/settings.py` |
| Create | `services/reporting-and-analytics-service/alembic.ini` |
| Create | `services/reporting-and-analytics-service/migrations/env.py` |
| Create | `services/reporting-and-analytics-service/migrations/script.py.mako` |
| Create | `services/reporting-and-analytics-service/migrations/versions/0001_baseline.py` |
| Modify | `services/test-management-service/src/models/test.py` (add categories relationship) |
| Modify | `services/test-management-service/migrations/env.py` (import category model) |
| Modify | `services/test-management-service/src/db/session.py` (import category in init_db) |
| Modify | `services/test-management-service/main.py` (register category router) |
| Modify | `services/test-management-service/tests/conftest.py` (import Category model) |
| Modify | `services/test-management-service/src/services/skill_service.py` (add get_skill_by_id) |
| Modify | `services/user-service/src/db/session.py` (remove duplicate engine) |
| Modify | `services/api-gateway-service/main.py` (add /categories route) |
| Modify | `docker-compose.yml` (add reporting-postgres + reporting-and-analytics-service) |

---

## Verification

```bash
# 1. TMS migration at head
cd services/test-management-service
alembic upgrade head
alembic current
# → 0005 (head)

# 2. Category CRUD (requires running stack)
TOKEN=$(curl -s -X POST http://localhost:8000/v1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"trainer@test.com","password":"test123"}' | jq -r '.access_token')

curl -s -X POST http://localhost:8000/v1/api/categories/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Python", "description": "Python programming"}' | jq .
# → 201

curl -s http://localhost:8000/v1/api/categories/ \
  -H "Authorization: Bearer $TOKEN" | jq .
# → 200 [{...}]

curl -s http://localhost:8000/v1/api/categories/1/ \
  -H "Authorization: Bearer $TOKEN" | jq .
# → 200 {id:1, name:"Python", ...}

curl -s http://localhost:8000/v1/api/categories/9999/ \
  -H "Authorization: Bearer $TOKEN"
# → 404

# 3. Skill 500 fixed
curl -s http://localhost:8000/v1/api/skills/1/ \
  -H "Authorization: Bearer $TOKEN"
# → 200 (not 500)

# 4. Reporting service health
curl -s http://localhost:8004/health
# → {"status": "ok"}

# 5. Reporting Alembic baseline
cd services/reporting-and-analytics-service
alembic upgrade head
alembic current
# → 0001 (head)

# 6. All TMS tests pass
cd services/test-management-service
pytest tests/ -q
# → 133 passed
```
