
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError

from src.models.question import Question
from src.schemas.question import (
    PresignedUploadResponse,
    QuestionCreate,
    QuestionResponse,
    QuestionUpdate,
)
from src.services.question_service import QuestionService
from src.services.upload_service import UploadService
from src.utils.dependencies import require_trainer
from src.utils.s3_client import generate_presigned_get_url

router = APIRouter(prefix="/questions", tags=["Questions"])


def _to_response(question: Question) -> QuestionResponse:
    """Convert a Beanie document to the response schema, enriching the image.

    ``mode='json'`` converts ObjectId to string. When an image is attached, a
    fresh pre-signed GET URL is minted so the client can render it directly.
    Used on single-document endpoints only — list endpoints skip enrichment to
    avoid minting one pre-signed URL per row.
    """
    data = question.model_dump(by_alias=True, mode='json')
    if data.get("image_object_key"):
        data["image_url"] = generate_presigned_get_url(data["image_object_key"])
    return QuestionResponse(**data)


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
async def create_question(question: QuestionCreate):
    """Create a new question with comprehensive validation."""
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
    response_model=list[QuestionResponse],
    summary="Get all questions",
    description="Retrieve all questions from the database."
)
async def get_all_questions():
    """Retrieve all questions."""
    try:
        questions = await QuestionService.get_all_questions()
        # Convert Beanie documents to response schema (mode='json' converts ObjectId to string)
        return [QuestionResponse(**q.model_dump(by_alias=True, mode='json')) for q in questions]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching questions: {str(e)}"
        )


# NOTE: declared BEFORE "/{id}" — otherwise the path parameter captures
# "presigned-upload-url" and this endpoint becomes unreachable.
@router.get(
    "/presigned-upload-url",
    response_model=PresignedUploadResponse,
    summary="Get a pre-signed upload policy for a question image",
    description="""
    Generate a pre-signed MinIO POST policy for uploading a question diagram
    or screenshot directly from the browser. **Trainer only.**

    **Flow:**
    1. Client requests this endpoint with the file's `content_type`.
    2. Client POSTs the file as multipart/form-data to `url`, including every
       key/value in `fields` plus the `file` field.
    3. Client stores the returned `object_key` on the question via create/update.

    The 5 MB size ceiling is enforced server-side by the policy, not just the
    browser. **Allowed content types:** `image/png`, `image/jpeg`.
    """
)
async def get_presigned_upload_url(
    content_type: str = Query(..., description="MIME type of the file (image/png or image/jpeg)"),
    _: str = Depends(require_trainer),
):
    """Generate a pre-signed upload policy for a question image (trainer only)."""
    try:
        return UploadService.presigned_question_image_upload(content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the upload URL: {str(e)}",
        ) from e


# NOTE: declared BEFORE "/{id}" — otherwise the path parameter captures
# "sample" and this endpoint becomes unreachable.
@router.get(
    "/sample",
    response_model=list[QuestionResponse],
    summary="Sample N random questions from the whole bank",
    description="""
    Return a random sample of questions drawn from the entire question bank
    using MongoDB's ``$sample`` aggregation. Used internally by
    test-management-service to seed a quiz session.

    Sampling is **not** skill-filtered — it draws from all questions.
    """,
)
async def sample_questions(
    limit: int = Query(..., ge=1, le=500, description="Number of questions to sample"),
):
    """Return ``limit`` randomly sampled questions."""
    try:
        questions = await QuestionService.sample_questions(limit)
        return [QuestionResponse(**q.model_dump(by_alias=True, mode='json')) for q in questions]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while sampling questions: {str(e)}"
        )


@router.get(
    "/{id}",
    response_model=QuestionResponse,
    summary="Get question by ID",
    description="Retrieve a specific question by its MongoDB _id."
)
async def get_question_by_id(id: str):
    """Retrieve a specific question by ID."""
    try:
        question = await QuestionService.get_question_by_id(id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID '{id}' not found"
            )
        # Single-document endpoint: enrich with a pre-signed image_url if present.
        return _to_response(question)
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
async def update_question(id: str, question_update: QuestionUpdate):
    """Update an existing question with validation."""
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
async def delete_question(id: str):
    """Delete a question by ID."""
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
    response_model=list[QuestionResponse],
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
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return")
):
    """Get questions filtered by type."""
    try:
        questions = await QuestionService.find_by_type(question_type, limit)
        return [QuestionResponse(**q.model_dump(by_alias=True, mode='json')) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.get(
    "/by-skill/{skill}",
    response_model=list[QuestionResponse],
    summary="Get questions by skill",
    description="Retrieve questions that include the specified skill."
)
async def get_questions_by_skill(
    skill: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return")
):
    """Get questions filtered by skill."""
    try:
        questions = await QuestionService.find_by_skill(skill, limit)
        return [QuestionResponse(**q.model_dump(by_alias=True, mode='json')) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


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
    """
)
async def get_questions_by_difficulty(
    difficulty: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return")
):
    """Get questions filtered by difficulty."""
    try:
        questions = await QuestionService.find_by_difficulty(difficulty, limit)
        return [QuestionResponse(**q.model_dump(by_alias=True, mode='json')) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


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
    """
)
async def get_questions_by_tags(
    tags: list[str] = Query(..., description="List of tags to filter by"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return")
):
    """Get questions filtered by tags."""
    try:
        questions = await QuestionService.find_by_tags(tags, limit)
        return [QuestionResponse(**q.model_dump(by_alias=True, mode='json')) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


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
    """
)
async def filter_questions(
    type: str | None = Query(None, description="Question type filter"),
    skill: str | None = Query(None, description="Skill filter"),
    difficulty: str | None = Query(None, description="Difficulty filter"),
    tags: list[str] | None = Query(None, description="Tags filter (OR condition)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return")
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
        return [QuestionResponse(**q.model_dump(by_alias=True, mode='json')) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )
