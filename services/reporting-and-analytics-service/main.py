from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.db.session import verify_db_connection
from src.middleware.correlation import CorrelationIdMiddleware
from src.utils.logging_config import setup_logging
from src.v1.routes.reports_route import router as reports_router

load_dotenv()
setup_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)

app = FastAPI(title="Reporting & Analytics Service", version="1.0.0")

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
app.add_middleware(CorrelationIdMiddleware)


# ---- Routes ----
app.include_router(reports_router, prefix="/v1/api")


# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# ---- DB connection check (read-only; never creates tables) ----
@app.on_event("startup")
async def on_startup():
    await verify_db_connection()


# ---- Run server ----
if __name__ == "__main__":
    port = int(getenv("PORT", 8004))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
