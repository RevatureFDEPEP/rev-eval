from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn
import re
import logging
from os import getenv
from typing import Optional, Dict
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import JWT middleware
from src.middleware.auth import verify_jwt_token, add_user_context_headers

app = FastAPI(title="API Gateway")

# Configure CORS
origins = getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service name to port mapping (compose-internal DNS)
SERVICE_PORTS = {
    "user-service": 8002,
    "test-management-service": 8001,
    "question-management-service": 8003,
}

# ===== SERVICE ROUTING CONFIGURATION =====
# Map endpoint patterns to services
ROUTES = [
    {"pattern": r"^/v1/api/auth(/.*)?$", "service": "user-service"},
    {"pattern": r"^/v1/api/users(/.*)?$", "service": "user-service"},
    {"pattern": r"^/v1/api/dashboard(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/tests(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/submissions(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/skills(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/questions(/.*)?$", "service": "question-management-service"},
]

# Paths that bypass JWT verification (login, register). under what criteria do we bypass jwt??
#why is it designed this way 
PUBLIC_PATH_PREFIXES = (
    "/v1/api/auth/login",
    "/v1/api/auth/register",
)


# Compile patterns for performance
COMPILED_ROUTES = [
    {"pattern": re.compile(r["pattern"]), "service": r["service"]}
    for r in ROUTES
]

def find_service_for_path(path: str) -> Optional[str]:
    """Find service based on endpoint pattern"""
    full_path = f"/{path}" if not path.startswith("/") else path

    for route in COMPILED_ROUTES:
        if route["pattern"].match(full_path):
            return route["service"]

    return None


def get_service_url(service_name: str) -> str:
    """Get service URL via compose-internal DNS (service-name:port)."""
    port = SERVICE_PORTS.get(service_name)
    if not port:
        raise ValueError(f"Unknown service: {service_name}")
    return f"http://{service_name}:{port}"


# ===== STARTUP/SHUTDOWN =====
@app.on_event("startup")
def on_startup():
    """Log startup information"""
    service_name = getenv('SERVICE_NAME', 'api-gateway')
    service_port = int(getenv('PORT', '8000'))
    logger.info(f"✅ {service_name} starting on port {service_port}")
    logger.info(f"📍 Service discovery: compose-internal DNS")

@app.on_event("shutdown")
def on_shutdown():
    """Log shutdown"""
    service_name = getenv('SERVICE_NAME', 'api-gateway')
    logger.info(f"👋 {service_name} shutting down")

# ===== ROUTES =====
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/routes")
def list_routes():
    """List all configured routes"""
    return {
        "routes": [
            {"pattern": r["pattern"], "service": r["service"]}
            for r in ROUTES
        ]
    }

# ===== PUBLIC AUTH PASS-THROUGH (no JWT required) =====
# why do we have three types of routing instead of just one unified smart routing system with JWT verification
#do we need load balancing if we convert this to a single routing system?? 
@app.api_route(
    "/v1/api/auth/{auth_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def public_auth_proxy(auth_path: str, request: Request):
    """Forward /v1/api/auth/* to user-service without JWT verification.

    login + register need to issue tokens; other /auth/* paths (e.g. /me)
    still need a Bearer header and are forwarded as-is — user-service
    enforces its own auth there.
    """
    full_path = f"/v1/api/auth/{auth_path}"
    logger.info(f"🔓 Public auth proxy: {request.method} {full_path}")

    target_url = f"{get_service_url('user-service')}{full_path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    body = await request.body() if request.method not in ("GET", "HEAD") else None
    headers = dict(request.headers)
    for h in ("host", "content-length", "x-forwarded-proto", "x-forwarded-scheme"):
        headers.pop(h, None)

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.request(
            request.method, target_url, content=body, headers=headers, timeout=30.0,
        )

    if resp.headers.get("content-type", "").startswith("application/json"):
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )


# ===== SMART ROUTING (NO SERVICE NAME IN URL) =====
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def smart_gateway(
    path: str,
    request: Request,
    user_context: Dict[str, str] = Depends(verify_jwt_token)
):
    """
    Smart routing based on endpoint pattern with JWT authentication.
    Example: GET /v1/api/tests -> routes to test-management-service

    Requires: Valid JWT token in Authorization header
    """
    logger.info("=" * 80)
    logger.info(f"🔍 Incoming: {request.method} /{path}")
    logger.info(f"👤 User: {user_context.get('email')} ({user_context.get('role')})")

    # Find service based on path
    service_name = find_service_for_path(path)

    if not service_name:
        logger.error(f"❌ No service found for path: /{path}")
        raise HTTPException(
            status_code=404,
            detail=f"No service configured for path: /{path}"
        )

    logger.info(f"📍 Matched service: {service_name}")

    try:
        service_base_url = get_service_url(service_name)
        target_url = f"{service_base_url}/{path}"

        # Preserve query parameters
        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        logger.info(f"📤 Forwarding: {request.method} -> {target_url}")

        # Forward the request
        async with httpx.AsyncClient(follow_redirects=True) as client:
            method = request.method
            body = await request.body()
            headers = dict(request.headers)

            # Remove problematic headers
            headers.pop('host', None)
            headers.pop('content-length', None)
            headers.pop('x-forwarded-proto', None)
            headers.pop('x-forwarded-scheme', None)

            # Add user context headers for downstream services
            headers = add_user_context_headers(headers, user_context)

            resp = await client.request(
                method,
                target_url,
                content=body if body else None,
                headers=headers,
                timeout=30.0
            )

        logger.info(f"✅ Response: {resp.status_code}")
        
        # Log errors
        if resp.status_code >= 400:
            logger.error(f"❌ Error Response:")
            try:
                logger.error(f"   {resp.json()}")
            except:
                logger.error(f"   {resp.text[:200]}")
        
        logger.info("=" * 80)
        
        # Return response with correct status code
        if resp.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse(
                content=resp.json(),
                status_code=resp.status_code
            )
        else:
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type")
            )
            
    except HTTPException:
        raise
    except httpx.ConnectError as e:
        logger.error(f"❌ Connection Error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to service '{service_name}': {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Gateway error: {str(e)}"
        )

# ===== LEGACY ROUTE (WITH SERVICE NAME) ===== // why this is in place?? which scenario requires legacy routing??
@app.api_route("/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def legacy_gateway(service_name: str, path: str, request: Request):
    """
    Legacy routing with service name in URL.
    Example: GET /test-management-service/v1/api/tests
    """
    logger.info("=" * 80)
    logger.info(f"🔍 Legacy route: {request.method} /{service_name}/{path}")
    logger.info("=" * 80)

    try:
        service_base_url = get_service_url(service_name)
        target_url = f"{service_base_url}/{path}"

        if request.url.query:
            target_url = f"{target_url}?{request.url.query}"

        logger.info(f"📤 Forwarding: {request.method} -> {target_url}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            method = request.method
            body = await request.body()
            headers = dict(request.headers)
            
            headers.pop('host', None)
            headers.pop('content-length', None)
            headers.pop('x-forwarded-proto', None)
            headers.pop('x-forwarded-scheme', None)
            
            resp = await client.request(
                method, 
                target_url, 
                content=body if body else None,
                headers=headers,
                timeout=30.0
            )

        print(f"✅ Response: {resp.status_code}")
        print("=" * 80)
        
        if resp.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        else:
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type")
            )
            
    except HTTPException:
        raise
    except httpx.ConnectError as e:
        print(f"❌ Connection Error: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to service: {str(e)}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gateway error: {str(e)}")

if __name__ == "__main__":
    port = int(getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)