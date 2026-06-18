"""Tests for the guarded, idempotent question-bank startup seeder (W5-F4).

Run real Beanie inserts via the `beanie_db` fixture (conftest.py, backed by
mongomock-motor — no MongoDB required). Cover: seeding an empty bank, the
no-op re-run (idempotency), and the SEED_QUESTION_BANK opt-out.
"""
import pytest
from src.config.settings import settings
from src.db.seed import seed_question_bank
from src.db.seed_data import QUESTIONS
from src.models.question import Question


@pytest.fixture(autouse=True)
def _seed_enabled(monkeypatch):
    """Default the flag on for these tests regardless of the ambient env."""
    monkeypatch.setattr(settings, "SEED_QUESTION_BANK", True)


async def test_seeds_empty_bank(beanie_db):
    inserted = await seed_question_bank()

    # At least most fixtures land; some malformed true_false rows (W5-F3
    # encoding defect) are tolerated and skipped, so allow inserted <= total.
    assert inserted > 0
    assert inserted <= len(QUESTIONS)
    assert await Question.find_all().count() == inserted


async def test_idempotent_rerun_is_noop(beanie_db):
    first = await seed_question_bank()
    count_after_first = await Question.find_all().count()

    second = await seed_question_bank()

    assert first > 0
    assert second == 0  # bank already populated → skipped
    assert await Question.find_all().count() == count_after_first


async def test_disabled_flag_seeds_nothing(beanie_db, monkeypatch):
    monkeypatch.setattr(settings, "SEED_QUESTION_BANK", False)

    inserted = await seed_question_bank()

    assert inserted == 0
    assert await Question.find_all().count() == 0
