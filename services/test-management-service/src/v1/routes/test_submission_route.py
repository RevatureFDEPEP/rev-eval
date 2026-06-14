from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.test_submission_schema import (
    BulkAssignRequest,
    BulkAssignResult,
    TestSubmissionCreate,
    TestSubmissionOut,
    TestSubmissionUpdate,
    TrainerReviewRequest,
    TrainerReviewResponse,
)
from src.services.test_submission_service import TestSubmissionService
from src.utils.dependencies import (
    ensure_can_access_submission,
    get_current_trainer_or_admin,
    get_current_user_from_headers,
    is_admin,
    is_trainer,
)

router = APIRouter(prefix="/submissions", tags=["Test Submissions"])

@router.post("/", response_model=TestSubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    submission_in: TestSubmissionCreate,
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    """Create a submission. Participants may only create their own; trainers
    and admins may create on behalf of any user (assignment workflows)."""
    if not (is_trainer(current_user) or is_admin(current_user)):
        caller_id = current_user.get("id")
        if caller_id is None or int(submission_in.user_id) != int(caller_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Participants may only create submissions for themselves",
            )
    return await TestSubmissionService.create_submission(db, submission_in)

@router.get("/", response_model=List[TestSubmissionOut])
async def list_submissions(
    user_id: Optional[int] = Query(None, description="Filter submissions by user ID"),
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db)
):
    """
    List test submissions.

    - Participants only ever see their own submissions; a `?user_id=` pointing
      at another user is rejected.
    - Trainers/admins may filter by `user_id` or list all.
    """
    privileged = is_trainer(current_user) or is_admin(current_user)
    auth_user_id = current_user.get("id")

    if not privileged:
        # Participants are pinned to their own submissions regardless of input.
        if user_id is not None and (auth_user_id is None or int(user_id) != int(auth_user_id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You may only view your own submissions",
            )
        if auth_user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
        return await TestSubmissionService.list_submissions_by_user(db, auth_user_id)

    if user_id is not None:
        return await TestSubmissionService.list_submissions_by_user(db, user_id)
    return await TestSubmissionService.list_all_submissions(db)

@router.get("/{submission_id}/", response_model=TestSubmissionOut)
async def get_submission(
    submission_id: int,
    current_user: Dict = Depends(get_current_user_from_headers),
    db: AsyncSession = Depends(get_db),
):
    try:
        submission = await TestSubmissionService.get_submission_by_id(db, submission_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Submission not found")
    ensure_can_access_submission(current_user, submission.user_id)
    return submission

@router.put("/{submission_id}/", response_model=TestSubmissionOut)
async def update_submission(
    submission_id: int,
    submission_in: TestSubmissionUpdate,
    _caller: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mutate submission status/scores. Trainer/admin only."""
    try:
        return await TestSubmissionService.update_submission(db, submission_id, submission_in)
    except ValueError:
        raise HTTPException(status_code=404, detail="Submission not found")

@router.delete("/{submission_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    _caller: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a submission. Trainer/admin only."""
    try:
        await TestSubmissionService.delete_submission(db, submission_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Submission not found")

@router.post("/bulk-assign", response_model=BulkAssignResult, status_code=status.HTTP_201_CREATED)
async def bulk_assign_test(
    request: BulkAssignRequest,
    current_user: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk assign a test to multiple participants by email.
    Creates user records (inactive) for unknown emails.
    The assigned_by_id is automatically extracted from gateway headers and resolved via user-service.
    """
    return await TestSubmissionService.bulk_assign_test(db, request, current_user)


@router.get("/trainer/evaluated", response_model=List[TestSubmissionOut])
async def get_evaluated_submissions_for_trainer(
    current_user: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of EVALUATED submissions for tests created by this trainer.

    This endpoint returns submissions that:
    - Have status EVALUATED (AI evaluation complete)
    - Are for tests created by the authenticated trainer
    - Are waiting for trainer review
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    trainer_id = current_user.get("id")
    if not trainer_id:
        raise HTTPException(status_code=401, detail="Invalid user")

    return await TestSubmissionService.get_evaluated_submissions_for_trainer(db, trainer_id)


@router.get("/trainer/all", response_model=List[TestSubmissionOut])
async def get_all_submissions_for_trainer(
    current_user: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ALL submissions for tests created by this trainer across all statuses.

    This endpoint returns submissions that:
    - Are for tests created by the authenticated trainer
    - Include ALL statuses (ASSIGNED, IN_PROGRESS, COMPLETED, EVALUATED, GRADED, ABANDONED)
    - Include both QUIZ and INTERVIEW test types
    - Include test relationship for test_name and test_type
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    trainer_id = current_user.get("id")
    if not trainer_id:
        raise HTTPException(status_code=401, detail="Invalid user")

    return await TestSubmissionService.get_all_submissions_for_trainer(db, trainer_id)


@router.get("/graded")
async def get_graded_submissions(
    current_user: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of graded submissions (already reviewed by trainer).
    Returns submissions with GRADED status.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    return await TestSubmissionService.get_graded_submissions(db)


@router.get("/{submission_id}/review-details")
async def get_submission_review_details(
    submission_id: int,
    current_user: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full review details for a submission including:
    - Submission metadata
    - Test information
    - Interview transcript (from MongoDB via interview service)
    - AI evaluation data

    This is used by trainers to review and score interviews.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        return await TestSubmissionService.get_submission_review_details(db, submission_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching review details: {str(e)}")


@router.post("/{submission_id}/trainer-review", response_model=TrainerReviewResponse)
async def submit_trainer_review(
    submission_id: int,
    review: TrainerReviewRequest,
    current_user: Dict = Depends(get_current_trainer_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit trainer's review and score for a submission.

    Updates:
    - trainer_score: Trainer's score
    - final_score: Set to trainer_score (authoritative)
    - feedback: Trainer's feedback (optional)
    - reviewed_at: Current timestamp
    - reviewed_by_id: Trainer's user ID
    - status: Changed to GRADED
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    trainer_id = current_user.get("id")
    if not trainer_id:
        raise HTTPException(status_code=401, detail="Invalid user")

    try:
        return await TestSubmissionService.submit_trainer_review(
            db, submission_id, review, trainer_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting review: {str(e)}")
