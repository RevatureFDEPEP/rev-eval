"""
SQS Consumer for polling and processing events from AWS SQS queue.

This module provides functionality to continuously poll an SQS queue,
process different event types, and handle message lifecycle.
"""

import json
import boto3
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime

from src.config.settings import settings

logger = logging.getLogger(__name__)


class SQSConsumer:
    """
    AWS SQS Consumer for polling and processing events.

    This consumer handles long-polling from SQS, message processing,
    and proper message deletion after successful handling.
    """

    def __init__(self):
        """Initialize the SQS consumer with boto3 client."""
        self._sqs_client = None
        self._event_handlers: Dict[str, Callable] = {}
        self._is_running = False
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the boto3 SQS client with credentials from settings."""
        try:
            logger.info("🔧 Initializing SQS Consumer...")
            logger.info(f"   AWS_REGION: {settings.AWS_REGION}")
            logger.info(f"   SQS_ENABLED: {settings.SQS_ENABLED}")
            logger.info(f"   SQS_QUEUE_URL: {settings.SQS_QUEUE_URL[:50] + '...' if settings.SQS_QUEUE_URL and len(settings.SQS_QUEUE_URL) > 50 else settings.SQS_QUEUE_URL or 'NOT SET'}")

            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self._sqs_client = boto3.client(
                    'sqs',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info(f"✅ SQS Consumer initialized with explicit credentials")
            else:
                # Use default AWS credentials chain (IAM role, env vars, etc.)
                self._sqs_client = boto3.client(
                    'sqs',
                    region_name=settings.AWS_REGION
                )
                logger.info(f"✅ SQS Consumer initialized with default credentials chain")
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQS consumer: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self._sqs_client = None

    def register_handler(self, event_type: str, handler: Callable):
        """
        Register an event handler for a specific event type.

        Args:
            event_type: Type of event (e.g., 'TEST_ASSIGNED')
            handler: Async function to handle the event
        """
        self._event_handlers[event_type] = handler
        logger.info(f"📝 Registered handler for event type: {event_type}")

    def verify_connection(self) -> bool:
        """
        Verify that the SQS consumer can connect to the queue.

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

    async def _process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process a single SQS message.

        Args:
            message: SQS message dictionary

        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Parse message body
            body = json.loads(message['Body'])
            event_type = body.get('event_type')
            event_data = body.get('data', {})
            timestamp = body.get('timestamp')

            logger.info(f"📨 Processing message: {event_type}")
            logger.info(f"   Message ID: {message['MessageId']}")
            logger.info(f"   Timestamp: {timestamp}")

            # Find and execute handler
            handler = self._event_handlers.get(event_type)
            if handler:
                logger.info(f"🎯 Found handler for event type: {event_type}")
                await handler(event_data)
                logger.info(f"✅ Successfully processed {event_type} event")
                return True
            else:
                logger.warning(f"⚠️  No handler registered for event type: {event_type}")
                # Still return True to delete message (avoid reprocessing unknown events)
                return True

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse message JSON: {str(e)}")
            logger.error(f"   Message Body: {message.get('Body', '')[:200]}")
            return False
        except Exception as e:
            logger.error(f"❌ Error processing message: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def _poll_once(self) -> int:
        """
        Poll the SQS queue once and process available messages.

        Returns:
            int: Number of messages processed
        """
        if not self._sqs_client or not settings.SQS_QUEUE_URL:
            return 0

        try:
            # Receive messages from SQS (long polling)
            response = self._sqs_client.receive_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MaxNumberOfMessages=settings.SQS_MAX_MESSAGES,
                WaitTimeSeconds=settings.SQS_WAIT_TIME_SECONDS,
                VisibilityTimeout=settings.SQS_VISIBILITY_TIMEOUT,
                MessageAttributeNames=['All']
            )

            messages = response.get('Messages', [])

            if not messages:
                logger.debug("📭 No messages in queue")
                return 0

            logger.info(f"📬 Received {len(messages)} message(s) from SQS")

            processed_count = 0
            for message in messages:
                # Process message
                success = await self._process_message(message)

                if success:
                    # Delete message from queue after successful processing
                    try:
                        self._sqs_client.delete_message(
                            QueueUrl=settings.SQS_QUEUE_URL,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        logger.info(f"🗑️  Deleted message {message['MessageId']} from queue")
                        processed_count += 1
                    except Exception as delete_error:
                        logger.error(f"❌ Failed to delete message {message['MessageId']}: {str(delete_error)}")
                else:
                    logger.warning(f"⚠️  Message {message['MessageId']} processing failed, will retry later")

            return processed_count

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"❌ AWS ClientError while polling SQS")
            logger.error(f"   Error Code: {error_code}")
            logger.error(f"   Error Message: {error_message}")
            return 0
        except BotoCoreError as e:
            logger.error(f"❌ BotoCoreError while polling SQS: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"❌ Unexpected error while polling SQS: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return 0

    async def start_polling(self):
        """
        Start the continuous polling loop.
        This should be run in a background task.
        """
        if not settings.SQS_ENABLED:
            logger.info("🛑 SQS polling disabled (SQS_ENABLED=False)")
            return

        if not self._sqs_client or not settings.SQS_QUEUE_URL:
            logger.error("🛑 Cannot start polling - SQS not properly configured")
            return

        # Verify connection before starting
        if not self.verify_connection():
            logger.error("🛑 SQS connection verification failed - polling not started")
            return

        self._is_running = True
        logger.info("🚀 Starting SQS polling loop...")
        logger.info(f"   Queue URL: {settings.SQS_QUEUE_URL[:50]}...")
        logger.info(f"   Polling Interval: {settings.SQS_POLLING_INTERVAL}s")
        logger.info(f"   Max Messages per Poll: {settings.SQS_MAX_MESSAGES}")
        logger.info(f"   Long Polling Wait Time: {settings.SQS_WAIT_TIME_SECONDS}s")

        total_processed = 0
        poll_count = 0

        while self._is_running:
            try:
                poll_count += 1
                logger.debug(f"📡 Poll #{poll_count} starting...")

                processed = await self._poll_once()
                total_processed += processed

                if processed > 0:
                    logger.info(f"📊 Statistics: Processed {processed} messages (Total: {total_processed})")

                # Small delay between polls (long polling already provides wait)
                await asyncio.sleep(settings.SQS_POLLING_INTERVAL)

            except asyncio.CancelledError:
                logger.info("🛑 SQS polling cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in polling loop: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # Wait before retrying to avoid tight error loop
                await asyncio.sleep(10)

        logger.info(f"🏁 SQS polling stopped. Total messages processed: {total_processed}")

    def stop_polling(self):
        """Stop the polling loop."""
        logger.info("🛑 Stopping SQS polling...")
        self._is_running = False


# Singleton instance
sqs_consumer = SQSConsumer()
