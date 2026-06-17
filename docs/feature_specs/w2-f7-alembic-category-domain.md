# W2-F7 — Relational Schema Evolution using Alembic Migrations & Scaffolded Domain

*Extend the relational testing models to include a new "Question Categories" domain, scaffolding the database layers and updating schemas safely.*

* **Curriculum Fit**: Day 10 (Alembic Relational Evolution, FastAPI Service Conventions, and Compose composition).
* **Prerequisites**: Day 10 topics.
* **Required for**: W3-F1 (Quiz Session Creation Backend — the sessions table is a new Alembic migration on top of the existing test-management-service schema established here), W4-F1 (Candidate Results Reporting Endpoints — reporting-and-analytics-service Alembic environment must be initialized before new reporting migrations can run)
* **Time Estimate**: Without AI tools: 4–7 hours | With AI tools (Gemini/Claude Code): 2–3 hours

## Implementation Details

1. In test-management-service, add a new SQLAlchemy model `Category` (representing topics like "Python", "Docker", "Algorithms") and create a many-to-many relationship with `Skill`.
2. Initialize Alembic inside `services/test-management-service/` (if not done) or add models to the existing Alembic env context.
3. Run `alembic revision --autogenerate -m "Add categories and skills relationship"` to generate the migration script, review the script, and run `alembic upgrade head`.
4. Scaffold the standard repository, service, and router layers to allow trainers to fetch, create, and link Categories conforming to standard project conventions.
