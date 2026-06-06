#!/bin/bash

# Startup script for test-management-service
# Waits for Postgres, applies Alembic migrations, and starts the service.
#
# Schema and demo seed data are owned entirely by Alembic (alembic/versions/):
#   0001 baseline schema, 0002 categories, 0003 demo seed data.
# init_db() no longer runs create_all — migrations are the only schema path.

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

# Adopt-or-migrate: volumes created before Alembic already have the baseline
# tables (made by the old create_all path) but no alembic_version. Stamp the
# baseline revision so upgrade applies only what's newer, instead of failing
# on duplicate tables.
echo "📦 Applying database migrations..."
NEEDS_STAMP=$(python -c "
import psycopg2
import os
conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'postgres'),
    port=os.getenv('DB_PORT', '5432'),
    user=os.getenv('DB_USERNAME', 'root'),
    password=os.getenv('DB_PASSWORD', 'root'),
    dbname=os.getenv('DB_NAME', 'eval_ai_dev')
)
cur = conn.cursor()
def has_table(name):
    cur.execute(
        'SELECT 1 FROM information_schema.tables '
        'WHERE table_schema = current_schema() AND table_name = %s',
        (name,),
    )
    return cur.fetchone() is not None
print('yes' if (has_table('skills') and not has_table('alembic_version')) else 'no')
conn.close()
")

if [ "$NEEDS_STAMP" = "yes" ]; then
    echo "🏷️  Pre-Alembic schema detected — stamping baseline revision 0001..."
    alembic stamp 0001 || exit 1
fi

# Fail hard on migration errors: the container exits and compose restarts it
# (e.g. revision 0003 raises until user-service has seeded the demo users).
alembic upgrade head || exit 1
echo "✅ Database schema is up to date!"

# Start the FastAPI service
echo "🚀 Starting FastAPI service..."
exec python main.py
