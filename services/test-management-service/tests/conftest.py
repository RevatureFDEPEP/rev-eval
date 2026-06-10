"""Shared test fixtures / setup.

Import every model so SQLAlchemy can resolve relationship strings (e.g.
Test.submissions -> TestSubmission) when a test constructs a mapped object.
Mirrors the "import all models" pattern in src/db/session.py init_db().
"""
from src.models.answer import Answer  # noqa: F401
from src.models.category import Category  # noqa: F401
from src.models.idempotency_key import IdempotencyKey  # noqa: F401
from src.models.session import Session  # noqa: F401
from src.models.skill import Skill  # noqa: F401
from src.models.test import Test  # noqa: F401
from src.models.test_skill import TestSkill  # noqa: F401
from src.models.test_submission import TestSubmission  # noqa: F401
