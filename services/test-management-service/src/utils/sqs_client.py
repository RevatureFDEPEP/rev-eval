"""
SQS Client for publishing events to AWS SQS queue.

This module provides functionality to publish events to an AWS SQS queue
for asynchronous processing of test assignments and other notifications.
"""

import json
import boto3
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from botocore.exceptions import ClientError, BotoCoreError
from src.config.settings import settings

logger = logging.getLogger(__name__)


class SQSClient:
    """
    AWS SQS Client for publishing events.

    This client handles the connection to AWS SQS and provides methods
    to publish different types of events with proper error handling.
    """

    _instance: Optional['SQSClient'] = None
    _sqs_client = None
    _is_fifo_queue = False

    def __new__(cls):
        """Singleton pattern to reuse SQS client across requests."""
        if cls._instance is None:
            cls._instance = super(SQSClient, cls).__new__(cls)
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        """Initialize the boto3 SQS client with credentials from settings."""
        try:
            logger.info("🔧 Initializing SQS Client...")
            logger.info(f"   AWS_REGION: {settings.AWS_REGION}")
            logger.info(f"   SQS_ENABLED: {settings.SQS_ENABLED}")
            logger.info(f"   SQS_QUEUE_URL: {settings.SQS_QUEUE_URL[:50] + '...' if settings.SQS_QUEUE_URL and len(settings.SQS_QUEUE_URL) > 50 else settings.SQS_QUEUE_URL or 'NOT SET'}")
            logger.info(f"   AWS_ACCESS_KEY_ID: {'SET' if settings.AWS_ACCESS_KEY_ID else 'NOT SET'}")
            logger.info(f"   AWS_SECRET_ACCESS_KEY: {'SET' if settings.AWS_SECRET_ACCESS_KEY else 'NOT SET'}")

            # Detect queue type from URL
            self._is_fifo_queue = settings.SQS_QUEUE_URL and settings.SQS_QUEUE_URL.endswith('.fifo')
            logger.info(f"   Queue Type: {'FIFO' if self._is_fifo_queue else 'Standard'}")

            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self._sqs_client = boto3.client(
                    'sqs',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info(f"✅ SQS Client initialized with explicit credentials for region: {settings.AWS_REGION}")
            else:
                # Use default AWS credentials chain (IAM role, env vars, etc.)
                self._sqs_client = boto3.client(
                    'sqs',
                    region_name=settings.AWS_REGION
                )
                logger.info(f"✅ SQS Client initialized with default credentials chain for region: {settings.AWS_REGION}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQS client: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self._sqs_client = None
            self._is_fifo_queue = False

    def _serialize_datetime(self, obj: Any) -> Any:
        """Helper to serialize datetime objects to ISO format strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def verify_connection(self) -> bool:
        """
        Verify that the SQS client can connect to the queue.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        if not settings.SQS_ENABLED:
            logger.info("🔍 SQS verification skipped - SQS_ENABLED is False")
            return False

        if not self._sqs_client:
            logger.error("🔍 SQS verification failed - client not initialized")
            return False

        if not settings.SQS_QUEUE_URL:
            logger.error("🔍 SQS verification failed - SQS_QUEUE_URL not configured")
            return False

        try:
            logger.info("🔍 Verifying SQS connection...")
            # Try to get queue attributes to verify connectivity
            response = self._sqs_client.get_queue_attributes(
                QueueUrl=settings.SQS_QUEUE_URL,
                AttributeNames=['QueueArn', 'ApproximateNumberOfMessages']
            )

            queue_arn = response.get('Attributes', {}).get('QueueArn', 'Unknown')
            message_count = response.get('Attributes', {}).get('ApproximateNumberOfMessages', '0')

            logger.info(f"✅ SQS connection verified successfully!")
            logger.info(f"   Queue ARN: {queue_arn}")
            logger.info(f"   Messages in queue: {message_count}")
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"❌ SQS connection verification failed")
            logger.error(f"   Error Code: {error_code}")
            logger.error(f"   Error Message: {error_message}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during SQS verification: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def publish_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        message_group_id: Optional[str] = None,
        deduplication_id: Optional[str] = None
    ) -> bool:
        """
        Publish an event to the SQS queue.

        Args:
            event_type: Type of event (e.g., 'TEST_ASSIGNED', 'TEST_COMPLETED')
            event_data: Dictionary containing event payload
            message_group_id: Required for FIFO queues
            deduplication_id: Optional deduplication ID for FIFO queues

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        logger.info(f"📤 Attempting to publish event: {event_type}")

        if not settings.SQS_ENABLED:
            logger.warning(f"📭 SQS is DISABLED in settings, skipping event: {event_type}")
            return False

        if not self._sqs_client:
            logger.error(f"❌ SQS client not initialized - cannot publish {event_type}")
            return False

        if not settings.SQS_QUEUE_URL:
            logger.error(f"❌ SQS_QUEUE_URL not configured - cannot publish {event_type}")
            return False

        try:
            # Prepare message body
            message_body = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": event_data
            }

            # Convert message to JSON
            message_json = json.dumps(message_body, default=self._serialize_datetime)
            logger.debug(f"📝 Message body prepared (size: {len(message_json)} bytes)")

            # Prepare send message parameters
            send_params = {
                "QueueUrl": settings.SQS_QUEUE_URL,
                "MessageBody": message_json,
                "MessageAttributes": {
                    "EventType": {
                        "StringValue": event_type,
                        "DataType": "String"
                    }
                }
            }

            # Add FIFO-specific parameters ONLY for FIFO queues
            if self._is_fifo_queue:
                if message_group_id:
                    send_params["MessageGroupId"] = message_group_id
                    logger.debug(f"   MessageGroupId: {message_group_id}")
                else:
                    # FIFO queues require MessageGroupId, use default if not provided
                    send_params["MessageGroupId"] = "default"
                    logger.debug(f"   MessageGroupId: default (auto-assigned)")

                if deduplication_id:
                    send_params["MessageDeduplicationId"] = deduplication_id
                    logger.debug(f"   DeduplicationId: {deduplication_id}")
            else:
                logger.debug(f"   Standard queue - skipping FIFO parameters")

            logger.info(f"📨 Sending message to SQS queue: {settings.SQS_QUEUE_URL[:50]}...")

            # Send message to SQS (boto3 is synchronous)
            response = self._sqs_client.send_message(**send_params)

            # Verify response
            message_id = response.get("MessageId")
            sequence_number = response.get("SequenceNumber")
            md5_of_body = response.get("MD5OfMessageBody")

            logger.info(f"✅ Event published to SQS successfully!")
            logger.info(f"   Event Type: {event_type}")
            logger.info(f"   Message ID: {message_id}")
            if sequence_number:
                logger.info(f"   Sequence Number: {sequence_number}")
            logger.info(f"   MD5 Hash: {md5_of_body}")
            logger.info(f"   Queue URL: {settings.SQS_QUEUE_URL[:50]}...")

            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"❌ AWS ClientError publishing event {event_type}")
            logger.error(f"   Error Code: {error_code}")
            logger.error(f"   Error Message: {error_message}")
            logger.error(f"   Queue URL: {settings.SQS_QUEUE_URL}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        except BotoCoreError as e:
            logger.error(f"❌ BotoCoreError publishing event {event_type}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error publishing event {event_type}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def publish_test_assigned_event(
        self,
        test_id: int,
        test_name: str,
        user_id: int,
        user_email: str,
        assigned_by_id: int,
        submission_id: int,
        assigned_at: datetime,
        due_date: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        skills: Optional[List[str]] = None,
        test_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Publish a TEST_ASSIGNED event when a test is assigned to a participant.

        Args:
            test_id: ID of the test
            test_name: Name of the test
            user_id: ID of the user (participant)
            user_email: Email of the participant
            assigned_by_id: ID of the user who assigned the test (trainer)
            submission_id: ID of the created test submission
            assigned_at: When the test was assigned (start date)
            due_date: Optional due date for test completion
            duration_minutes: Test duration in minutes
            skills: List of skills being tested
            test_details: Optional additional test details (role, curriculum, etc.)

        Returns:
            bool: True if event was published successfully
        """
        event_data = {
            "test_id": test_id,
            "test_name": test_name,
            "user_id": user_id,
            "user_email": user_email,
            "assigned_by_id": assigned_by_id,
            "submission_id": submission_id,
            "assigned_at": assigned_at.isoformat(),
            "due_date": due_date.isoformat() if due_date else None,
            "duration_minutes": duration_minutes,
            "skills": skills or [],
        }

        # Add optional test details if provided
        if test_details:
            event_data.update(test_details)

        # Use submission_id as deduplication ID to prevent duplicate events
        deduplication_id = f"test_assigned_{submission_id}_{int(datetime.utcnow().timestamp())}"

        # Use test_id as message group ID for FIFO ordering
        message_group_id = f"test_{test_id}"

        return await self.publish_event(
            event_type="TEST_ASSIGNED",
            event_data=event_data,
            message_group_id=message_group_id,
            deduplication_id=deduplication_id
        )
# Singleton instance
sqs_client = SQSClient()
