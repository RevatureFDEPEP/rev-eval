from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.db.session import init_db
from src.v1.routes.reports_route import router as reports_router

load_dotenv()

app = FastAPI(title="Reporting & Analytics Service", version="1.0.0")

# ---- CORS ----
# Day 16 topic: allow the frontend origin so the results page can fetch reports.
origins = settings.ALLOW_ORIGINS or "*"
allow_origins = ["*"] if origins == "*" else [o.strip() for o in origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routes ----
app.include_router(reports_router, prefix="/v1/api")


# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# ---- DB Init ----
@app.on_event("startup")
async def on_startup():
    await init_db()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(getenv("PORT", "8004")),
        reload=False,
    )
