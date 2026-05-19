from typing import List, Optional
from sqlalchemy.orm import Session

from src.repositories.test_repository import (
    create_test,
    get_test,
    list_tests,
    update_test,
    delete_test,
    add_participant_by_email,
    remove_participant_by_email,
)
from src.schemas.test_schema import TestCreate, TestUpdate


def create_new_test(db: Session, payload: TestCreate):
    return create_test(db, payload)


def get_test_by_id(db: Session, test_id: int):
    return get_test(db, test_id)


def list_all_tests(db: Session, skip: int = 0, limit: int = 100):
    return list_tests(db, skip=skip, limit=limit)


def update_existing_test(db: Session, test_obj, payload: TestUpdate):
    return update_test(db, test_obj, payload)


def delete_existing_test(db: Session, test_obj):
    delete_test(db, test_obj)


def add_participant(db: Session, test_obj, email: str):
    return add_participant_by_email(db, test_obj, email)


def remove_participant(db: Session, test_obj, email: str) -> bool:
    return remove_participant_by_email(db, test_obj, email)