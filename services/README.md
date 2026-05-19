

# 🧠 **Rev EvalAI Backend**

A modular **FastAPI-based backend** for the **EvalAI Interview Evaluation Platform**.
This service powers AI-driven test and participant management, supporting roles, dashboards, and microservice communication.

---

## 📁 **Project Structure**

```
evalai-backend/
│
├── src/
│   ├── config/
│   │   ├── settings.py         # Loads environment variables (DB config, secrets)
│   │   └── __init__.py
│   │
│   ├── db/
│   │   ├── init.py             # DB engine, session, Base declaration
│   │   └── __init__.py
│   │
│   ├── models/                 # SQLAlchemy models
│   │   ├── test_model.py
│   │   ├── participant_model.py
│   │   └── __init__.py
│   │
│   ├── repositories/           # Data access logic (CRUD, joins, queries)
│   │   ├── test_repository.py
│   │   ├── participant_repository.py
│   │   └── __init__.py
│   │
│   ├── schemas/                # Pydantic models (request/response)
│   │   ├── test_schema.py
│   │   ├── participant_schema.py
│   │   └── __init__.py
│   │
│   ├── services/               # Business logic layer
│   │   ├── test_service.py
│   │   ├── participant_service.py
│   │   └── __init__.py
│   │
│   ├── v1/
│   │   └── routes/             # FastAPI routers
│   │       ├── test_routes.py
│   │       ├── participant_routes.py
│   │       └── __init__.py
│   │
│   ├── utils/                  # Helper functions, constants, logging, validation
│   │   ├── logger.py
│   │   └── __init__.py
│   │
│   └── main.py                 # Entry point — initializes FastAPI app and routes
│
├── .env                        # Environment variables (DB credentials, secrets)
├── requirements.txt             # Dependencies
├── Dockerfile                   # Optional containerization
├── README.md                    # You are here
└── alembic/                     # (Optional) for database migrations
```

---

## ⚙️ **Environment Variables**

Create a `.env` file in the project root with the following keys:

```
DB_HOST=your-db-endpoint
DB_PORT=5432
DB_USERNAME=postgres
DB_PASSWORD=yourpassword
DB_NAME=evalai
```

---

## 🚀 **Local Setup**

### **1️⃣ Create Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### **2️⃣ Install Dependencies**

```bash
pip install -r requirements.txt
```

### **3️⃣ Setup Database**

Ensure PostgreSQL (or RDS) is running and the credentials match `.env`.

Initialize database tables:

```bash
python -m src.main --init-db
```

### **4️⃣ Run Application**

```bash
uvicorn src.main:app --reload
```

### **5️⃣ Access**

* API: `http://localhost:8000`
* Docs: `http://localhost:8000/docs`

---

## 🧩 **Tech Stack**

| Component   | Technology                |
| ----------- | ------------------------- |
| Framework   | FastAPI                   |
| ORM         | SQLAlchemy (2.x)          |
| Database    | PostgreSQL / AWS RDS      |
| Validation  | Pydantic                  |
| Task Queue  | (Optional) Celery + Redis |
| HTTP Client | httpx (async)             |

---

## 🧱 **Development Guidelines**

### **Adding a New Feature / Microservice**

1. **Create Model(s)** in `src/models/`

   * Define DB schema using SQLAlchemy ORM.
2. **Add Schema(s)** in `src/schemas/`

   * Use Pydantic for request/response validation.
3. **Create Repository Layer** in `src/repositories/`

   * Add CRUD and query logic.
4. **Add Service Layer** in `src/services/`

   * Implement business logic that coordinates repositories.
5. **Expose Routes** in `src/v1/routes/`

   * Add API endpoints using FastAPI routers.
6. **Register Router** in `main.py`

   ```python
   from src.v1.routes import test_routes, participant_routes
   app.include_router(test_routes.router, prefix="/api/v1/tests")
   app.include_router(participant_routes.router, prefix="/api/v1/participants")
   ```

---

### **Updating Models**

* Never modify existing columns directly in production.
* Use **Alembic migrations** for schema evolution:

  ```bash
  alembic revision --autogenerate -m "Add new field to tests"
  alembic upgrade head
  ```

---

### **Async Guidelines**

If async is enabled:

* Use `create_async_engine()` and `AsyncSession`.
* Use `await` for all DB and network calls.
* Never mix sync and async sessions in the same function.

---

### **Code Style**

* Follow **PEP8**.
* Use type hints (`-> str`, `-> dict`).
* One model/service/repository per file.
* Keep functions small and descriptive.

---

### **Error Handling**

* Centralize custom exceptions in `src/utils/exceptions.py`.
* Use FastAPI’s `HTTPException` for API-level errors.

---

### **Logging**

Use the logger from `src/utils/logger.py`:

```python
from src.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("Test created successfully")
```

---

### **Branching & PRs**

* `main`: stable production branch
* `develop`: integration branch
* Feature branches: `feature/<name>`
* Create a PR to `develop` → reviewed → merged to `main` via version release.


### ✅ **Summary**

This backend follows:

* **Clean architecture (Config → DB → Model → Repository → Service → Route)**
* **Extensibility** for multiple microservices
* **Async-ready** for modern, scalable backend communication
