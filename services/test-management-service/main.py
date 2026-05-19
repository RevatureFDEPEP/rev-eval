import consul
import threading
import time
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

# Global variables
consul_client = None
heartbeat_running = False

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

# ---- DB Init + Consul ----
@app.on_event("startup")
async def on_startup():
    await init_db()
    register_with_consul()

@app.on_event("shutdown")
def on_shutdown():
    """Deregister from Consul on shutdown"""
    global consul_client
    if consul_client:
        try:
            service_port = int(settings.PORT) if isinstance(settings.PORT, str) else settings.PORT
            service_id = f"{settings.SERVICE_NAME}-{service_port}"
            consul_client.agent.service.deregister(service_id)
            print(f"✅ Deregistered {service_id} from Consul")
        except Exception as e:
            print(f"⚠️ Deregistration failed: {e}")

def register_with_consul():
    global consul_client, heartbeat_running
    
    try:
        # For Codespaces, use 127.0.0.1
        hostname = getenv("SERVICE_HOSTNAME", "127.0.0.1")
        
        # Convert ports to int
        consul_port = int(settings.CONSUL_PORT) if isinstance(settings.CONSUL_PORT, str) else settings.CONSUL_PORT
        service_port = int(settings.PORT) if isinstance(settings.PORT, str) else settings.PORT
        
        print(f"🔍 Connecting to Consul at {settings.CONSUL_HOST}:{consul_port}")
        
        # Create global Consul client
        consul_client = consul.Consul(
            host=settings.CONSUL_HOST, 
            port=consul_port
        )
        
        service_id = f"{settings.SERVICE_NAME}-{service_port}"

        # Deregister old instance if exists
        try:
            consul_client.agent.service.deregister(service_id)
            print(f"🔄 Deregistered old instance: {service_id}")
        except Exception as dereg_error:
            print(f"ℹ️ No old instance to deregister: {dereg_error}")

        # Register service
        consul_client.agent.service.register(
            name=settings.SERVICE_NAME,
            service_id=service_id,
            address=hostname,
            port=service_port,
            check={
                "ttl": "15s",
                "deregister_critical_service_after": "1m"
            }
        )
        
        print(f"✅ Registered {settings.SERVICE_NAME} at {hostname}:{service_port}")
        print(f"   Service ID: {service_id}")
        
        # Start heartbeat thread only once
        if not heartbeat_running:
            def send_heartbeat():
                global heartbeat_running, consul_client
                heartbeat_running = True
                consecutive_failures = 0
                
                while True:
                    try:
                        consul_client.agent.check.ttl_pass(f"service:{service_id}")
                        print(f"💓 Heartbeat sent to Consul")
                        consecutive_failures = 0
                    except Exception as e:
                        consecutive_failures += 1
                        print(f"⚠️ Heartbeat failed ({consecutive_failures}x): {e}")
                        
                        # Try to reconnect after 3 failures
                        if consecutive_failures >= 3:
                            print("🔄 Attempting to reconnect to Consul...")
                            try:
                                consul_client = consul.Consul(
                                    host=settings.CONSUL_HOST,
                                    port=consul_port
                                )
                                consecutive_failures = 0
                            except Exception as reconnect_error:
                                print(f"❌ Reconnection failed: {reconnect_error}")
                    
                    time.sleep(10)
            
            threading.Thread(target=send_heartbeat, daemon=True).start()
            print("🚀 Heartbeat thread started")
        
    except Exception as e:
        print(f"⚠️ Consul registration failed: {e}")
        import traceback
        traceback.print_exc()

# ---- Run server ----
if __name__ == "__main__":
    port = int(getenv("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)