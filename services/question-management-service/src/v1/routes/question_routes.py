import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from src.schemas.question import (
    PresignedUploadResponse,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)
from src.services.question_service import QuestionService
from src.services.upload_service import (
    InvalidContentTypeError,
    InvalidFilenameError,
    create_presigned_upload,
)
from src.utils.auth import get_current_trainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get(
    "/presigned-upload-url",
    response_model=PresignedUploadResponse,
    summary="Get a presigned upload URL for a question image",
    description="""
    Issue a short-lived presigned POST policy the client uses to upload a
    question image directly to MinIO/S3 (no bytes flow through this service).

    **Auth:** trainer-only. The caller's role is read from the gateway-injected
    `X-User-Role` header (this service does not re-verify the JWT — see the
    header-trust caveat in `src/utils/auth.py`).

    **Content types:** only `image/png` and `image/jpeg` are allowed.

    **Size cap:** the policy binds a `content-length-range` condition so the
    object store rejects any upload over `max_bytes` (5 MiB) server-side.

    The client POSTs multipart form-data to `url`: every entry in `fields`
    first, then the `file` part. Returns `url`, `fields`, the object `key` to
    reference after upload, the policy `expires_in` TTL (seconds), and
    `max_bytes`. Does not touch the database.
    """,
)
async def get_presigned_upload_url(
    filename: str = Query(..., min_length=1, description="Original filename"),
    content_type: str = Query(..., description="MIME type (image/png|image/jpeg)"),
    _trainer: dict = Depends(get_current_trainer),
):
    """Generate a trainer-only presigned POST policy for a question image."""
    try:
        return create_presigned_upload(filename=filename, content_type=content_type)
    except InvalidContentTypeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except InvalidFilenameError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except Exception as e:
        # Log the real cause server-side; never echo the exception text to the
        # client (it can leak bucket names, endpoints, credentials in tracebacks).
        logger.exception("Failed to generate presigned upload URL")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        ) from e


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
    """,
)
async def create_question(question: QuestionCreate):
    """Create a new question with comprehensive validation."""
    try:
        question_id = await QuestionService.create_question(question)
        return {"message": "Question created successfully", "id": question_id}
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the question: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=list[QuestionResponse],
    summary="Get all questions",
    description="Retrieve all questions from the database.",
)
async def get_all_questions():
    """Retrieve all questions."""
    try:
        questions = await QuestionService.get_all_questions()
        # Convert Beanie documents to response schema (mode='json' converts ObjectId to string)
        return [
            QuestionResponse(**q.model_dump(by_alias=True, mode="json"))
            for q in questions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching questions: {str(e)}",
        ) from e


@router.get(
    "/{id}",
    response_model=QuestionResponse,
    summary="Get question by ID",
    description="Retrieve a specific question by its MongoDB _id.",
)
async def get_question_by_id(id: str):
    """Retrieve a specific question by ID."""
    try:
        question = await QuestionService.get_question_by_id(id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{id}' not found",
            )
        # Convert Beanie document to response schema (mode='json' converts ObjectId to string)
        return QuestionResponse(**question.model_dump(by_alias=True, mode="json"))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the question: {str(e)}",
        ) from e


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
    """,
)
async def update_question(id: str, question_update: QuestionUpdate):
    """Update an existing question with validation."""
    try:
        updated = await QuestionService.update_question(id, question_update)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{id}' not found",
            )
        return {"message": "Question updated successfully", "id": id}
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"validation_errors": e.errors()},
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the question: {str(e)}",
        ) from e


@router.delete(
    "/{id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Delete question",
    description="Delete a question by its MongoDB _id.",
)
async def delete_question(id: str):
    """Delete a question by ID."""
    try:
        deleted = await QuestionService.delete_question(id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{id}' not found",
            )
        return {"message": "Question deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the question: {str(e)}",
        ) from e


# ============================================================================
# FILTER ENDPOINTS
# ============================================================================


@router.get(
    "/by-type/{question_type}",
    response_model=list[QuestionResponse],
    summary="Get questions by type",
    description="""
    Retrieve questions filtered by type.

    **Valid question types:**
    - `mcq` - Multiple choice with single correct answer
    - `multi` - Multiple choice with multiple correct answers
    - `true_false` - True/False questions
    - `text` - Open-ended text questions
    """,
)
async def get_questions_by_type(
    question_type: str,
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of questions to return"
    ),
):
    """Get questions filtered by type."""
    try:
        questions = await QuestionService.find_by_type(question_type, limit)
        return [
            QuestionResponse(**q.model_dump(by_alias=True, mode="json"))
            for q in questions
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        ) from e


@router.get(
    "/by-skill/{skill}",
    response_model=list[QuestionResponse],
    summary="Get questions by skill",
    description="Retrieve questions that include the specified skill.",
)
async def get_questions_by_skill(
    skill: str,
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of questions to return"
    ),
):
    """Get questions filtered by skill."""
    try:
        questions = await QuestionService.find_by_skill(skill, limit)
        return [
            QuestionResponse(**q.model_dump(by_alias=True, mode="json"))
            for q in questions
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        ) from e


@router.get(
    "/by-difficulty/{difficulty}",
    response_model=list[QuestionResponse],
    summary="Get questions by difficulty",
    description="""
    Retrieve questions filtered by difficulty level.

    **Valid difficulty levels:**
    - `easy` - Easy questions
    - `medium` - Medium difficulty questions
    - `hard` - Hard questions
    """,
)
async def get_questions_by_difficulty(
    difficulty: str,
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of questions to return"
    ),
):
    """Get questions filtered by difficulty."""
    try:
        questions = await QuestionService.find_by_difficulty(difficulty, limit)
        return [
            QuestionResponse(**q.model_dump(by_alias=True, mode="json"))
            for q in questions
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        ) from e


@router.get(
    "/by-tags",
    response_model=list[QuestionResponse],
    summary="Get questions by tags",
    description="""
    Retrieve questions that have any of the specified tags.

    **Usage:**
    - Provide tags as comma-separated query parameters
    - Example: `/by-tags?tags=python&tags=beginner&tags=loops`
    - Returns questions that have ANY of the specified tags
    """,
)
async def get_questions_by_tags(
    tags: list[str] = Query(..., description="List of tags to filter by"),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of questions to return"
    ),
):
    """Get questions filtered by tags."""
    try:
        questions = await QuestionService.find_by_tags(tags, limit)
        return [
            QuestionResponse(**q.model_dump(by_alias=True, mode="json"))
            for q in questions
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        ) from e


@router.get(
    "/filter",
    response_model=list[QuestionResponse],
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
    """,
)
async def filter_questions(
    type: str | None = Query(None, description="Question type filter"),
    skill: str | None = Query(None, description="Skill filter"),
    difficulty: str | None = Query(None, description="Difficulty filter"),
    tags: list[str] | None = Query(None, description="Tags filter (OR condition)"),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of questions to return"
    ),
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
            limit=limit,
        )
        return [
            QuestionResponse(**q.model_dump(by_alias=True, mode="json"))
            for q in questions
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        ) from e
