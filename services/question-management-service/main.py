import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.db.session import close_db, init_db
from src.utils.s3_client import ensure_bucket
from src.v1.routes.question_routes import router as question_router

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

# routes
app.include_router(question_router, prefix="/v1/api")

# ---- Health Endpoint ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await init_db()
    # Best-effort bucket bootstrap — no `mc` init container exists. Non-fatal:
    # if MinIO is briefly unavailable at boot, the first upload will surface it.
    try:
        ensure_bucket()
    except Exception as e:
        print(f"⚠️ MinIO bucket ensure failed (uploads may 500 until fixed): {e}")

@app.on_event("shutdown")
async def on_shutdown():
    """Close MongoDB connection on shutdown."""
    try:
        await close_db()
    except Exception as e:
        print(f"⚠️ MongoDB connection close failed: {e}")

# ---- Run server ----
if __name__ == "__main__":
    port = int(settings.PORT) if isinstance(settings.PORT, str) else settings.PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
