#!/bin/bash

# Startup script for reporting-and-analytics-service
# Waits for the database, creates tables, and starts the service.

echo "🚀 Starting Reporting and Analytics Service..."

echo "⏳ Waiting for database to be ready..."
until python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USERNAME', 'root'),
        password=os.getenv('DB_PASSWORD', 'root'),
        dbname=os.getenv('DB_NAME', 'eval_ai_dev')
    )
    conn.close()
    print('Database is ready!')
except Exception as e:
    print(f'Database not ready: {e}')
    exit(1)
"; do
    echo "Database not ready, waiting 2 seconds..."
    sleep 2
done

echo "✅ Database is ready!"

# Alembic migrations are the source of truth for the schema (see ADR 0001).
# Fall back to metadata create_all only if the migration step fails, so a fresh
# environment still comes up.
echo "📦 Applying database migrations (alembic upgrade head)..."
if alembic upgrade head; then
    echo "✅ Migrations applied!"
else
    echo "⚠️ alembic upgrade failed — falling back to create_all..."
    python -c "
import asyncio
from src.db.session import init_db

async def create_tables():
    await init_db()
    print('✅ Tables created via create_all fallback!')

asyncio.run(create_tables())
"
fi

echo "🚀 Starting FastAPI service..."
exec python main.py
