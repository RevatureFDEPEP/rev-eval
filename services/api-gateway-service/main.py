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
from src.middleware.auth import verify_workos_token, add_user_context_headers

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

# AWS Cloud Map configuration
# Services are discovered via DNS in the format: service-name.namespace
CLOUD_MAP_NAMESPACE = getenv("CLOUD_MAP_NAMESPACE", "evalai.local")

# Service name to port mapping (for Cloud Map DNS-based discovery)
SERVICE_PORTS = {
    "user-service": 8002,
    "test-management-service": 8001,
    "question-management-service": 8003,
    "notification-service": 8004,
    "ai-quiz-service": 8005,
    "ai-interview-service": 8009,
}

# ===== SERVICE ROUTING CONFIGURATION =====
# Map endpoint patterns to services
ROUTES = [
    {"pattern": r"^/v1/api/users(/.*)?$", "service": "user-service"},
    {"pattern": r"^/v1/api/dashboard(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/tests(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/submissions(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/skills(/.*)?$", "service": "test-management-service"},
    {"pattern": r"^/v1/api/questions(/.*)?$", "service": "question-management-service"},
    {"pattern": r"^/v1/api/test-sessions(/.*)?$", "service": "ai-quiz-service"},
    {"pattern": r"^/v1/api/notifications(/.*)?$", "service": "notification-service"},
    # AI Interview Service routes (HTTP endpoints)
    # Note: WebSocket endpoint ws://ai-interview-service:8009/ws/{session_id} should connect directly
    # Gateway doesn't currently support WebSocket proxying - use direct connection for interviews
    {"pattern": r"^/v1/api/interview(/.*)?$", "service": "ai-interview-service"},
]


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
    """
    Get service URL using AWS Cloud Map DNS-based service discovery.
    Services are accessible via DNS: service-name.namespace:port
    """
    port = SERVICE_PORTS.get(service_name)
    if not port:
        raise ValueError(f"Unknown service: {service_name}")

    # Use DNS name from Cloud Map
    dns_name = f"{service_name}.{CLOUD_MAP_NAMESPACE}"
    return f"http://{dns_name}:{port}"


async def sync_user_with_user_service(user_context: Dict[str, str]):
    """
    Sync user with user-service after JWT verification.

    This ensures the user exists in the centralized user database
    before routing requests to other services.
    """
    try:
        # Get user-service URL via Cloud Map DNS
        user_service_url = get_service_url("user-service")
        user_sync_url = f"{user_service_url}/v1/api/users/sync"

        # Prepare headers with user context
        headers = {
            "X-User-Id": user_context.get("user_id", ""),
            "X-User-Email": user_context.get("email", ""),
            "X-User-First-Name": user_context.get("first_name", ""),
            "X-User-Last-Name": user_context.get("last_name", ""),
            "X-User-Role": user_context.get("role", ""),
            "Content-Type": "application/json"
        }

        logger.info(f"🔄 Syncing user with user-service: {user_context.get('email')}")

        # Call user-service to sync user
        async with httpx.AsyncClient() as client:
            response = await client.post(
                user_sync_url,
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                logger.info(f"✅ User synced successfully")
            else:
                logger.warning(f"⚠️ User sync returned status {response.status_code}")

    except Exception as e:
        # Don't fail the request if user sync fails
        # Log the error and continue
        logger.error(f"❌ User sync failed: {str(e)}")
        logger.error("   Request will continue without user sync")

# ===== STARTUP/SHUTDOWN =====
@app.on_event("startup")
def on_startup():
    """Log startup information"""
    service_name = getenv('SERVICE_NAME', 'api-gateway')
    service_port = int(getenv('PORT', '8000'))
    logger.info(f"✅ {service_name} starting on port {service_port}")
    logger.info(f"🌐 Using Cloud Map namespace: {CLOUD_MAP_NAMESPACE}")
    logger.info(f"📍 Service discovery: DNS-based (AWS Cloud Map)")

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

# ===== SMART ROUTING (NO SERVICE NAME IN URL) =====
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def smart_gateway(
    path: str,
    request: Request,
    user_context: Dict[str, str] = Depends(verify_workos_token)
):
    """
    Smart routing based on endpoint pattern with JWT authentication.
    Example: GET /v1/api/tests -> routes to test-management-service

    Requires: Valid JWT token in Authorization header
    """
    logger.info("=" * 80)
    logger.info(f"🔍 Incoming: {request.method} /{path}")
    logger.info(f"👤 User: {user_context.get('email')} ({user_context.get('role')})")

    # Sync user with user-service (non-blocking, best-effort)
    # This ensures user exists in centralized user database
    await sync_user_with_user_service(user_context)

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
        # Get service URL via Cloud Map DNS
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

            # Determine timeout based on endpoint (AI endpoints need more time)
            # LLM question generation can take 30-60 seconds
            timeout = 120.0 if "part-a/questions" in path or "part-b/questions" in path else 30.0

            if timeout > 30:
                logger.info(f"⏱️  Using extended timeout: {timeout}s for AI endpoint")

            resp = await client.request(
                method,
                target_url,
                content=body if body else None,
                headers=headers,
                timeout=timeout
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

# ===== LEGACY ROUTE (WITH SERVICE NAME) =====
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
        # Get service URL via Cloud Map DNS
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