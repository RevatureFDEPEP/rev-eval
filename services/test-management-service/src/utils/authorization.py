"""
Record-level authorization for test-management-service.

Authentication (who the caller is) comes from src.utils.dependencies. These
helpers decide which records that caller may touch:

- A trainer manages a test they created. Tests with no recorded creator
  (created before ownership was tracked) can be managed by any trainer.
- A trainer reaches a submission or quiz session through the test it belongs to.
- A participant reaches only their own submissions and quiz sessions, and only
  the tests they have been assigned.

Every check runs before the route reads or writes the record it protects.
"""
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.test import Test
from src.models.test_submission import TestSubmission
from src.repositories.test_repository import TestRepository
from src.repositories.test_submission_repository import TestSubmissionRepository


def caller_id(user: Dict[str, Any]) -> int:
    user_id = user.get("id")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return int(user_id)


def is_trainer(user: Dict[str, Any]) -> bool:
    return (user.get("role") or "").upper() == "TRAINER"


def forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def trainer_manages_test(user: Dict[str, Any], test: Test) -> bool:
    return is_trainer(user) and (test.created_by_id is None or test.created_by_id == caller_id(user))


async def managed_test(db: AsyncSession, user: Dict[str, Any], test_id: int) -> Test:
    """The test, if this trainer manages it; 404 if it does not exist, else 403."""
    if not is_trainer(user):
        raise forbidden("This endpoint requires trainer role")
    test = await TestRepository.get_by_id(db, test_id)
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    if not trainer_manages_test(user, test):
        raise forbidden("Only the trainer who created this test can manage it")
    return test


async def managed_test_ids(db: AsyncSession, user: Dict[str, Any]) -> List[int]:
    """Ids of the tests this trainer manages."""
    result = await db.execute(
        select(Test.id).where(or_(Test.created_by_id == caller_id(user), Test.created_by_id.is_(None)))
    )
    return [row[0] for row in result.all()]


async def assigned_test_ids(db: AsyncSession, user: Dict[str, Any]) -> List[int]:
    """Ids of the tests this participant has a submission for."""
    result = await db.execute(
        select(TestSubmission.test_id).where(TestSubmission.user_id == caller_id(user)).distinct()
    )
    return [row[0] for row in result.all()]


async def can_read_test(db: AsyncSession, user: Dict[str, Any], test_id: int) -> bool:
    if is_trainer(user):
        return True
    return test_id in await assigned_test_ids(db, user)


async def submission_for(
    db: AsyncSession, user: Dict[str, Any], submission_id: int, *, trainer_only: bool = False
) -> TestSubmission:
    """
    The submission, if the caller may reach it: its participant (unless
    trainer_only), or a trainer who manages its test. 404 if it does not exist.
    """
    submission = await TestSubmissionRepository.get_by_id(db, submission_id)
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    await check_submission_access(db, user, submission, trainer_only=trainer_only)
    return submission


async def check_submission_access(
    db: AsyncSession, user: Dict[str, Any], submission: TestSubmission, *, trainer_only: bool = False
) -> None:
    if is_trainer(user):
        test: Optional[Test] = await TestRepository.get_by_id(db, submission.test_id)
        if test is not None and trainer_manages_test(user, test):
            return
        raise forbidden("Only the trainer who created this test can access its submissions")
    if trainer_only:
        raise forbidden("This endpoint requires trainer role")
    if submission.user_id != caller_id(user):
        raise forbidden("You can only access your own submissions")
