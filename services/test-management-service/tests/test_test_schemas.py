import pytest
from pydantic import ValidationError

from src.models.test import TestType
from src.schemas.skill_schema import SkillCreate, SkillUpdate
from src.schemas.test_schema import TestCreate, TestUpdate


class TestTestCreate:
    def test_valid_quiz(self):
        test = TestCreate(name="Python Basics", test_type=TestType.QUIZ)
        assert test.name == "Python Basics"
        assert test.test_type == TestType.QUIZ
        assert test.number_of_questions == 20
        assert test.active is True

    def test_valid_interview(self):
        test = TestCreate(name="Tech Interview", test_type=TestType.INTERVIEW)
        assert test.test_type == TestType.INTERVIEW

    def test_default_skill_ids_empty(self):
        test = TestCreate(name="My Test", test_type=TestType.QUIZ)
        assert test.skill_ids == []

    def test_explicit_skill_ids(self):
        test = TestCreate(name="My Test", test_type=TestType.QUIZ, skill_ids=[1, 2, 3])
        assert test.skill_ids == [1, 2, 3]

    @pytest.mark.parametrize("test_type", list(TestType))
    def test_all_test_types_valid(self, test_type):
        test = TestCreate(name="Test", test_type=test_type)
        assert test.test_type == test_type

    def test_with_optional_metadata(self):
        test = TestCreate(
            name="Java Assessment",
            test_type=TestType.QUIZ,
            role="Junior Developer",
            curriculum="Java Basics",
            duration_seconds=2700,
            number_of_questions=15,
            active=False,
        )
        assert test.role == "Junior Developer"
        assert test.duration_seconds == 2700
        assert test.active is False


class TestTestUpdate:
    def test_all_optional(self):
        update = TestUpdate()
        assert update.name is None
        assert update.test_type is None
        assert update.active is None
        assert update.skill_ids is None

    def test_partial_name_update(self):
        update = TestUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.test_type is None

    def test_deactivate(self):
        update = TestUpdate(active=False)
        assert update.active is False

    def test_update_skill_ids(self):
        update = TestUpdate(skill_ids=[5, 10])
        assert update.skill_ids == [5, 10]


class TestSkillSchemas:
    def test_skill_create_name_only(self):
        skill = SkillCreate(name="Python")
        assert skill.name == "Python"
        assert skill.description is None

    def test_skill_create_with_description(self):
        skill = SkillCreate(name="Python", description="Python programming")
        assert skill.description == "Python programming"

    def test_skill_update_all_optional(self):
        update = SkillUpdate()
        assert update.name is None
        assert update.description is None

    def test_skill_update_partial(self):
        update = SkillUpdate(description="Updated description")
        assert update.description == "Updated description"
        assert update.name is None
