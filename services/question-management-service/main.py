import uvicorn
import consul
import threading
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from os import getenv
from src.config.settings import settings
from src.db.session import init_db, close_db
from src.v1.routes.question_routes import router as question_router

app = FastAPI(
    title="Question Management Service",
    version="1.0.0",
    description="Microservice for managing questions with MongoDB storage",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global variables
consul_client = None
heartbeat_running = False

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routes
app.include_router(question_router, prefix="/v1/api")

# ---- Health Endpoint ----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    register_with_consul()
    await init_db()

@app.on_event("shutdown")
async def on_shutdown():
    """Gracefully shutdown: close MongoDB connection and deregister from Consul"""
    global consul_client

    # Close MongoDB connection
    try:
        await close_db()
    except Exception as e:
        print(f"⚠️ MongoDB connection close failed: {e}")

    # Deregister from Consul
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
        
        # Convert to int
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
        except Exception:
            pass  # Old instance may not exist

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
                        
                        # Reconnect after 3 failures
                        if consecutive_failures >= 3:
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
    port = int(settings.PORT) if isinstance(settings.PORT, str) else settings.PORT
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)