import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.db.session import close_db, init_db
from src.middleware.correlation import CorrelationIdMiddleware
from src.utils.logging_config import setup_logging
from src.v1.routes.question_routes import router as question_router

# Structured JSON logging (re-applied in the startup event — see
# setup_logging docstring for why)
setup_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)

app = FastAPI(
    title="Question Management Service",
    version="1.0.0",
    description="Microservice for managing questions with MongoDB storage",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Correlation id for distributed log tracing (uses the gateway-forwarded
# X-Correlation-Id, generating one only for direct calls)
app.add_middleware(CorrelationIdMiddleware)

# routes
app.include_router(question_router, prefix="/v1/api")

# ---- Health Endpoint ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    setup_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)
    await init_db()

@app.on_event("shutdown")
async def on_shutdown():
    """Close MongoDB connection on shutdown."""
    try:
        await close_db()
    except Exception as e:
        logging.getLogger(__name__).warning(f"MongoDB connection close failed: {e}")

# ---- Run server ----
if __name__ == "__main__":
    port = int(settings.PORT) if isinstance(settings.PORT, str) else settings.PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
