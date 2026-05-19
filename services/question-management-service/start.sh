#!/bin/bash
set -euo pipefail

echo "🚀 Starting Question Management Service..."

echo "⏳ Waiting for MongoDB..."
until python -c "
import pymongo
from src.config.settings import settings

try:
    client = pymongo.MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    client.close()
    print('MongoDB is ready!')
except Exception as e:
    print(f'MongoDB not ready: {e}')
    exit(1)
"; do
    echo "MongoDB not ready, retrying in 2s..."
    sleep 2
done

echo "✅ MongoDB ready."

echo "📦 Initializing database..."
python -c "
import asyncio
from src.db.session import init_db

async def initialize():
    try:
        await init_db()
        print('✅ MongoDB initialized successfully!')
    except Exception as e:
        print(f'⚠️ MongoDB initialization warning: {e}')

asyncio.run(initialize())
"

echo "🚀 Starting FastAPI service..."
exec python main.py
