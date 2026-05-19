# src/repositories/test_submission_repository.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from src.models.test_submission import TestSubmission
from src.schemas.test_submission_schema import TestSubmissionCreate, TestSubmissionUpdate

class TestSubmissionRepository:

    @staticmethod
    def _strip_timezone_from_dict(data: dict) -> dict:
        """Strip timezone info from datetime fields for POC"""
        datetime_fields = ['due_date', 'assigned_at', 'started_at', 'submitted_at']
        for field in datetime_fields:
            if field in data and data[field] is not None:
                if isinstance(data[field], datetime) and data[field].tzinfo is not None:
                    data[field] = data[field].replace(tzinfo=None)
        return data

    @staticmethod
    async def get_by_id(db: AsyncSession, submission_id: int) -> Optional[TestSubmission]:
        result = await db.execute(
            select(TestSubmission)
            .options(selectinload(TestSubmission.test))  # Eagerly load test relationship
            .where(TestSubmission.id == submission_id)
        )
        return result.scalars().first()

    @staticmethod
    async def list_all(db: AsyncSession) -> List[TestSubmission]:
        result = await db.execute(
            select(TestSubmission)
            .options(selectinload(TestSubmission.test))  # Eagerly load test relationship
            .order_by(TestSubmission.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_by_user(db: AsyncSession, user_id: int) -> List[TestSubmission]:
        """Get all test submissions by a specific user"""
        result = await db.execute(
            select(TestSubmission)
            .options(selectinload(TestSubmission.test))  # Eagerly load test relationship
            .where(TestSubmission.user_id == user_id)
            .order_by(TestSubmission.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def list_by_test(db: AsyncSession, test_id: int) -> List[TestSubmission]:
        """Get all submissions for a specific test"""
        result = await db.execute(
            select(TestSubmission)
            .options(selectinload(TestSubmission.test))  # Eagerly load test relationship
            .where(TestSubmission.test_id == test_id)
            .order_by(TestSubmission.created_at.desc())
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_user_and_test(
        db: AsyncSession,
        user_id: int,
        test_id: int
    ) -> Optional[TestSubmission]:
        """Get a user's submission for a specific test (most recent if multiple)"""
        result = await db.execute(
            select(TestSubmission)
            .options(selectinload(TestSubmission.test))  # Eagerly load test relationship
            .where(
                TestSubmission.user_id == user_id,
                TestSubmission.test_id == test_id
            )
            .order_by(TestSubmission.created_at.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, submission_in: TestSubmissionCreate) -> TestSubmission:
        # Convert to dict and strip timezones (POC fix)
        submission_data = submission_in.model_dump() if hasattr(submission_in, 'model_dump') else submission_in.dict()
        submission_data = TestSubmissionRepository._strip_timezone_from_dict(submission_data)
        
        submission = TestSubmission(**submission_data)
        db.add(submission)
        await db.commit()
        await db.refresh(submission)
        return submission

    @staticmethod
    async def update(db: AsyncSession, submission: TestSubmission, submission_in: TestSubmissionUpdate) -> TestSubmission:
        # Convert to dict and strip timezones (POC fix)
        update_data = submission_in.model_dump(exclude_unset=True) if hasattr(submission_in, 'model_dump') else submission_in.dict(exclude_unset=True)
        update_data = TestSubmissionRepository._strip_timezone_from_dict(update_data)
        
        for field, value in update_data.items():
            setattr(submission, field, value)
        await db.commit()
        await db.refresh(submission)
        return submission

    @staticmethod
    async def delete(db: AsyncSession, submission: TestSubmission) -> None:
        await db.delete(submission)
        await db.commit()