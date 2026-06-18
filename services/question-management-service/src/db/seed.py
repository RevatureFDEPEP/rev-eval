"""Guarded, idempotent question-bank startup seed (W5-F4).

On a fresh stack the Mongo ``questions`` collection is empty, so the
test-management-service ``POST /sessions`` flow (which ``$sample``s the bank)
fails with an empty-bank error until someone seeds by hand. This module lets
the service seed the demo fixtures itself on startup.

Behaviour:
  * Disabled when ``settings.SEED_QUESTION_BANK`` is false (opt-out for
    prod-like profiles).
  * Idempotent — seeds only when the bank is empty; a populated bank is left
    untouched, so ``docker compose up`` on an existing volume is a no-op and
    never inserts duplicates.
  * Reuses the shared fixture (``src.db.seed_data.QUESTIONS``) through the same
    create path as the API (``QuestionService.create_question``), so option_ids
    and validation match real inserts.
  * Robust — a fixture rejected by validation (e.g. the W5-F3-flagged
    ``true_false`` encoding defect) is logged and skipped, not fatal.

``init_db()`` (and thus Beanie) must have run before this is called.
"""

import logging

from src.config.settings import settings
from src.db.seed_data import QUESTIONS
from src.models.question import Option, Question
from src.repositories.question_repository import QuestionRepository
from src.schemas.question import QuestionCreate

logger = logging.getLogger(__name__)


def _to_question(fixture: dict) -> Question:
    """Validate a fixture via QuestionCreate and build a storable Question.

    Mirrors QuestionService.create_question's conversion (1-indexed option_ids
    auto-generated from position) without importing the service layer, so the
    seeder's dependency surface stays minimal.
    """
    data = QuestionCreate(**fixture).model_dump()
    if data.get("options"):
        data["options"] = [
            Option(option_id=idx, text=opt["text"])
            for idx, opt in enumerate(data["options"], start=1)
        ]
    return Question(**data)


async def seed_question_bank() -> int:
    """Seed demo questions if enabled and the bank is empty.

    Returns:
        int: the number of questions inserted (0 when disabled or skipped).
    """
    if not settings.SEED_QUESTION_BANK:
        logger.info("SEED_QUESTION_BANK is false; skipping question-bank seed")
        return 0

    existing = await Question.find_all().count()
    if existing > 0:
        logger.info(
            "Question bank already has %d question(s); skipping seed", existing
        )
        return 0

    logger.info("Question bank empty; seeding %d demo question(s)", len(QUESTIONS))

    inserted = 0
    skipped = 0
    for i, fixture in enumerate(QUESTIONS, start=1):
        try:
            await QuestionRepository.create(_to_question(fixture))
            inserted += 1
        except Exception as e:  # validation/HTTP/anything — never fatal
            skipped += 1
            preview = str(fixture.get("question_text", ""))[:60]
            logger.warning(
                "Skipped seed fixture %d (%s...): %s", i, preview, e
            )

    logger.info(
        "Question-bank seed complete: inserted=%d skipped=%d", inserted, skipped
    )
    return inserted
