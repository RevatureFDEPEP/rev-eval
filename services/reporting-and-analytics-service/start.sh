#!/bin/bash

# Startup script for reporting-and-analytics-service
# Waits for the reporting Postgres, applies Alembic migrations, starts the app.
#
# Schema is owned entirely by Alembic (alembic/versions/): 0001 is an empty
# baseline at the W2-M10 scaffold stage; reporting tables land in W4-F1.
# init_db() (app startup) is a connectivity check only — no create_all.

echo "🚀 Starting Reporting and Analytics Service..."

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
until python -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'reporting-postgres'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USERNAME', 'root'),
        password=os.getenv('DB_PASSWORD', 'root'),
        dbname=os.getenv('DB_NAME', 'eval_ai_reporting')
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

# Fail hard on migration errors: the container exits and compose restarts it.
# This is a fresh, private datastore, so no legacy `alembic stamp` adopt branch
# is needed (unlike test-management-service).
echo "📦 Applying database migrations..."
alembic upgrade head || exit 1
echo "✅ Database schema is up to date!"

# Start the FastAPI service
echo "🚀 Starting FastAPI service..."
exec python main.py
