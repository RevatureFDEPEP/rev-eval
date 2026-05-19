from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from src.v1.routes.test_route import router as test_router
from src.v1.routes.skill_route import router as skill_router
from src.v1.routes.test_submission_route import router as test_submission_router
from src.db.session import init_db
from src.config.settings import settings

load_dotenv()

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

# ---- Routes ----
app.include_router(test_router, prefix="/v1/api")
app.include_router(skill_router, prefix="/v1/api")
app.include_router(test_submission_router, prefix="/v1/api")

# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

# ---- DB Init ----
@app.on_event("startup")
async def on_startup():
    await init_db()

# ---- Run server ----
if __name__ == "__main__":
    port = int(getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
