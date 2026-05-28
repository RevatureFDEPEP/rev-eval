from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from src.v1.routes.auth_route import router as auth_router
from src.v1.routes.user_route import router as user_router
from src.db.session import init_db
from src.config.settings import settings

load_dotenv()

app = FastAPI(title="User Service", version="1.0.0")

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
# Register authentication and user management routes under /v1/api.
# The auth router handles login/register flows, and user router handles
# profile and user CRUD operations.
app.include_router(auth_router, prefix="/v1/api")
app.include_router(user_router, prefix="/v1/api")

# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}

# ---- DB Init ----
# Initialize the database connection when the service starts.
# This user-service startup hook is synchronous, unlike the async init in
# the test-management-service.
@app.on_event("startup")
def on_startup():
    init_db()

# ---- Run server ----
if __name__ == "__main__":
    port = int(getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
