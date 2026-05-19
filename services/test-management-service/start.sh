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

# Create database tables using init_db
echo "📦 Creating database tables..."
python -c "
import asyncio
from src.db.session import init_db

async def create_tables():
    await init_db()
    print('✅ Tables created successfully!')

asyncio.run(create_tables())
"

if [ $? -eq 0 ]; then
    echo "✅ Database tables ready!"
else
    echo "⚠️ Table creation failed, but continuing..."
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
