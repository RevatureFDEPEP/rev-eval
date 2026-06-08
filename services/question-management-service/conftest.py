"""Test bootstrap for question-management-service.

`src.config.settings.Settings()` runs at import and requires SERVICE_NAME.
A MONGO_URI is set so the global `settings.mongo_url` resolves; the Mongo
client is created lazily, so these tests never open a connection.
"""
import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/evalai")

import pytest_asyncio  # noqa: E402


@pytest_asyncio.fixture
async def beanie_db():
    """Initialise Beanie over an in-memory Mongo mock.

    Uses ``mongomock_motor.AsyncMongoMockClient`` (a Motor-compatible mock) so
    the Question document and ``QuestionRepository`` exercise real Beanie query
    paths without a running MongoDB. A fresh client per test keeps collections
    isolated. Yields the client; tests use Beanie / the repository directly.
    """
    from beanie import init_beanie
    from mongomock_motor import AsyncMongoMockClient
    from src.models.question import Question

    client = AsyncMongoMockClient()
    await init_beanie(database=client.test_db, document_models=[Question])
    yield client
