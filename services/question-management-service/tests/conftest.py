import os

os.environ.setdefault("SERVICE_NAME", "question-management-service")
os.environ.setdefault("PORT", "8003")
os.environ.setdefault("SERVICE_HOSTNAME", "localhost")

import pytest
import pytest_asyncio
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie

# mongomock 4.3 doesn't support the authorizedCollections kwarg that Beanie 2.x
# passes to list_collection_names. Patch it to silently drop unknown kwargs.
from mongomock.database import Database as _MockDatabase
_orig_lcn = _MockDatabase.list_collection_names
import inspect as _inspect
_lcn_params = set(_inspect.signature(_orig_lcn).parameters)
def _patched_lcn(self, **kwargs):
    filtered = {k: v for k, v in kwargs.items() if k in _lcn_params}
    return _orig_lcn(self, **filtered)
_MockDatabase.list_collection_names = _patched_lcn

from src.models.question import Question


@pytest_asyncio.fixture(scope="function")
async def question_db():
    client = AsyncMongoMockClient()
    db = client["testdb"]
    await init_beanie(database=db, document_models=[Question])
    yield db
    await Question.delete_all()
