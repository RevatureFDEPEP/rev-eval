from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.test_service import TestService
from src.schemas.test_schema import TestCreate, TestUpdate, TestOut
from src.db.session import get_db
from src.utils.authorization import (
    assigned_test_ids,
    caller_id,
    can_read_test,
    forbidden,
    is_trainer,
    managed_test,
)
from src.utils.dependencies import get_current_trainer, get_current_user

router = APIRouter(prefix="/tests", tags=["Tests"])

# Trainers create and manage tests (only the tests they created; legacy tests
# with no recorded creator can be managed by any trainer). Participants read
# only the tests they have been assigned.


@router.post("/", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def create_test(
    test_in: TestCreate,
    db: AsyncSession = Depends(get_db),
    trainer: Dict = Depends(get_current_trainer),
):
    return await TestService.create_test(db, test_in, creator_id=caller_id(trainer))


@router.get("/", response_model=List[TestOut])
async def list_tests(db: AsyncSession = Depends(get_db), current_user: Dict = Depends(get_current_user)):
    tests = await TestService.list_all_tests(db)
    if is_trainer(current_user):
        return tests
    assigned = set(await assigned_test_ids(db, current_user))
    return [t for t in tests if t.id in assigned]


@router.get("/{test_id}/", response_model=TestOut)
async def get_test(test_id: int, db: AsyncSession = Depends(get_db), current_user: Dict = Depends(get_current_user)):
    if not await can_read_test(db, current_user, test_id):
        raise forbidden("This test has not been assigned to you")
    try:
        return await TestService.get_test_by_id(db, test_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found")


@router.put("/{test_id}/", response_model=TestOut)
async def update_test(
    test_id: int,
    test_in: TestUpdate,
    db: AsyncSession = Depends(get_db),
    trainer: Dict = Depends(get_current_trainer),
):
    """Update a test. Only the trainer who created it (or any trainer, for a legacy test)."""
    await managed_test(db, trainer, test_id)
    try:
        return await TestService.update_test(db, test_id, test_in)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found")


@router.delete("/{test_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: int,
    db: AsyncSession = Depends(get_db),
    trainer: Dict = Depends(get_current_trainer),
):
    """Delete a test. Only the trainer who created it (or any trainer, for a legacy test)."""
    await managed_test(db, trainer, test_id)
    try:
        await TestService.delete_test(db, test_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found")


@router.get("/created-by/{user_id}/", response_model=List[TestOut])
async def list_tests_created_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    trainer: Dict = Depends(get_current_trainer),
):
    """Get all tests created by a specific user (trainers only)."""
    return await TestService.list_tests_created_by_user(db, user_id)


@router.get("/submissions-by/{user_id}/", response_model=List[TestOut])
async def list_tests_with_submissions_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """Get all tests a user has submitted. A participant may ask only about themselves."""
    if not is_trainer(current_user) and user_id != caller_id(current_user):
        raise forbidden("You can only list your own tests")
    return await TestService.list_tests_with_submissions_by_user(db, user_id)
