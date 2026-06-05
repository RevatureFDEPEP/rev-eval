from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.v1.routes.report_routes import router as report_router

load_dotenv()

app = FastAPI(title="Reporting & Analytics Service", version="1.0.0")

origins = settings.ALLOW_ORIGINS or "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins.split(",")] if origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report_router, prefix="/v1/api")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(getenv("PORT", 8004))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
