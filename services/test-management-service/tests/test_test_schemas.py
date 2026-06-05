import pytest
from pydantic import ValidationError

from src.models.test import TestType
from src.schemas.test_schema import TestCreate, TestUpdate

# --- TestType enum ---


def test_test_type_quiz_value():
    assert TestType.QUIZ == "QUIZ"


def test_test_type_interview_value():
    assert TestType.INTERVIEW == "INTERVIEW"


# --- TestCreate ---


def test_test_create_valid():
    t = TestCreate(name="Python Basics", test_type=TestType.QUIZ)
    assert t.name == "Python Basics"
    assert t.test_type == TestType.QUIZ


def test_test_create_name_required():
    with pytest.raises(ValidationError):
        TestCreate(test_type=TestType.QUIZ)


def test_test_create_type_required():
    with pytest.raises(ValidationError):
        TestCreate(name="Docker Exam")


def test_test_create_default_number_of_questions():
    t = TestCreate(name="Docker Exam", test_type=TestType.INTERVIEW)
    assert t.number_of_questions == 20


def test_test_create_default_active_true():
    t = TestCreate(name="Docker Exam", test_type=TestType.INTERVIEW)
    assert t.active is True


def test_test_create_empty_skill_ids_by_default():
    t = TestCreate(name="Docker Exam", test_type=TestType.QUIZ)
    assert t.skill_ids == []


def test_test_create_with_skill_ids():
    t = TestCreate(name="Docker Exam", test_type=TestType.QUIZ, skill_ids=[1, 2, 3])
    assert t.skill_ids == [1, 2, 3]


def test_test_create_invalid_type_raises():
    with pytest.raises(ValidationError):
        TestCreate(name="Docker Exam", test_type="INVALID")


# --- TestUpdate ---


def test_test_update_all_optional():
    u = TestUpdate()
    assert u.name is None
    assert u.test_type is None
    assert u.active is None


def test_test_update_partial_name():
    u = TestUpdate(name="Renamed Test")
    assert u.name == "Renamed Test"
    assert u.test_type is None


def test_test_update_partial_active():
    u = TestUpdate(active=False)
    assert u.active is False
    assert u.name is None
