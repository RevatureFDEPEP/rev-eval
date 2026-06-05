import pytest
from src.models.test import Test, TestType
from src.models.skill import Skill
from src.models.test_submission import TestSubmission, SubmissionStatus


class TestTestTypeEnum:
    @pytest.mark.parametrize("value", ["QUIZ", "INTERVIEW"])
    def test_value_exists(self, value):
        assert TestType(value) is not None

    def test_quiz_string_value(self):
        assert TestType.QUIZ == "QUIZ"

    def test_interview_string_value(self):
        assert TestType.INTERVIEW == "INTERVIEW"

    def test_all_types_are_str(self):
        for t in TestType:
            assert isinstance(t, str)


class TestSubmissionStatusEnum:
    @pytest.mark.parametrize("status,expected", [
        (SubmissionStatus.ASSIGNED, "ASSIGNED"),
        (SubmissionStatus.IN_PROGRESS, "IN_PROGRESS"),
        (SubmissionStatus.COMPLETED, "COMPLETED"),
        (SubmissionStatus.EVALUATED, "EVALUATED"),
        (SubmissionStatus.GRADED, "GRADED"),
        (SubmissionStatus.ABANDONED, "ABANDONED"),
    ])
    def test_status_string_values(self, status, expected):
        assert status == expected

    def test_six_statuses_defined(self):
        assert len(SubmissionStatus) == 6


class TestTestModel:
    async def test_create_minimal_test(self, db):
        test = Test(name="Java Quiz", test_type=TestType.QUIZ)
        db.add(test)
        await db.commit()
        await db.refresh(test)
        assert test.id is not None
        assert test.name == "Java Quiz"

    async def test_active_defaults_true(self, db):
        test = Test(name="Active Test", test_type=TestType.QUIZ)
        db.add(test)
        await db.commit()
        await db.refresh(test)
        assert test.active is True

    async def test_number_of_questions_default(self, db):
        test = Test(name="Default Q Count", test_type=TestType.QUIZ)
        db.add(test)
        await db.commit()
        await db.refresh(test)
        assert test.number_of_questions == 20

    async def test_timestamps_auto_set(self, db):
        test = Test(name="Timestamp Test", test_type=TestType.QUIZ)
        db.add(test)
        await db.commit()
        await db.refresh(test)
        assert test.created_at is not None
        assert test.updated_at is not None

    @pytest.mark.parametrize("test_type", [TestType.QUIZ, TestType.INTERVIEW])
    async def test_both_types_persist(self, db, test_type):
        test = Test(name=f"{test_type} Test", test_type=test_type)
        db.add(test)
        await db.commit()
        await db.refresh(test)
        assert test.test_type == test_type

    async def test_optional_metadata_fields(self, db):
        test = Test(
            name="Full Test",
            test_type=TestType.QUIZ,
            role="Java Developer",
            curriculum="Java 101",
            created_by_id=1,
        )
        db.add(test)
        await db.commit()
        await db.refresh(test)
        assert test.role == "Java Developer"
        assert test.curriculum == "Java 101"
        assert test.created_by_id == 1


class TestSkillModel:
    async def test_create_skill(self, db):
        skill = Skill(name="Python", description="Python programming")
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        assert skill.id is not None
        assert skill.name == "Python"

    async def test_description_optional(self, db):
        skill = Skill(name="Java")
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        assert skill.description is None

    @pytest.mark.parametrize("name,desc", [
        ("Python", "Python programming"),
        ("SQL", None),
        ("Spring Boot", "Java framework"),
    ])
    async def test_skill_persists_with_various_data(self, db, name, desc):
        skill = Skill(name=name, description=desc)
        db.add(skill)
        await db.commit()
        await db.refresh(skill)
        assert skill.name == name
        assert skill.description == desc

    def test_repr_contains_name_and_id(self):
        skill = Skill(id=5, name="Python")
        assert "Python" in repr(skill)
        assert "5" in repr(skill)


class TestTestSubmissionModel:
    async def test_create_submission_with_defaults(self, db):
        test = Test(name="FK Test", test_type=TestType.QUIZ)
        db.add(test)
        await db.commit()
        await db.refresh(test)

        sub = TestSubmission(test_id=test.id, user_id=42)
        db.add(sub)
        await db.commit()
        await db.refresh(sub)

        assert sub.id is not None
        assert sub.user_id == 42
        assert sub.status == SubmissionStatus.ASSIGNED
        assert sub.ai_score is None
        assert sub.trainer_score is None
        assert sub.final_score is None

    async def test_assigned_at_auto_set(self, db):
        test = Test(name="TS Test", test_type=TestType.QUIZ)
        db.add(test)
        await db.commit()
        await db.refresh(test)

        sub = TestSubmission(test_id=test.id, user_id=1)
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        assert sub.assigned_at is not None
