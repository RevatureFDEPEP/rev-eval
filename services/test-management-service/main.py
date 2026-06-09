from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.db.session import init_db
from src.middleware.correlation import CorrelationIdMiddleware
from src.utils import question_client
from src.utils.logging_config import setup_logging
from src.v1.routes.category_route import router as category_router
from src.v1.routes.session_route import router as session_router
from src.v1.routes.skill_route import router as skill_router
from src.v1.routes.test_route import router as test_router
from src.v1.routes.test_submission_route import router as test_submission_router

load_dotenv()

# Structured JSON logging (re-applied in the startup event — see
# setup_logging docstring for why)
setup_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)

app = FastAPI(title="Test Management Service", version="1.0.0")

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

# Correlation id for distributed log tracing (uses the gateway-forwarded
# X-Correlation-Id, generating one only for direct calls)
app.add_middleware(CorrelationIdMiddleware)

# ---- Routes ----
app.include_router(test_router, prefix="/v1/api")
app.include_router(skill_router, prefix="/v1/api")
app.include_router(test_submission_router, prefix="/v1/api")
app.include_router(category_router, prefix="/v1/api")
app.include_router(session_router, prefix="/v1/api")

# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

# ---- DB Init ----
@app.on_event("startup")
async def on_startup():
    setup_logging(settings.SERVICE_NAME, settings.LOG_LEVEL)
    await init_db()


# Close the cross-service httpx client singleton cleanly on shutdown.
@app.on_event("shutdown")
async def on_shutdown():
    await question_client.aclose()

# ---- Run server ----
if __name__ == "__main__":
    port = int(getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
