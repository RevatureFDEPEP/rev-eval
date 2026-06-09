import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.db.session import close_db, init_db
from src.logging_config import configure_json_logging, install_request_logging
from src.v1.routes.question_routes import router as question_router

configure_json_logging()

app = FastAPI(
    title="Question Management Service",
    version="1.0.0",
    description="Microservice for managing questions with MongoDB storage",
    docs_url="/docs",
    redoc_url="/redoc"
)
install_request_logging(app)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routes
app.include_router(question_router, prefix="/v1/api")

# ---- Health Endpoint ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.on_event("shutdown")
async def on_shutdown():
    """Close MongoDB connection on shutdown."""
    try:
        await close_db()
    except Exception:
        import logging

        logging.getLogger(__name__).exception("MongoDB connection close failed")

# ---- Run server ----
if __name__ == "__main__":
    port = int(settings.PORT) if isinstance(settings.PORT, str) else settings.PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
