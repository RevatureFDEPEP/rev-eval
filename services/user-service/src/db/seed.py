# src/db/seed.py
"""
Demo-user seeding for local development.

user-service owns the `users` table, so it owns seeding it too (the demo
tests/skills/submissions for test-management-service are seeded by that
service's Alembic data migration, which depends on these users existing —
compose ordering: test-management-service waits for this service's
healthcheck, which only passes after the startup event has run).
"""
import logging

from src.db.session import SessionLocal
from src.models.user import User, UserRole
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# All seeded users share this password — local dev convenience only.
DEV_PASSWORD = "password123"

DEMO_USERS = [
    # (email, full_name, first_name, last_name, role)
    ("trainer1@revature.com", "John Trainer", "John", "Trainer", UserRole.TRAINER),
    ("trainer2@revature.com", "Sarah Instructor", "Sarah", "Instructor", UserRole.TRAINER),
    ("student1@revature.com", "Alice Johnson", "Alice", "Johnson", UserRole.PARTICIPANT),
    ("student2@revature.com", "Bob Smith", "Bob", "Smith", UserRole.PARTICIPANT),
    ("student3@revature.com", "Carol Davis", "Carol", "Davis", UserRole.PARTICIPANT),
    ("student4@revature.com", "David Wilson", "David", "Wilson", UserRole.PARTICIPANT),
    ("student5@revature.com", "Eva Brown", "Eva", "Brown", UserRole.PARTICIPANT),
]


def seed_users() -> int:
    """
    Insert the demo users if the table is empty. Idempotent: a non-empty
    users table (including pre-existing dev volumes) is left untouched.

    Returns the number of users inserted.
    """
    db = SessionLocal()
    try:
        existing = db.query(User).count()
        if existing > 0:
            logger.info("Users table already has %d users, skipping seed.", existing)
            return 0

        # bcrypt is slow by design — hash the shared dev password once.
        password_hash = AuthService.hash_password(DEV_PASSWORD)
        db.add_all(
            User(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                role=role,
                is_active=True,
            )
            for email, full_name, first_name, last_name, role in DEMO_USERS
        )
        db.commit()
        logger.info(
            "Seeded %d demo users (shared dev password: %r).",
            len(DEMO_USERS),
            DEV_PASSWORD,
        )
        return len(DEMO_USERS)
    except Exception:
        db.rollback()
        # Seeding is a dev convenience — never block service startup on it.
        logger.error("User seeding failed!", exc_info=True)
        return 0
    finally:
        db.close()
