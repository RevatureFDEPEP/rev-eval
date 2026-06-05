from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
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
from src.utils.s3_client import generate_presigned_get_url

router = APIRouter(prefix="/questions", tags=["Questions"])


def _to_response(question: Question) -> QuestionResponse:
    """Convert a Beanie document to the response schema.

    mode='json' converts ObjectId to string. When an image is attached,
    enrich with a pre-signed GET URL so clients can render it directly.
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
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the question: {str(e)}"
        ) from e


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
        return [_to_response(q) for q in questions]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching questions: {str(e)}"
        ) from e


# NOTE: must be declared before "/{id}" or the path parameter captures it.
@router.get(
    "/presigned-upload-url",
    response_model=PresignedUploadResponse,
    summary="Get a pre-signed PUT URL for a question image",
    description="""
    Generate a pre-signed MinIO PUT URL for uploading a question diagram or
    screenshot directly from the browser.

    **Flow:**
    1. Client requests this endpoint with the file's `content_type`
    2. Client PUTs the file bytes to the returned `upload_url`
       (the `Content-Type` request header must match exactly)
    3. Client stores `object_key` on the question via create/update

    **Allowed content types:** `image/png`, `image/jpeg`
    """
)
async def get_presigned_upload_url(
    content_type: str = Query(..., description="MIME type of the file to upload (image/png or image/jpeg)")
):
    """Generate a pre-signed PUT URL for a question image upload."""
    try:
        return UploadService.presigned_question_image_upload(content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the upload URL: {str(e)}"
        ) from e


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
        # Convert Beanie document to response schema (mode='json' converts ObjectId to string)
        return _to_response(question)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the question: {str(e)}"
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
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating the question: {str(e)}"
        ) from e


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
        ) from e


# ============================================================================
# FILTER ENDPOINTS
# ============================================================================


@router.get(
    "/by-type/{question_type}",
    response_model=List[QuestionResponse],
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
        return [_to_response(q) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        ) from e


@router.get(
    "/by-skill/{skill}",
    response_model=List[QuestionResponse],
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
        return [_to_response(q) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        ) from e


@router.get(
    "/by-difficulty/{difficulty}",
    response_model=List[QuestionResponse],
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
        return [_to_response(q) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        ) from e


@router.get(
    "/by-tags",
    response_model=List[QuestionResponse],
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
    limit: int = Query(100, ge=1, le=500, description="Maximum number of questions to return")
):
    """Get questions filtered by tags."""
    try:
        questions = await QuestionService.find_by_tags(tags, limit)
        return [_to_response(q) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        ) from e


@router.get(
    "/filter",
    response_model=List[QuestionResponse],
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
        return [_to_response(q) for q in questions]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        ) from e
