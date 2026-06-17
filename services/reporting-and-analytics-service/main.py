from contextlib import asynccontextmanager
from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.session import init_db
from src.config.settings import settings
from src.v1.routes.report_route import router as report_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Reporting & Analytics Service",
    version="1.0.0",
    lifespan=lifespan,
)

origins = settings.ALLOW_ORIGINS or "*"
allow_origins = ["*"] if origins == "*" else [o.strip() for o in origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report_router, prefix="/v1/api")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":  # pragma: no cover
    port = int(getenv("PORT", 8004))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
