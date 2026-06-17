"""Pure helpers for the quiz-sampling endpoint (W3-F1, Part A).

These functions contain *no* I/O — no Mongo, no network, no clock — so they are
unit-testable with plain `pytest` (no live MongoDB, no async runner) and stay
inside the coverage gate without importing the route module or the Beanie model.

The route layer (``src/v1/routes/question_routes.py``) calls
``build_sample_pipeline`` to construct the ``$sample`` aggregation, hands it to
the repository, then maps each raw document through ``map_question_to_sample``
before returning it.  Correct answers (``correct_answers`` / ``sample_answer``)
are deliberately *never* copied into the projection — a quiz-taker must not be
able to read the answer key off the wire.
"""

from typing import Any

# Hard ceiling so a caller cannot request an unbounded $sample (DoS guard).
MAX_SAMPLE_SIZE = 200
DEFAULT_SAMPLE_SIZE = 20


def normalize_sample_size(n: int | None) -> int:
    """Clamp the requested sample size into ``[1, MAX_SAMPLE_SIZE]``.

    ``None`` (param omitted) falls back to ``DEFAULT_SAMPLE_SIZE``.  A value
    below 1 is raised to 1; a value above the ceiling is capped.
    """
    if n is None:
        return DEFAULT_SAMPLE_SIZE
    if n < 1:
        return 1
    if n > MAX_SAMPLE_SIZE:
        return MAX_SAMPLE_SIZE
    return n


def parse_skills(skills: str | None) -> list[str]:
    """Parse an optional comma-separated ``skills`` query string into a list.

    Whitespace is trimmed and empty fragments dropped, so ``"python, , sql,"``
    yields ``["python", "sql"]``.  ``None``/empty yields ``[]`` (no filter).
    """
    if not skills:
        return []
    return [s.strip() for s in skills.split(",") if s.strip()]


def build_sample_pipeline(n: int | None, skills: str | None) -> list[dict[str, Any]]:
    """Build the MongoDB aggregation pipeline for random question sampling.

    Pure: returns a plain list of stage dicts so it can be asserted in a unit
    test without touching Mongo.  When ``skills`` are supplied a ``$match`` on
    the ``skills`` array (``$in``) precedes the ``$sample`` stage so the random
    draw is taken from the filtered pool.
    """
    size = normalize_sample_size(n)
    skill_list = parse_skills(skills)

    pipeline: list[dict[str, Any]] = []
    if skill_list:
        pipeline.append({"$match": {"skills": {"$in": skill_list}}})
    pipeline.append({"$sample": {"size": size}})
    return pipeline


def map_question_to_sample(doc: dict[str, Any]) -> dict[str, Any]:
    """Project a raw question document into the quiz-safe sample shape.

    Returns exactly: ``_id`` (str), ``question_text``, ``type``, ``difficulty``,
    ``options``.  Correct answers are *never* included.  ``options`` is
    normalized to a list of ``{option_id, text}`` dicts (or ``None`` for
    answer-less types such as ``true_false`` / ``text``).
    """
    return {
        "_id": str(doc.get("_id")),
        "question_text": doc.get("question_text"),
        "type": doc.get("type"),
        "difficulty": doc.get("difficulty"),
        "options": _safe_options(doc.get("options")),
    }


def _safe_options(options: Any) -> list[dict[str, Any]] | None:
    """Normalize stored options to a list of plain dicts, or None.

    Accepts either dicts or option-like objects (``option_id``/``text``
    attributes) and strips anything else, so no answer-bearing field can leak
    through an unexpected option shape.
    """
    if not options:
        return None
    normalized: list[dict[str, Any]] = []
    for opt in options:
        if isinstance(opt, dict):
            normalized.append(
                {"option_id": opt.get("option_id"), "text": opt.get("text")}
            )
        else:
            normalized.append(
                {
                    "option_id": getattr(opt, "option_id", None),
                    "text": getattr(opt, "text", None),
                }
            )
    return normalized
