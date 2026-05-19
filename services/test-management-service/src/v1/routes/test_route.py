from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.test_service import TestService
from src.schemas.test_schema import TestCreate, TestUpdate, TestOut
from src.db.session import get_db
from src.utils.dependencies import get_current_user_from_headers

router = APIRouter(prefix="/tests", tags=["Tests"])

# Get current user's database ID from headers
async def get_current_user_id(current_user: dict = Depends(get_current_user_from_headers)) -> int:
    """
    Extract the database user ID from the current user context.
    
    The current_user dict comes from get_current_user_from_headers which
    fetches the user from user-service and returns the full user object including 'id'.
    """
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in user context"
        )
    return int(user_id)

@router.post("/", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def create_test(test_in: TestCreate, db: AsyncSession = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    return await TestService.create_test(db, test_in, creator_id=user_id)

@router.get("/", response_model=List[TestOut])
async def list_tests(db: AsyncSession = Depends(get_db)):
    return await TestService.list_all_tests(db)

@router.get("/{test_id}/", response_model=TestOut)
async def get_test(test_id: int, db: AsyncSession = Depends(get_db)):
    try:
        return await TestService.get_test_by_id(db, test_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found")

@router.put("/{test_id}/", response_model=TestOut)
async def update_test(
    test_id: int, 
    test_in: TestUpdate, 
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Update a test. Only the creator can update their test.
    If created_by_id is null (legacy test), allow editing.
    """
    try:
        # Get the test to check ownership
        test = await TestService.get_test_by_id(db, test_id)
        
        # Check if user is the creator
        # If created_by_id is null, allow editing (legacy tests)
        if test.created_by_id is not None and test.created_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this test. Only the creator can update it."
            )
        
        return await TestService.update_test(db, test_id, test_in)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found")

@router.delete("/{test_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: int, 
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """
    Delete a test. Only the creator can delete their test.
    If created_by_id is null (legacy test), allow deletion.
    """
    try:
        # Get the test to check ownership
        test = await TestService.get_test_by_id(db, test_id)
        
        # Check if user is the creator
        # If created_by_id is null, allow deletion (legacy tests)
        if test.created_by_id is not None and test.created_by_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this test. Only the creator can delete it."
            )
        
        await TestService.delete_test(db, test_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test not found")

@router.get("/created-by/{user_id}/", response_model=List[TestOut])
async def list_tests_created_by_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get all tests created by a specific user"""
    return await TestService.list_tests_created_by_user(db, user_id)

@router.get("/submissions-by/{user_id}/", response_model=List[TestOut])
async def list_tests_with_submissions_by_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get all tests that a specific user has submitted"""
    return await TestService.list_tests_with_submissions_by_user(db, user_id)