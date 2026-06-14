from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import ValidationError
from src.schemas.question import (
    QuestionCreate,
    QuestionPublic,
    QuestionResponse,
    QuestionUpdate,
)
from src.services.question_service import QuestionService
from src.utils.dependencies import require_question_editor

router = APIRouter(prefix="/questions", tags=["Questions"])

# Roles allowed to see answer keys. The gateway injects the verified caller
# role as X-User-Role; everyone else (participants, anonymous) gets the safe
# QuestionPublic view with correct_answers/sample_answer/answer_explanation
# stripped. Trusted server-to-server callers (e.g. the quiz session service
# building its snapshot) identify as ADMIN.
_PRIVILEGED_ROLES = {"TRAINER", "ADMIN"}


def _is_privileged(role: Optional[str]) -> bool:
    return (role or "").strip().upper() in _PRIVILEGED_ROLES


def _serialize(question, privileged: bool) -> dict:
    """Serialize a Question document to a role-appropriate dict.

    Privileged callers get the full payload; everyone else gets the safe view,
    which omits the answer-key fields entirely (not merely nulls them).
    """
    data = question.model_dump(by_alias=True, mode="json")
    schema = QuestionResponse if privileged else QuestionPublic
    return schema(**data).model_dump(by_alias=True, mode="json")


def _serialize_many(questions, privileged: bool) -> list:
    return [_serialize(q, privileged) for q in questions]


@router.post(
    "/",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new question",
    description="""
    Create a new question with type-specific validation.

    **Question Types:**
    - **mcq**: Single correct answer from multiple options
    - **multi**: Multiple correct answers from options
    - **true_false**: Boolean true/false question
    - **text**: Open-ended text question with sample answer

    **Validation Rules:**
    - MCQ: Requires 2+ options and exactly one correct answer (int)
    - MULTI: Requires 2+ options and at least one correct answer (list of ints)
    - TRUE_FALSE: Requires boolean correct_answer, no options
    - TEXT: Requires sample_answer, no options or correct_answers
    """
)
async def create_question(
    question: QuestionCreate,
    _role: str = Depends(require_question_editor),
):
    """Create a new question with comprehensive validation. Trainer/admin only."""
    try:
        question_id = await QuestionService.create_question(question)
        return {
            "message": "Question created successfully",
            "id": question_id
        }
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the question: {str(e)}"
        )


@router.get(
    "/",
    response_model=None,
    summary="Get all questions",
    description=(
        "Retrieve all questions. Answer keys are included only for "
        "trainer/admin callers; participants receive the safe view."
    ),
)
async def get_all_questions(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """Retrieve all questions (answer keys stripped for non-privileged roles)."""
    try:
        questions = await QuestionService.get_all_questions()
        return _serialize_many(questions, _is_privileged(x_user_role))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching questions: {str(e)}"
        )


@router.get(
    "/{id}",
    response_model=None,
    summary="Get question by ID",
    description=(
        "Retrieve a specific question by its MongoDB _id. Answer keys are "
        "included only for trainer/admin callers."
    ),
)
async def get_question_by_id(
    id: str,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """Retrieve a specific question by ID (answer keys role-gated)."""
    try:
        question = await QuestionService.get_question_by_id(id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{id}' not found"
            )
        return _serialize(question, _is_privileged(x_user_role))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the question: {str(e)}"
        )


@router.put(
    "/{id}",
    response_model=dict,
    summary="Update question",
    description="""
    Update an existing question with type-aware validation.

    **Important:**
    - Question type cannot be changed after creation
    - All updates must be compatible with the question's existing type
    - Only provide fields you want to update (partial updates supported)
    """
)
async def update_question(
    id: str,
    question_update: QuestionUpdate,
    _role: str = Depends(require_question_editor),
):
    """Update an existing question with validation. Trainer/admin only."""
    try:
        updated = await QuestionService.update_question(id, question_update)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{id}' not found"
            )
        return {
            "message": "Question updated successfully",
            "id": id
        }
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the question: {str(e)}"
        )


@router.delete(
    "/{id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Delete question",
    description="Delete a question by its MongoDB _id."
)
async def delete_question(
    id: str,
    _role: str = Depends(require_question_editor),
):
    """Delete a question by ID. Trainer/admin only."""
    try:
        deleted = await QuestionService.delete_question(id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{id}' not found"
            )
        return {
            "message": "Question deleted successfully",
            "id": id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the question: {str(e)}"
        )


# ============================================================================
# FILTER ENDPOINTS
# ============================================================================


@router.get(
    "/by-type/{question_type}",
    response_model=None,
    summary="Get questions by type",
    description="""
    Retrieve questions filtered by type.

    **Valid question types:**
    - `mcq` - Multiple choice with single correct answer
    - `multi` - Multiple choice with multiple correct answers
    - `true_false` - True/False questions
    - `text` - Open-ended text questions
    """
)
async def get_questions_by_type(
    question_type: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """Get questions filtered by type."""
    try:
        questions = await QuestionService.find_by_type(question_type, limit)
        return _serialize_many(questions, _is_privileged(x_user_role))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.get(
    "/by-skill/{skill}",
    response_model=None,
    summary="Get questions by skill",
    description="Retrieve questions that include the specified skill."
)
async def get_questions_by_skill(
    skill: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """Get questions filtered by skill."""
    try:
        questions = await QuestionService.find_by_skill(skill, limit)
        return _serialize_many(questions, _is_privileged(x_user_role))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.get(
    "/by-difficulty/{difficulty}",
    response_model=None,
    summary="Get questions by difficulty",
    description="""
    Retrieve questions filtered by difficulty level.

    **Valid difficulty levels:**
    - `easy` - Easy questions
    - `medium` - Medium difficulty questions
    - `hard` - Hard questions
    """
)
async def get_questions_by_difficulty(
    difficulty: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """Get questions filtered by difficulty."""
    try:
        questions = await QuestionService.find_by_difficulty(difficulty, limit)
        return _serialize_many(questions, _is_privileged(x_user_role))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.get(
    "/by-tags",
    response_model=None,
    summary="Get questions by tags",
    description="""
    Retrieve questions that have any of the specified tags.

    **Usage:**
    - Provide tags as comma-separated query parameters
    - Example: `/by-tags?tags=python&tags=beginner&tags=loops`
    - Returns questions that have ANY of the specified tags
    """
)
async def get_questions_by_tags(
    tags: List[str] = Query(..., description="List of tags to filter by"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """Get questions filtered by tags."""
    try:
        questions = await QuestionService.find_by_tags(tags, limit)
        return _serialize_many(questions, _is_privileged(x_user_role))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.get(
    "/filter",
    response_model=None,
    summary="Filter questions by multiple criteria",
    description="""
    Advanced filtering endpoint that supports multiple criteria simultaneously.

    **All filters are optional, but at least one must be provided:**
    - `type` - Question type (mcq, multi, true_false, text)
    - `skill` - Skill name (exact match, case-sensitive)
    - `difficulty` - Difficulty level (easy, medium, hard)
    - `tags` - List of tags (returns questions with ANY of these tags)
    - `limit` - Maximum number of results (1-500, default: 100)

    **Examples:**
    - `/filter?type=mcq&difficulty=hard` - All hard MCQ questions
    - `/filter?skill=Python&difficulty=easy` - Easy Python questions
    - `/filter?tags=loops&tags=arrays&type=mcq` - MCQ questions about loops or arrays
    """
)
async def filter_questions(
    type: Optional[str] = Query(None, description="Question type filter"),
    skill: Optional[str] = Query(None, description="Skill filter"),
    difficulty: Optional[str] = Query(None, description="Difficulty filter"),
    tags: Optional[List[str]] = Query(None, description="Tags filter (OR condition)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
):
    """
    Filter questions using multiple criteria with AND conditions.

    All specified filters must match (AND logic), but tags use OR logic
    (any of the specified tags).
    """
    try:
        questions = await QuestionService.filter_questions(
            question_type=type,
            skill=skill,
            difficulty=difficulty,
            tags=tags,
            limit=limit
        )
        return _serialize_many(questions, _is_privileged(x_user_role))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
