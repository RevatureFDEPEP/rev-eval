"""Test bootstrap for question-management-service.

`src.config.settings.Settings()` runs at import and requires SERVICE_NAME.
A MONGO_URI is set so the global `settings.mongo_url` resolves; the Mongo
client is created lazily, so these tests never open a connection.
"""
import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/evalai")
