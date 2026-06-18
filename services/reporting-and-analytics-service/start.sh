#!/bin/bash

# Startup script for reporting-and-analytics-service.
#
# Waits for BOTH databases, applies this service's (empty) Alembic chain to its
# own private datastore, then starts the API.
#   - Own DB (DB_*): reporting's private store — only holds alembic_version.
#     Schema owned by Alembic; 0001 is an empty baseline (ADR 0001).
#   - TMS DB (TMS_DB_*): test-management's eval_ai_dev — READ-ONLY source for
#     report queries. We only wait for it; we never migrate it.
# init_db() (app startup) is a connectivity check for both — no create_all.

set -e

wait_for_db() {
    local host="$1" port="$2" user="$3" pw="$4" db="$5" label="$6"
    echo "⏳ Waiting for $label database ($host:$port/$db)..."
    until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(host='$host', port='$port', user='$user', password='$pw', dbname='$db').close()
except Exception as e:
    print(f'not ready: {e}'); sys.exit(1)
"; do
        echo "$label not ready, waiting 2 seconds..."
        sleep 2
    done
    echo "✅ $label database is ready!"
}

echo "🚀 Starting Reporting and Analytics Service..."

wait_for_db "${DB_HOST:-reporting-postgres}" "${DB_PORT:-5432}" \
    "${DB_USERNAME:-root}" "${DB_PASSWORD:-root}" "${DB_NAME:-eval_ai_reporting}" "own"

wait_for_db "${TMS_DB_HOST:-postgres}" "${TMS_DB_PORT:-5432}" \
    "${TMS_DB_USERNAME:-root}" "${TMS_DB_PASSWORD:-root}" "${TMS_DB_NAME:-eval_ai_dev}" "TMS (read-only)"

# Fresh private datastore — fail hard on migration error (compose restarts).
# No legacy `alembic stamp` adopt branch needed (unlike test-management).
echo "📦 Applying database migrations..."
alembic upgrade head
echo "✅ Database schema is up to date!"

echo "🚀 Starting FastAPI service..."
exec python main.py
