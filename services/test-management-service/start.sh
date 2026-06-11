#!/bin/bash

# Startup script for test-management-service
# Creates tables, seeds data, and starts the service

echo "🚀 Starting Test Management Service..."

# Wait for database to be ready
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

# Apply schema via Alembic migrations (single source of truth — no create_all).
# Adopt an existing create_all schema if one predates Alembic on this DB:
#   - alembic_version present  -> normal `upgrade head`
#   - no alembic_version but tables already exist -> `stamp head` (don't re-CREATE)
#   - empty DB -> `upgrade head` creates everything
echo "📦 Applying database migrations (alembic)..."
NEEDS_STAMP=$(python -c "
import os
import psycopg2
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'postgres'),
    port=os.getenv('DB_PORT', '5432'),
    user=os.getenv('DB_USERNAME', 'root'),
    password=os.getenv('DB_PASSWORD', 'root'),
    dbname=os.getenv('DB_NAME', 'eval_ai_dev'),
)
cur = conn.cursor()
cur.execute(\"SELECT to_regclass('public.alembic_version'), to_regclass('public.tests')\")
alembic_version, tests = cur.fetchone()
conn.close()
# Stamp only when legacy schema exists but Alembic was never initialised here.
print('1' if (alembic_version is None and tests is not None) else '0')
")

if [ "$NEEDS_STAMP" = "1" ]; then
    echo "ℹ️ Existing schema detected without alembic_version — stamping head."
    alembic stamp head
else
    alembic upgrade head
fi

if [ $? -eq 0 ]; then
    echo "✅ Database migrations applied!"
else
    echo "⚠️ Migration step failed, but continuing..."
fi

# Seed the database with mock data
echo "🌱 Seeding database with mock data..."
python seed_db.py

if [ $? -eq 0 ]; then
    echo "✅ Database seeded successfully!"
else
    echo "⚠️ Database seeding failed, but continuing..."
fi

# Start the FastAPI service
echo "🚀 Starting FastAPI service..."
exec python main.py
