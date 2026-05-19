"""
Email Service

Handles email sending via Amazon SES and logging.
"""
import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session
import logging
import json
from typing import Optional, Dict, Any

from src.config.settings import settings
from src.models.email_log import EmailLog

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Amazon SES"""

    def __init__(self):
        """Initialize SES client"""
        self.ses_client = None
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                self.ses_client = boto3.client(
                    'ses',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info(f"✅ SES client initialized for region: {settings.AWS_REGION}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize SES client: {str(e)}")
        else:
            logger.warning("⚠️  AWS credentials not configured. Email sending will be simulated.")

    def send_email(
        self,
        db: Session,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        template_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send an email via SES and log the result.

        Args:
            db: Database session
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML version of email body
            text_content: Plain text version (optional, falls back to stripping HTML)
            template_name: Name of template used (for logging)
            context: Template context data (for logging)

        Returns:
            Dict with success status, message_id, and log_id
        """
        # Default text content if not provided
        if not text_content:
            # Simple HTML stripping for plain text fallback
            import re
            text_content = re.sub('<[^<]+?>', '', html_content)

        # Prepare email log entry
        email_log = EmailLog(
            recipient_email=to_email,
            subject=subject,
            template_name=template_name,
            status='pending',
            context_data=json.dumps(context) if context else None
        )

        try:
            if not self.ses_client:
                # Simulate email sending in development
                logger.info(f"📧 [SIMULATED] Email to: {to_email}")
                logger.info(f"   Subject: {subject}")
                logger.info(f"   Template: {template_name or 'custom'}")

                email_log.status = 'sent'
                email_log.ses_message_id = f"simulated-{to_email}-{subject[:20]}"
                db.add(email_log)
                db.commit()
                db.refresh(email_log)

                return {
                    "success": True,
                    "message_id": email_log.ses_message_id,
                    "log_id": email_log.id,
                    "simulated": True
                }

            # Send via SES
            response = self.ses_client.send_email(
                Source=f"{settings.SES_SENDER_NAME} <{settings.SES_SENDER_EMAIL}>",
                Destination={
                    'ToAddresses': [to_email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_content,
                            'Charset': 'UTF-8'
                        },
                        'Text': {
                            'Data': text_content,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )

            # Extract message ID from response
            message_id = response.get('MessageId')

            # Update log with success
            email_log.status = 'sent'
            email_log.ses_message_id = message_id
            db.add(email_log)
            db.commit()
            db.refresh(email_log)

            logger.info(f"✅ Email sent successfully to {to_email}. Message ID: {message_id}")

            return {
                "success": True,
                "message_id": message_id,
                "log_id": email_log.id
            }

        except ClientError as e:
            error_message = e.response['Error']['Message']
            logger.error(f"❌ SES ClientError sending email to {to_email}: {error_message}")

            # Log the failure
            email_log.status = 'failed'
            email_log.error_message = error_message
            db.add(email_log)
            db.commit()
            db.refresh(email_log)

            return {
                "success": False,
                "error_message": error_message,
                "log_id": email_log.id
            }

        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Unexpected error sending email to {to_email}: {error_message}")

            # Log the failure
            email_log.status = 'failed'
            email_log.error_message = error_message
            db.add(email_log)
            db.commit()
            db.refresh(email_log)

            return {
                "success": False,
                "error_message": error_message,
                "log_id": email_log.id
            }

    def get_email_logs(
        self,
        db: Session,
        recipient_email: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[EmailLog]:
        """
        Retrieve email logs with optional filters.

        Args:
            db: Database session
            recipient_email: Filter by recipient email
            status: Filter by status ('sent', 'failed', 'bounced', 'complained')
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of EmailLog objects
        """
        query = db.query(EmailLog)

        if recipient_email:
            query = query.filter(EmailLog.recipient_email == recipient_email)

        if status:
            query = query.filter(EmailLog.status == status)

        query = query.order_by(EmailLog.sent_at.desc())
        query = query.limit(limit).offset(offset)

        return query.all()


# Singleton instance
email_service = EmailService()
