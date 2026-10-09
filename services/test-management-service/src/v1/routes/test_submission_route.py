from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.test_submission_service import TestSubmissionService
from src.schemas.test_submission_schema import (
    TestSubmissionCreate,
    TestSubmissionUpdate,
    TestSubmissionOut,
    BulkAssignRequest,
    BulkAssignResult,
    TrainerReviewRequest,
    TrainerReviewResponse
)
from src.db.session import get_db
from src.utils.authorization import (
    caller_id,
    forbidden,
    is_trainer,
    managed_test,
    managed_test_ids,
    submission_for,
)
from src.utils.dependencies import get_current_trainer, get_current_user

router = APIRouter(prefix="/submissions", tags=["Test Submissions"])

# Participants read only their own submissions; everything that assigns,
# changes, reviews or grades a submission is a trainer operation, limited to
# submissions for tests that trainer manages (src/utils/authorization.py).


@router.post("/", response_model=TestSubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    submission_in: TestSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    trainer: Dict = Depends(get_current_trainer),
):
    await managed_test(db, trainer, submission_in.test_id)
    return await TestSubmissionService.create_submission(db, submission_in)


@router.get("/", response_model=List[TestSubmissionOut])
async def list_submissions(
    user_id: Optional[int] = Query(None, description="Filter submissions by user ID"),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List test submissions.

    - Participants always get their own submissions; asking for another
      user_id is refused.
    - Trainers get one user's submissions with user_id, or all submissions without it.
    """
    if not is_trainer(current_user):
        own_id = caller_id(current_user)
        if user_id is not None and user_id != own_id:
            raise forbidden("You can only list your own submissions")
        return await TestSubmissionService.list_submissions_by_user(db, own_id)

    if user_id is not None:
        return await TestSubmissionService.list_submissions_by_user(db, user_id)
    return await TestSubmissionService.list_all_submissions(db)


@router.get("/{submission_id}/", response_model=TestSubmissionOut)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    await submission_for(db, current_user, submission_id)
    try:
        return await TestSubmissionService.get_submission_by_id(db, submission_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Submission not found")


@router.put("/{submission_id}/", response_model=TestSubmissionOut)
async def update_submission(
    submission_id: int,
    submission_in: TestSubmissionUpdate,
    db: AsyncSession = Depends(get_db),
    trainer: Dict = Depends(get_current_trainer),
):
    await submission_for(db, trainer, submission_id, trainer_only=True)
    try:
        return await TestSubmissionService.update_submission(db, submission_id, submission_in)
    except ValueError:
        raise HTTPException(status_code=404, detail="Submission not found")


@router.delete("/{submission_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    trainer: Dict = Depends(get_current_trainer),
):
    await submission_for(db, trainer, submission_id, trainer_only=True)
    try:
        await TestSubmissionService.delete_submission(db, submission_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Submission not found")


@router.post("/bulk-assign", response_model=BulkAssignResult, status_code=status.HTTP_201_CREATED)
async def bulk_assign_test(
    request: BulkAssignRequest,
    trainer: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    Bulk assign a test the trainer manages to participants by email.
    Unknown emails are invited (inactive participant accounts) through user-service,
    which authorizes the lookup and the invite from the forwarded trainer token.
    """
    await managed_test(db, trainer, request.test_id)
    try:
        return await TestSubmissionService.bulk_assign_test(db, request, trainer, auth_header=authorization)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/trainer/evaluated", response_model=List[TestSubmissionOut])
async def get_evaluated_submissions_for_trainer(
    trainer: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """EVALUATED submissions, waiting for review, for tests this trainer created."""
    return await TestSubmissionService.get_evaluated_submissions_for_trainer(
        db, caller_id(trainer), auth_header=authorization
    )


@router.get("/trainer/all", response_model=List[TestSubmissionOut])
async def get_all_submissions_for_trainer(
    trainer: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """All non-EVALUATED submissions for tests this trainer created, QUIZ and INTERVIEW."""
    return await TestSubmissionService.get_all_submissions_for_trainer(
        db, caller_id(trainer), auth_header=authorization
    )


@router.get("/graded")
async def get_graded_submissions(
    trainer: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db)
):
    """GRADED submissions (already reviewed) for tests this trainer manages."""
    managed = set(await managed_test_ids(db, trainer))
    graded = await TestSubmissionService.get_graded_submissions(db)
    return [s for s in graded if s.test_id in managed]


@router.get("/{submission_id}/review-details")
async def get_submission_review_details(
    submission_id: int,
    trainer: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db)
):
    """
    Full review details for a submission (metadata, test, interview transcript,
    AI evaluation), for the trainer who manages its test.
    """
    await submission_for(db, trainer, submission_id, trainer_only=True)
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
    trainer: Dict = Depends(get_current_trainer),
    db: AsyncSession = Depends(get_db)
):
    """
    Record the trainer's score and feedback; the submission becomes GRADED.
    Only the trainer who manages the submission's test can grade it.
    """
    await submission_for(db, trainer, submission_id, trainer_only=True)
    try:
        return await TestSubmissionService.submit_trainer_review(
            db, submission_id, review, caller_id(trainer)
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting review: {str(e)}")
