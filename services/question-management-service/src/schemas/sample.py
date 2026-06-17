"""Response schema for the quiz-sampling endpoint (W3-F1, Part A).

Kept in its own module — deliberately importing *only* pydantic, no Beanie
model and none of the heavy ``QuestionCreate``/``QuestionUpdate`` validators in
``schemas/question.py`` — so the route's quiz-safe ``response_model`` is
unit-testable (and stays measurable under ``pytest --cov``) without dragging the
pre-existing untested validator module into the coverage denominator.
"""

from pydantic import BaseModel, ConfigDict, Field


class QuizSampleQuestion(BaseModel):
    """Quiz-safe projection of a sampled question.

    This is the *structural* answer-key guard for the ``GET
    /v1/api/questions/sample`` endpoint that backs the quiz-session backend
    (``POST /v1/api/test-sessions/``). Declaring it as the route's
    ``response_model`` means FastAPI drops any field outside this set on the way
    out — so even if a future change to ``map_question_to_sample`` accidentally
    let ``correct_answers``/``sample_answer`` through, the wire response still
    cannot leak the answer key. The omission is enforced by the type, not just
    by a hand-built dict.

    Fields are exactly ``_id``/``id``, ``question_text``, ``type``,
    ``difficulty``, ``options`` — never any correct-answer field.
    """

    # populate_by_name lets the route hand us the mapped dict (keyed by ``_id``);
    # FastAPI serializes the response back out by alias, so the wire shape stays
    # ``_id`` for the frontend.
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="MongoDB document ID", alias="_id")
    question_text: str | None = None
    type: str | None = None
    difficulty: str | None = None
    options: list[dict] | None = None
