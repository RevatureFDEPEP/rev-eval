import consul
import threading
import time
import asyncio
from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from src.v1.routes.notification_route import router as notification_router
from src.db.session import init_db
from src.config.settings import settings
from src.utils.sqs_consumer import sqs_consumer
from src.services.event_handlers import EVENT_HANDLERS

load_dotenv()

app = FastAPI(title="Notification Service", version="1.0.0")

# Global variables
consul_client = None
heartbeat_running = False
sqs_polling_task = None

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
app.include_router(notification_router)

# ---- Health Endpoint ----
@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "notification-service"}


# ---- DB Init + Consul + SQS ----
@app.on_event("startup")
async def on_startup():
    global sqs_polling_task

    # Initialize database
    init_db()

    # Register with Consul
    register_with_consul()

    # Register SQS event handlers
    print("📝 Registering SQS event handlers...")
    for event_type, handler in EVENT_HANDLERS.items():
        sqs_consumer.register_handler(event_type, handler)
    print(f"✅ Registered {len(EVENT_HANDLERS)} event handler(s)")

    # Start SQS polling in background task
    if settings.SQS_ENABLED:
        print("🚀 Starting SQS polling task...")
        sqs_polling_task = asyncio.create_task(sqs_consumer.start_polling())
        print("✅ SQS polling task started")
    else:
        print("⚠️  SQS polling disabled (SQS_ENABLED=False)")


@app.on_event("shutdown")
async def on_shutdown():
    """Deregister from Consul and stop SQS polling on shutdown"""
    global consul_client, sqs_polling_task

    # Stop SQS polling
    if sqs_polling_task:
        print("🛑 Stopping SQS polling...")
        sqs_consumer.stop_polling()
        sqs_polling_task.cancel()
        try:
            await sqs_polling_task
        except asyncio.CancelledError:
            print("✅ SQS polling task stopped")

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
        # For Docker, use service hostname; for local, use 127.0.0.1
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
    port = int(getenv("PORT", 8004))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
