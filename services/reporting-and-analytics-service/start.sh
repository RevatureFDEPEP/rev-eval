#!/bin/bash

# Startup script for reporting-and-analytics-service.
#
# This service is a READ-ONLY consumer of test-management-service's data: it
# reads quiz_sessions / session_answers from the shared eval_ai_dev Postgres
# (see adr/0001-cross-service-data-access.md). It owns NO tables, so it
# runs NO Alembic migrations here — doing so would touch the `alembic_version`
# row that test-management-service owns in the same database. Its Alembic
# environment is scaffolded (with an isolated version_table) for the day this
# service gains tables of its own.

echo "🚀 Starting Reporting & Analytics Service..."

# Wait for the shared database to be reachable.
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

# No migrations: this service owns no tables (read-only). See note above.

echo "🚀 Starting FastAPI service..."
exec python main.py
