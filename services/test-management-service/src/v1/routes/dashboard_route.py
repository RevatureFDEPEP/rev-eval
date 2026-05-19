"""
Dashboard Statistics Endpoints

Provides aggregated statistics for trainer and participant dashboards.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from src.db.session import get_db
from src.models.test import Test, TestType
from src.models.test_submission import TestSubmission, SubmissionStatus
from src.models.user import User, UserRole
from src.schemas.test_schema import (
    TrainerDashboardStats,
    ParticipantDashboardStats,
    AssignedTestInfo
)
from typing import Optional, List
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


def get_user_context(
    x_user_id: Optional[str] = Header(None),
    x_user_email: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None)
):
    """Extract user context from headers set by API Gateway"""
    if not x_user_email or not x_user_role:
        raise HTTPException(status_code=401, detail="User context not found in headers")

    return {
        "user_id": x_user_id,
        "email": x_user_email,
        "role": x_user_role
    }


# @router.get("/dashboard/trainer/stats", response_model=TrainerDashboardStats)
# def get_trainer_dashboard_stats(
#     db: Session = Depends(get_db),
#     user_context: dict = Depends(get_user_context)
# ):
#     """
#     Get dashboard statistics for trainers.

#     Returns:
#         - active_tests_count: Number of active tests created by this trainer
#         - total_participants_count: Number of unique participants assigned to trainer's tests
#         - pending_submissions_count: Number of submissions awaiting completion
#         - quiz_tests_count: Number of QUIZ tests
#         - interview_tests_count: Number of INTERVIEW tests
#         - total_submissions: Total submissions made
#         - completed_submissions: Number of completed submissions
#     """
#     trainer_email = user_context["email"]
#     logger.info(f"📊 Getting trainer dashboard stats for: {trainer_email}")

#     # Get trainer user
#     trainer = db.query(User).filter(User.email == trainer_email).first()
#     if not trainer:
#         logger.warning(f"⚠️ Trainer not found: {trainer_email}")
#         # Return empty stats
#         return TrainerDashboardStats(
#             active_tests_count=0,
#             total_participants_count=0,
#             pending_submissions_count=0,
#             quiz_tests_count=0,
#             interview_tests_count=0,
#             total_submissions=0,
#             completed_submissions=0
#         )

#     # Get tests created by this trainer
#     trainer_tests = db.query(Test).filter(
#         Test.created_by == trainer.id,
#         Test.active == True
#     ).all()

#     trainer_test_ids = [t.id for t in trainer_tests]
#     logger.info(f"📝 Found {len(trainer_tests)} active tests for trainer")

#     # Active tests count
#     active_tests_count = len(trainer_tests)

#     # Count tests by type
#     quiz_tests_count = sum(1 for t in trainer_tests if t.test_type == TestType.QUIZ)
#     interview_tests_count = sum(1 for t in trainer_tests if t.test_type == TestType.INTERVIEW)
#     logger.info(f"📊 Test types - QUIZ: {quiz_tests_count}, INTERVIEW: {interview_tests_count}")

#     # Get all submissions for trainer's tests
#     submissions = db.query(TestSubmission).filter(
#         TestSubmission.test_id.in_(trainer_test_ids)
#     ).all() if trainer_test_ids else []

#     total_submissions = len(submissions)
#     pending_submissions_count = sum(
#         1 for s in submissions if s.status == SubmissionStatus.ASSIGNED
#     )
#     completed_submissions = sum(
#         1 for s in submissions if s.status == SubmissionStatus.COMPLETED
#     )
#     logger.info(f"📈 Submissions - Total: {total_submissions}, Pending: {pending_submissions_count}, Completed: {completed_submissions}")

#     # Get unique participants count (user_id instead of participant_id)
#     unique_user_ids = set(s.user_id for s in submissions)
#     total_participants_count = len(unique_user_ids)
#     logger.info(f"👥 Unique participants: {total_participants_count}")

#     stats = TrainerDashboardStats(
#         active_tests_count=active_tests_count,
#         total_participants_count=total_participants_count,
#         pending_submissions_count=pending_submissions_count,
#         quiz_tests_count=quiz_tests_count,
#         interview_tests_count=interview_tests_count,
#         total_submissions=total_submissions,
#         completed_submissions=completed_submissions
#     )

#     logger.info(f"✅ Returning trainer stats: {stats}")
#     return stats


# @router.get("/dashboard/participant/stats", response_model=ParticipantDashboardStats)
# def get_participant_dashboard_stats(
#     db: Session = Depends(get_db),
#     user_context: dict = Depends(get_user_context)
# ):
#     """
#     Get dashboard statistics for participants.

#     Returns:
#         - assigned_tests_count: Total tests assigned to this participant
#         - completed_tests_count: Tests completed by this participant
#         - in_progress_tests_count: Tests currently in progress
#         - average_score: Average score across completed tests
#         - tests_due_this_week: Number of tests due within 7 days
#     """
#     participant_email = user_context["email"]
#     logger.info(f"📊 Getting participant dashboard stats for: {participant_email}")

#     # Get user by email
#     user = db.query(User).filter(User.email == participant_email).first()

#     if not user:
#         logger.warning(f"⚠️ User not found for email: {participant_email}")
#         # Return empty stats if user doesn't exist yet
#         return ParticipantDashboardStats(
#             assigned_tests_count=0,
#             completed_tests_count=0,
#             in_progress_tests_count=0,
#             average_score=None,
#             tests_due_this_week=0
#         )

#     logger.info(f"👤 Found user: {participant_email}")

#     # Get all submissions for this user (no Participant model anymore)
#     submissions = db.query(TestSubmission).filter(
#         TestSubmission.user_id == user.id
#     ).all()

#     assigned_tests_count = len(submissions)
#     completed_tests_count = sum(
#         1 for s in submissions if s.status == SubmissionStatus.COMPLETED
#     )
#     in_progress_tests_count = sum(
#         1 for s in submissions if s.status == SubmissionStatus.IN_PROGRESS
#     )

#     logger.info(f"📈 Participant submissions - Total: {assigned_tests_count}, Completed: {completed_tests_count}, In Progress: {in_progress_tests_count}")

#     # Calculate average score from completed tests
#     completed_with_scores = [s for s in submissions if s.status == SubmissionStatus.COMPLETED and s.final_score is not None]
#     average_score = (
#         sum(s.final_score for s in completed_with_scores) / len(completed_with_scores)
#         if completed_with_scores else None
#     )

#     # Tests due this week (within 7 days from now)
#     now = datetime.utcnow()
#     week_from_now = now + timedelta(days=7)

#     tests_due_this_week = sum(
#         1 for s in submissions
#         if s.due_date and now <= s.due_date <= week_from_now
#         and s.status != SubmissionStatus.COMPLETED
#     )

#     logger.info(f"📅 Tests due this week: {tests_due_this_week}, Average score: {average_score}")

#     stats = ParticipantDashboardStats(
#         assigned_tests_count=assigned_tests_count,
#         completed_tests_count=completed_tests_count,
#         in_progress_tests_count=in_progress_tests_count,
#         average_score=average_score,
#         tests_due_this_week=tests_due_this_week
#     )
    
#     logger.info(f"✅ Returning participant stats: {stats}")
#     return stats


# @router.get("/dashboard/participant/assigned-tests", response_model=List[AssignedTestInfo])
# def get_assigned_tests(
#     db: Session = Depends(get_db),
#     user_context: dict = Depends(get_user_context)
# ):
#     """
#     Get list of all tests assigned to the current participant.

#     Returns detailed information about each assigned test including:
#     - Test metadata (name, type, duration)
#     - Assignment details (assigned date, due date, status)
#     - Score (if completed)
#     """
#     participant_email = user_context["email"]

#     # Get user by email
#     user = db.query(User).filter(User.email == participant_email).first()

#     if not user:
#         return []

#     # Get all submissions with test details
#     submissions_with_tests = db.query(
#         TestSubmission, Test
#     ).join(
#         Test, TestSubmission.test_id == Test.id
#     ).filter(
#         TestSubmission.user_id == user.id
#     ).all()

#     # Build response
#     assigned_tests = []
#     for submission, test in submissions_with_tests:
#         assigned_tests.append(AssignedTestInfo(
#             submission_id=submission.id,
#             test_id=test.id,
#             test_name=test.name,
#             test_type=test.test_type,
#             duration_seconds=int(test.duration.total_seconds()) if test.duration else None,
#             assigned_at=submission.assigned_at,
#             due_date=submission.due_date,
#             status=submission.status,
#             final_score=submission.final_score
#         ))

#     # Sort by due date (earliest first), then by assigned date
#     assigned_tests.sort(
#         key=lambda x: (
#             x.due_date if x.due_date else datetime.max,
#             x.assigned_at
#         )
#     )

#     return assigned_tests


# @router.get("/dashboard/trainer/tests", response_model=List[dict])
# def get_trainer_tests(
#     db: Session = Depends(get_db),
#     user_context: dict = Depends(get_user_context)
# ):
#     """
#     Get list of all tests created by the current trainer with submission counts.
#     """
#     trainer_email = user_context["email"]

#     # Get trainer user
#     trainer = db.query(User).filter(User.email == trainer_email).first()

#     if not trainer:
#         return []

#     # Get all tests by trainer
#     tests = db.query(Test).filter(
#         Test.created_by == trainer.id
#     ).order_by(Test.created_at.desc()).all()

#     # For each test, get submission stats
#     result = []
#     for test in tests:
#         submissions = db.query(TestSubmission).filter(
#             TestSubmission.test_id == test.id
#         ).all()

#         result.append({
#             "id": test.id,
#             "name": test.name,
#             "test_type": test.test_type.value,
#             "active": test.active,
#             "created_at": test.created_at,
#             "duration_seconds": int(test.duration.total_seconds()) if test.duration else None,
#             "total_submissions": len(submissions),
#             "completed_submissions": sum(1 for s in submissions if s.status == SubmissionStatus.COMPLETED),
#             "pending_submissions": sum(1 for s in submissions if s.status == SubmissionStatus.ASSIGNED)
#         })

#     return result
