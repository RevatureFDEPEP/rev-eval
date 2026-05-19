#!/bin/bash

# Startup script for question-management-service
# Waits for MongoDB Atlas and starts the service

echo "🚀 Starting Question Management Service..."

# Wait for MongoDB Atlas to be ready
echo "⏳ Waiting for MongoDB Atlas to be ready..."
until python -c "
import pymongo
import os
from urllib.parse import quote_plus

try:
    # Get MongoDB Atlas credentials
    mongo_user = os.getenv('MONGO_USER')
    mongo_password = os.getenv('MONGODB_PASSWORD')
    mongo_cluster = os.getenv('MONGO_CLUSTER')
    mongo_appname = os.getenv('MONGO_APPNAME')

    if not all([mongo_user, mongo_password, mongo_cluster, mongo_appname]):
        raise Exception('Missing required MongoDB Atlas environment variables: MONGO_USER, MONGODB_PASSWORD, MONGO_CLUSTER, MONGO_APPNAME')

    # URL encode credentials
    username = quote_plus(mongo_user)
    password = quote_plus(mongo_password)

    # MongoDB Atlas connection string
    connection_string = (
        f'mongodb+srv://{username}:{password}'
        f'@{mongo_cluster}/?appName={mongo_appname}'
        f'&retryWrites=true&w=majority&authSource=admin'
    )

    # Try to connect
    client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    client.close()
    print('MongoDB Atlas is ready!')
except Exception as e:
    print(f'MongoDB Atlas not ready: {e}')
    exit(1)
"; do
    echo "MongoDB Atlas not ready, waiting 2 seconds..."
    sleep 2
done

echo "✅ MongoDB Atlas is ready!"

# Initialize database and collections
echo "📦 Initializing MongoDB database and collections..."
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

if [ $? -eq 0 ]; then
    echo "✅ Database initialization complete!"
else
    echo "⚠️ Database initialization had warnings, but continuing..."
fi

# Start the FastAPI service
echo "🚀 Starting FastAPI service..."
exec python main.py
