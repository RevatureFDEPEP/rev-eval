from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.db.session import init_db

load_dotenv()

app = FastAPI(title="Reporting and Analytics Service", version="1.0.0")

# ---- CORS ----
origins = settings.ALLOW_ORIGINS or "*"
if origins == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routes ----
# Business endpoints land in W4-F1 (Candidate Results Reporting Endpoints).
# Routers are included here with the standard /v1/api prefix, e.g.:
#     app.include_router(reports_router, prefix="/v1/api")
# When they are added, register the matching pattern in the api-gateway
# ROUTES table — services are not auto-discovered.

# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

# ---- DB Init ----
@app.on_event("startup")
async def on_startup():
    # Schema is owned by Alembic (start.sh runs `alembic upgrade head` before
    # the app boots); init_db() is a connectivity check only.
    await init_db()

# ---- Run server ----
if __name__ == "__main__":
    port = int(getenv("PORT", settings.PORT))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
