from typing import List, Dict, Any
import httpx
import os
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.test_submission_repository import TestSubmissionRepository
from src.repositories.test_repository import TestRepository
from src.services.test_service import TestService
from src.schemas.test_submission_schema import (
    TestSubmissionCreate,
    TestSubmissionUpdate,
    TestSubmissionOut,
    BulkAssignRequest,
    BulkAssignResult,
    TrainerReviewRequest,
    TrainerReviewResponse,
    SubmissionStatus
)
from src.utils.sqs_client import sqs_client
from src.config import settings

logger = logging.getLogger(__name__)

class TestSubmissionService:

    @staticmethod
    async def create_submission(db: AsyncSession, submission_in: TestSubmissionCreate) -> TestSubmissionOut:

        submission = await TestSubmissionRepository.create(db, submission_in)
        # test = await TestService.get_test_by_id(db, submission_in.test_id)
        # if not test:
        #     raise ValueError(f"Test with ID {request.test_id} not found")

        # # Direct service-to-service communication (internal network)
        # user_service_url = settings.USER_SERVICE_URL

        # async with httpx.AsyncClient(timeout=30.0) as client:
        #     try:
        #                 # Check if user exists (direct call to user-service)
        #                 user_response = await client.get(
        #                     f"{user_service_url}/v1/api/users/by-email/{email}"
        #                 )

        #                 if user_response.status_code == 404:
        #                     # User doesn't exist, create and invite (direct call to user-service)
        #                     invite_response = await client.post(
        #                         f"{user_service_url}/v1/api/users/invite",
        #                         json={"email": email}
        #                     )

        #                     if invite_response.status_code not in [200, 201]:
        #                         errors.append({
        #                             "email": email,
        #                             "error": f"Failed to create user and send invite: {invite_response.text}"
        #                         })
        #                         failure_count += 1
        #                         continue

        #                     user_data = invite_response.json()
        #                     user_id = user_data.get("id")
        #                 elif user_response.status_code == 200:
        #                     # User exists
        #                     user_data = user_response.json()
        #                     user_id = user_data.get("id")
        #                 else:
        #                     errors.append({
        #                         "email": email,
        #                         "error": f"Failed to check user existence: {user_response.text}"
        #                     })
        #                     failure_count += 1
        #                     continue

        #                 # Create test submission
        #                 submission_data = TestSubmissionCreate(
        #                     test_id=request.test_id,
        #                     user_id=user_id,
        #                     assigned_by_id=current_user["id"],  # Use authenticated user's database ID from user-service
        #                     due_date=request.due_date
        #                 )

        #                 submission = await TestSubmissionRepository.create(db, submission_data)
        #                 submission_out = TestSubmissionOut.from_orm(submission)
        #                 created_submissions.append(submission_out)
        #                 submission_ids.append(submission.id)
        #                 success_count += 1

        #                 # Publish TEST_ASSIGNED event to SQS (individual event for each participant)
        #                 try:
        #                     test_skills = [ts.name for ts in test.skills] if test.skills else []
        #                     duration_minutes = int(test.duration_seconds / 60) if test.duration_seconds else 60

        #                     logger.info(f"📤 Publishing TEST_ASSIGNED event for {email} (submission_id: {submission.id})")

        #                     sqs_success = await sqs_client.publish_test_assigned_event(
        #                         test_id=test.id,
        #                         test_name=test.name,
        #                         user_id=user_id,
        #                         user_email=email,
        #                         assigned_by_id=current_user["id"],
        #                         submission_id=submission.id,
        #                         assigned_at=submission.assigned_at,  # When the test was assigned
        #                         due_date=request.due_date,
        #                         duration_minutes=duration_minutes,
        #                         skills=test_skills,
        #                         test_details={
        #                             "role": test.role,
        #                             "curriculum": test.curriculum,
        #                             "active": test.active
        #                         }
        #                     )

        #                     if sqs_success:
        #                         logger.info(f"✅ TEST_ASSIGNED event published successfully for {email}")
        #                     else:
        #                         logger.warning(f"⚠️ TEST_ASSIGNED event publishing returned False for {email}")

        #                 except Exception as sqs_error:
        #                     # Don't fail the assignment if SQS publishing fails
        #                     logger.error(f"❌ Exception while publishing TEST_ASSIGNED event for {email}: {str(sqs_error)}")
        #                     import traceback
        #                     logger.error(traceback.format_exc())

        #             except httpx.RequestError as e:
        #                 errors.append({
        #                     "email": email,
        #                     "error": f"Network error contacting user service: {str(e)}"
        #                 })
        #                 failure_count += 1
        #             except Exception as e:
        #                 errors.append({
        #                     "email": email,
        #                     "error": f"Unexpected error: {str(e)}"
        #                 })
        #                 failure_count += 1

        return TestSubmissionOut.from_orm(submission)

    @staticmethod
    async def update_submission(db: AsyncSession, submission_id: int, submission_in: TestSubmissionUpdate) -> TestSubmissionOut:
        submission = await TestSubmissionRepository.get_by_id(db, submission_id)
        if not submission:
            raise ValueError("Submission not found")
        submission = await TestSubmissionRepository.update(db, submission, submission_in)
        return TestSubmissionOut.from_orm(submission)

    @staticmethod
    async def delete_submission(db: AsyncSession, submission_id: int) -> None:
        submission = await TestSubmissionRepository.get_by_id(db, submission_id)
        if not submission:
            raise ValueError("Submission not found")
        await TestSubmissionRepository.delete(db, submission)

    @staticmethod
    async def get_submission_by_id(db: AsyncSession, submission_id: int) -> TestSubmissionOut:
        submission = await TestSubmissionRepository.get_by_id(db, submission_id)
        if not submission:
            raise ValueError("Submission not found")
        return TestSubmissionOut.from_orm(submission)

    @staticmethod
    async def list_all_submissions(db: AsyncSession) -> List[TestSubmissionOut]:
        submissions = await TestSubmissionRepository.list_all(db)
        return [TestSubmissionOut.from_orm(s) for s in submissions]

    @staticmethod
    async def list_submissions_by_user(db: AsyncSession, user_id: int) -> List[TestSubmissionOut]:
        """Get all submissions for a specific user (participant view)"""
        submissions = await TestSubmissionRepository.list_by_user(db, user_id)
        return [TestSubmissionOut.from_orm(s) for s in submissions]

    @staticmethod
    async def bulk_assign_test(db: AsyncSession, request: BulkAssignRequest, current_user: dict) -> BulkAssignResult:
        """
        Bulk assign a test to multiple participants.
        For each email:
        1. Check if user exists (via user-service)
        2. If not, create user and send invite (via user-service)
        3. Create test submission in ASSIGNED status
        4. Publish TEST_ASSIGNED event to SQS

        Args:
            db: Database session
            request: Bulk assignment request with test_id, emails, and due_date
            current_user: Current authenticated user dict (trainer) with database ID from user-service
        """
        created_submissions = []
        errors = []
        success_count = 0
        failure_count = 0
        submission_ids = []

        # Fetch test details first (needed for notifications and SQS events)
        test = await TestService.get_test_by_id(db, request.test_id)
        if not test:
            raise ValueError(f"Test with ID {request.test_id} not found")

        # Direct service-to-service communication (internal network)
        user_service_url = settings.USER_SERVICE_URL

        async with httpx.AsyncClient(timeout=30.0) as client:
            for email in request.participant_emails:
                try:
                    # Check if user exists (direct call to user-service)
                    user_response = await client.get(
                        f"{user_service_url}/v1/api/users/by-email/{email}"
                    )

                    if user_response.status_code == 404:
                        # User doesn't exist, create and invite (direct call to user-service)
                        invite_response = await client.post(
                            f"{user_service_url}/v1/api/users/invite",
                            json={"email": email}
                        )

                        if invite_response.status_code not in [200, 201]:
                            errors.append({
                                "email": email,
                                "error": f"Failed to create user and send invite: {invite_response.text}"
                            })
                            failure_count += 1
                            continue

                        user_data = invite_response.json()
                        user_id = user_data.get("id")
                    elif user_response.status_code == 200:
                        # User exists
                        user_data = user_response.json()
                        user_id = user_data.get("id")
                    else:
                        errors.append({
                            "email": email,
                            "error": f"Failed to check user existence: {user_response.text}"
                        })
                        failure_count += 1
                        continue

                    # Create test submission
                    submission_data = TestSubmissionCreate(
                        test_id=request.test_id,
                        user_id=user_id,
                        assigned_by_id=current_user["id"],  # Use authenticated user's database ID from user-service
                        due_date=request.due_date
                    )

                    submission = await TestSubmissionRepository.create(db, submission_data)
                    submission_out = TestSubmissionOut.from_orm(submission)
                    created_submissions.append(submission_out)
                    submission_ids.append(submission.id)
                    success_count += 1

                    # Publish TEST_ASSIGNED event to SQS (individual event for each participant)
                    try:
                        test_skills = [ts.name for ts in test.skills] if test.skills else []
                        duration_minutes = int(test.duration_seconds / 60) if test.duration_seconds else 60

                        logger.info(f"📤 Publishing TEST_ASSIGNED event for {email} (submission_id: {submission.id})")

                        sqs_success = await sqs_client.publish_test_assigned_event(
                            test_id=test.id,
                            test_name=test.name,
                            user_id=user_id,
                            user_email=email,
                            assigned_by_id=current_user["id"],
                            submission_id=submission.id,
                            assigned_at=submission.assigned_at,  # When the test was assigned
                            due_date=request.due_date,
                            duration_minutes=duration_minutes,
                            skills=test_skills,
                            test_details={
                                "role": test.role,
                                "curriculum": test.curriculum,
                                "active": test.active
                            }
                        )

                        if sqs_success:
                            logger.info(f"✅ TEST_ASSIGNED event published successfully for {email}")
                        else:
                            logger.warning(f"⚠️ TEST_ASSIGNED event publishing returned False for {email}")

                    except Exception as sqs_error:
                        # Don't fail the assignment if SQS publishing fails
                        logger.error(f"❌ Exception while publishing TEST_ASSIGNED event for {email}: {str(sqs_error)}")
                        import traceback
                        logger.error(traceback.format_exc())

                except httpx.RequestError as e:
                    errors.append({
                        "email": email,
                        "error": f"Network error contacting user service: {str(e)}"
                    })
                    failure_count += 1
                except Exception as e:
                    errors.append({
                        "email": email,
                        "error": f"Unexpected error: {str(e)}"
                    })
                    failure_count += 1

        return BulkAssignResult(
            success_count=success_count,
            failure_count=failure_count,
            created_submissions=created_submissions,
            errors=errors
        )

    @staticmethod
    async def get_evaluated_submissions_for_trainer(db: AsyncSession, trainer_id: int) -> List[TestSubmissionOut]:
        """
        Get list of EVALUATED submissions for any trainer to review.

        Returns submissions where:
        - Status is EVALUATED (AI evaluation complete, awaiting trainer review)
        - Any trainer can review any interview (no ownership restriction)
        - Fetch participant names from User Service

        Note: trainer_id parameter is kept for future access control if needed
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from src.models.test_submission import TestSubmission
        from src.models.test import Test

        # Get all EVALUATED submissions (any trainer can review any interview)
        query = (
            select(TestSubmission)
            .options(selectinload(TestSubmission.test))  # Eagerly load test relationship
            .join(Test, TestSubmission.test_id == Test.id)
            .where(TestSubmission.status == SubmissionStatus.EVALUATED)
            .order_by(TestSubmission.submitted_at.desc())
        )

        result = await db.execute(query)
        submissions = result.scalars().all()

        # Fetch participant names from User Service
        user_service_url = settings.USER_SERVICE_URL
        submission_outs = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for submission in submissions:
                submission_out = TestSubmissionOut.from_orm(submission)

                # Fetch participant details
                try:
                    user_response = await client.get(
                        f"{user_service_url}/v1/api/users/{submission.user_id}"
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        # Construct full name from first_name and last_name
                        first_name = user_data.get("first_name", "").strip()
                        last_name = user_data.get("last_name", "").strip()
                        if first_name and last_name:
                            full_name = f"{first_name} {last_name}"
                        elif first_name:
                            full_name = first_name
                        elif last_name:
                            full_name = last_name
                        else:
                            full_name = user_data.get("email", "Unknown")
                        submission_out.participant_name = full_name
                        submission_out.participant_email = user_data.get("email")
                except Exception as e:
                    logger.warning(f"Failed to fetch user {submission.user_id}: {e}")
                    submission_out.participant_name = f"User #{submission.user_id}"

                submission_outs.append(submission_out)

        return submission_outs

    @staticmethod
    async def get_graded_submissions(db: AsyncSession) -> List[TestSubmissionOut]:
        """
        Get list of GRADED submissions (already reviewed by trainer).

        Returns submissions where:
        - Status is GRADED (trainer review complete)
        - Includes trainer_score and final_score
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from src.models.test_submission import TestSubmission
        from src.models.test import Test

        # Get all GRADED submissions
        query = (
            select(TestSubmission)
            .options(selectinload(TestSubmission.test))  # Eagerly load test relationship
            .join(Test, TestSubmission.test_id == Test.id)
            .where(TestSubmission.status == SubmissionStatus.GRADED)
            .order_by(TestSubmission.reviewed_at.desc())
        )

        result = await db.execute(query)
        submissions = result.scalars().all()

        return [TestSubmissionOut.from_orm(s) for s in submissions]

    @staticmethod
    async def get_all_submissions_for_trainer(db: AsyncSession, trainer_id: int) -> List[TestSubmissionOut]:
        """
        Get ALL submissions for tests created by this trainer across all statuses.

        Returns submissions where:
        - Test was created by the authenticated trainer
        - Include statuses: ASSIGNED, IN_PROGRESS, COMPLETED, GRADED, ABANDONED
        - Exclude EVALUATED (those appear in "Pending Review" tab)
        - Include both QUIZ and INTERVIEW test types
        - Eager load test relationship for test_name and test_type
        - Fetch participant names from User Service
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from src.models.test_submission import TestSubmission
        from src.models.test import Test

        # Get all submissions for tests created by this trainer (exclude EVALUATED)
        query = (
            select(TestSubmission)
            .join(Test, TestSubmission.test_id == Test.id)
            .options(selectinload(TestSubmission.test))  # Eager load test relationship
            .where(
                Test.created_by_id == trainer_id,  # Filter by trainer
                TestSubmission.status != SubmissionStatus.EVALUATED  # Exclude EVALUATED
            )
            .order_by(TestSubmission.created_at.desc())  # Most recent first
        )

        result = await db.execute(query)
        submissions = result.scalars().all()

        # Fetch participant names from User Service
        user_service_url = settings.USER_SERVICE_URL
        submission_outs = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for submission in submissions:
                submission_out = TestSubmissionOut.from_orm(submission)

                # Fetch participant details
                try:
                    user_response = await client.get(
                        f"{user_service_url}/v1/api/users/{submission.user_id}"
                    )
                    if user_response.status_code == 200:
                        user_data = user_response.json()
                        # Construct full name from first_name and last_name
                        first_name = user_data.get("first_name", "").strip()
                        last_name = user_data.get("last_name", "").strip()
                        if first_name and last_name:
                            full_name = f"{first_name} {last_name}"
                        elif first_name:
                            full_name = first_name
                        elif last_name:
                            full_name = last_name
                        else:
                            full_name = user_data.get("email", "Unknown")
                        submission_out.participant_name = full_name
                        submission_out.participant_email = user_data.get("email")
                except Exception as e:
                    logger.warning(f"Failed to fetch user {submission.user_id}: {e}")
                    submission_out.participant_name = f"User #{submission.user_id}"

                submission_outs.append(submission_out)

        return submission_outs

    @staticmethod
    async def get_submission_review_details(db: AsyncSession, submission_id: int) -> Dict[str, Any]:
        """
        Get full review details for a submission including:
        - Submission metadata
        - Test information
        - Interview transcript (from MongoDB via interview service)
        - AI evaluation data

        This is used by trainers to review and score interviews.
        """
        # Get submission
        submission = await TestSubmissionRepository.get_by_id(db, submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")

        # Get test details
        test = await TestService.get_test_by_id(db, submission.test_id)
        if not test:
            raise ValueError(f"Test {submission.test_id} not found")

        # Get interview transcript from interview service
        interview_service_url = settings.INTERVIEW_SERVICE_URL
        transcript_data = None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{interview_service_url}/v1/api/interview/submissions/{submission_id}/transcript"
                )

                if response.status_code == 200:
                    transcript_data = response.json()
                else:
                    logger.warning(f"⚠️ Could not fetch transcript for submission {submission_id}: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error fetching transcript for submission {submission_id}: {e}")

        # Build response
        return {
            "submission": TestSubmissionOut.from_orm(submission),
            "test": {
                "id": test.id,
                "name": test.name,
                "test_type": test.test_type,
                "role": test.role,
                "curriculum": test.curriculum,
                "duration_seconds": test.duration_seconds,
                "skills": [{"id": s.id, "name": s.name, "description": s.description} for s in test.skills] if test.skills else []
            },
            "transcript": transcript_data
        }

    @staticmethod
    async def submit_trainer_review(
        db: AsyncSession,
        submission_id: int,
        review: TrainerReviewRequest,
        trainer_id: int
    ) -> TrainerReviewResponse:
        """
        Submit trainer's review and score for a submission.

        Updates:
        - trainer_score: Trainer's score
        - final_score: Set to trainer_score (authoritative)
        - feedback: Trainer's feedback (optional)
        - reviewed_at: Current timestamp
        - reviewed_by_id: Trainer's user ID
        - status: Changed to TRAINER_REVIEWED
        """
        # Get submission
        submission = await TestSubmissionRepository.get_by_id(db, submission_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")

        # Validate that submission is in EVALUATED status
        if submission.status != SubmissionStatus.EVALUATED:
            raise ValueError(
                f"Submission {submission_id} is not in EVALUATED status. "
                f"Current status: {submission.status}"
            )

        # Update submission with trainer review
        now = datetime.now(timezone.utc).replace(tzinfo=None)  # Strip timezone for POC

        update_data = TestSubmissionUpdate(
            trainer_score=review.trainer_score,
            final_score=review.trainer_score,  # Trainer score is authoritative
            feedback=review.feedback,
            status=SubmissionStatus.GRADED
        )

        # Manually set reviewed fields (not in TestSubmissionUpdate schema)
        submission.reviewed_at = now
        submission.reviewed_by_id = trainer_id

        # Update using repository
        updated_submission = await TestSubmissionRepository.update(db, submission, update_data)

        # Save comprehensive trainer evaluation to MongoDB (for interviews)
        # This stores the full evaluation structure alongside AI evaluation
        if review.trainer_evaluation and submission.test.test_type.value == "INTERVIEW":
            interview_service_url = settings.INTERVIEW_SERVICE_URL
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    mongo_response = await client.patch(
                        f"{interview_service_url}/v1/api/interview/submissions/{submission_id}/trainer-evaluation",
                        json={
                            "trainer_evaluation": review.trainer_evaluation,
                            "reviewed_at": now.isoformat(),
                            "reviewed_by_id": trainer_id
                        }
                    )
                    if mongo_response.status_code != 200:
                        logger.warning(
                            f"Failed to save trainer evaluation to MongoDB: {mongo_response.status_code} - {mongo_response.text}"
                        )
            except Exception as e:
                logger.error(f"Error saving trainer evaluation to MongoDB: {str(e)}")
                # Don't fail the request if MongoDB update fails

        return TrainerReviewResponse(
            submission_id=updated_submission.id,
            trainer_score=updated_submission.trainer_score,
            final_score=updated_submission.final_score,
            ai_score=updated_submission.ai_score,
            feedback=updated_submission.feedback,
            reviewed_at=updated_submission.reviewed_at,
            reviewed_by_id=updated_submission.reviewed_by_id,
            status=updated_submission.status
        )
