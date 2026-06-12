from os import getenv

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.logging_config import configure_json_logging, install_request_logging
from src.v1.routes.report_route import router as report_router

load_dotenv()
configure_json_logging()

app = FastAPI(title="Reporting & Analytics Service", version="1.0.0")
install_request_logging(app)

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
app.include_router(report_router, prefix="/v1/api")


# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


# ---- Run server ----
if __name__ == "__main__":
    port = int(getenv("PORT", 8004))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
