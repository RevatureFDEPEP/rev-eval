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

# Apply database migrations (Alembic owns the schema).
echo "📦 Applying database migrations..."

# Adopt Alembic over a database created by the old create_all path: if the app
# tables already exist but Alembic has never recorded a version, stamp the
# baseline so only new migrations (e.g. quiz_sessions) are applied.
NEEDS_STAMP=$(python -c "
import os, psycopg2
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'postgres'),
    port=os.getenv('DB_PORT', '5432'),
    user=os.getenv('DB_USERNAME', 'root'),
    password=os.getenv('DB_PASSWORD', 'root'),
    dbname=os.getenv('DB_NAME', 'eval_ai_dev'))
cur = conn.cursor()
cur.execute(\"select to_regclass('public.alembic_version'), to_regclass('public.tests')\")
av, tests = cur.fetchone()
conn.close()
print('yes' if (av is None and tests is not None) else 'no')
")

if [ "$NEEDS_STAMP" = "yes" ]; then
    echo "🔖 Existing schema found; stamping Alembic baseline (0001)..."
    alembic stamp 0001
fi

alembic upgrade head

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
