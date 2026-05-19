from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.test_repository import TestRepository
from src.repositories.test_skill_repository import TestSkillRepository
from src.repositories.skill_repository import SkillRepository
from src.schemas.test_schema import TestCreate, TestUpdate, TestOut
from src.schemas.skill_schema import SkillOut
from src.schemas.test_skill_schema import TestSkillCreate

class TestService:

    @staticmethod
    async def create_test(db: AsyncSession, test_in: TestCreate, creator_id: int) -> TestOut:
        """
        Create a new test and automatically link skills
        """
        # Step 1: create test
        test_data = test_in.dict(exclude={"skill_ids"})
        test_data["created_by_id"] = creator_id
        test = await TestRepository.create(db, TestCreate(**test_data))
        
        # Step 2: link skills using TestSkill
        for skill_id in test_in.skill_ids:
            ts_in = TestSkillCreate(test_id=test.id, skill_id=skill_id)
            await TestSkillRepository.create(db, ts_in)

        # Step 3: fetch skill info for output - more efficient
        skills = []
        for skill_id in test_in.skill_ids:
            skill = await SkillRepository.get_by_id(db, skill_id)
            if skill:
                skills.append(skill)

        return TestOut.from_orm(test).copy(update={"skills": [SkillOut.from_orm(s) for s in skills]})

    @staticmethod
    async def update_test(db: AsyncSession, test_id: int, test_in: TestUpdate) -> TestOut:
        """
        Update a test and optionally update its skills
        """
        test = await TestRepository.get_by_id(db, test_id)
        if not test:
            raise ValueError("Test not found")

        # Update basic fields
        test = await TestRepository.update(db, test, test_in)

        # Update skills if provided
        if test_in.skill_ids is not None:
            # Query existing links explicitly (no relationship access)
            existing_links = await TestSkillRepository.list_by_test(db, test_id)
            
            # Remove existing links
            for link in existing_links:
                await TestSkillRepository.delete(db, link)
            
            # Add new links
            for skill_id in test_in.skill_ids:
                ts_in = TestSkillCreate(test_id=test.id, skill_id=skill_id)
                await TestSkillRepository.create(db, ts_in)
            
            # Fetch skills for response
            skills = []
            for skill_id in test_in.skill_ids:
                skill = await SkillRepository.get_by_id(db, skill_id)
                if skill:
                    skills.append(skill)
        else:
            # If not updating skills, fetch current ones
            current_links = await TestSkillRepository.list_by_test(db, test_id)
            skills = []
            for link in current_links:
                skill = await SkillRepository.get_by_id(db, link.skill_id)
                if skill:
                    skills.append(skill)

        return TestOut.from_orm(test).copy(update={"skills": [SkillOut.from_orm(s) for s in skills]})

    @staticmethod
    async def delete_test(db: AsyncSession, test_id: int) -> None:
        test = await TestRepository.get_by_id(db, test_id)
        if not test:
            raise ValueError("Test not found")
        await TestRepository.delete(db, test)

    @staticmethod
    async def get_test_by_id(db: AsyncSession, test_id: int) -> TestOut:
        test = await TestRepository.get_by_id(db, test_id)
        if not test:
            raise ValueError("Test not found")
        
        # Fetch associated skills explicitly
        links = await TestSkillRepository.list_by_test(db, test_id)
        skills = []
        for link in links:
            skill = await SkillRepository.get_by_id(db, link.skill_id)
            if skill:
                skills.append(skill)
        
        return TestOut.from_orm(test).copy(update={"skills": [SkillOut.from_orm(s) for s in skills]})

    @staticmethod
    async def list_all_tests(db: AsyncSession) -> List[TestOut]:
        tests = await TestRepository.list_all(db)
        
        # Fetch skills for each test
        results = []
        for test in tests:
            links = await TestSkillRepository.list_by_test(db, test.id)
            skills = []
            for link in links:
                skill = await SkillRepository.get_by_id(db, link.skill_id)
                if skill:
                    skills.append(skill)
            
            results.append(
                TestOut.from_orm(test).copy(update={"skills": [SkillOut.from_orm(s) for s in skills]})
            )
        
        return results

    @staticmethod
    async def list_tests_created_by_user(db: AsyncSession, user_id: int) -> List[TestOut]:
        """
        Return all tests created by a specific user
        """
        tests = await TestRepository.list_by_creator(db, user_id)
        
        # Fetch skills for each test
        results = []
        for test in tests:
            links = await TestSkillRepository.list_by_test(db, test.id)
            skills = []
            for link in links:
                skill = await SkillRepository.get_by_id(db, link.skill_id)
                if skill:
                    skills.append(skill)
            
            results.append(
                TestOut.from_orm(test).copy(update={"skills": [SkillOut.from_orm(s) for s in skills]})
            )
        
        return results

    @staticmethod
    async def list_tests_with_submissions_by_user(db: AsyncSession, user_id: int) -> List[TestOut]:
        """
        Return all tests for which the user has submitted (has test submissions)
        """
        from src.repositories.test_submission_repository import TestSubmissionRepository

        # Get submissions by this user
        submissions = await TestSubmissionRepository.list_by_user(db, user_id)
        
        # Get unique test IDs
        user_test_ids = list(set(s.test_id for s in submissions))

        # Fetch test objects with skills
        results = []
        for tid in user_test_ids:
            test = await TestRepository.get_by_id(db, tid)
            if test:
                links = await TestSkillRepository.list_by_test(db, tid)
                skills = []
                for link in links:
                    skill = await SkillRepository.get_by_id(db, link.skill_id)
                    if skill:
                        skills.append(skill)
                
                results.append(
                    TestOut.from_orm(test).copy(update={"skills": [SkillOut.from_orm(s) for s in skills]})
                )

        return results