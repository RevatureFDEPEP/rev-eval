from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from src.models.test import Test
from src.schemas.test_schema import TestCreate, TestUpdate

class TestRepository:


    @staticmethod
    async def get_by_id(db: AsyncSession, test_id: int) -> Optional[Test]:
        result = await db.execute(select(Test).where(Test.id == test_id))
        test = result.scalars().first()
        if test and test.duration:
            test.duration_seconds = int(test.duration.total_seconds())
        else:
            test.duration_seconds = None
        return test
    @staticmethod
    async def list_all(db: AsyncSession) -> List[Test]:
        result = await db.execute(select(Test))
        tests = result.scalars().all()
        for test in tests:
            if test.duration:
                test.duration_seconds = int(test.duration.total_seconds())
            else:
                test.duration_seconds = None
        return tests
    @staticmethod
    async def create(db: AsyncSession, test_in: TestCreate) -> Test:
        test_data = test_in.dict(exclude={"skill_ids", "duration_seconds"})
        
        # Convert seconds → timedelta
        if test_in.duration_seconds is not None:
            test_data["duration"] = timedelta(seconds=test_in.duration_seconds)
        
        test = Test(**test_data)
        db.add(test)
        await db.commit()
        await db.refresh(test)
        return test


    @staticmethod
    async def update(db: AsyncSession, test: Test, test_in: TestUpdate) -> Test:
        update_data = test_in.dict(exclude_unset=True, exclude={"skill_ids"})
        
        # Convert seconds → timedelta
        if "duration_seconds" in update_data:
            update_data["duration"] = timedelta(seconds=update_data.pop("duration_seconds"))
        
        for field, value in update_data.items():
            setattr(test, field, value)
        
        await db.commit()
        await db.refresh(test)
        return test
    @staticmethod
    async def delete(db: AsyncSession, test: Test) -> None:
        await db.delete(test)
        await db.commit()
    
    @staticmethod
    async def list_by_creator(db: AsyncSession, creator_id: int) -> List[Test]:
        """Get all tests created by a specific user"""
        result = await db.execute(
            select(Test)
            .where(Test.created_by_id == creator_id)
            .order_by(Test.created_at.desc())
        )
        tests = list(result.scalars().all())
        for test in tests:
            if test.duration:
                test.duration_seconds = int(test.duration.total_seconds())
            else:
                test.duration_seconds = None
        return tests
    


