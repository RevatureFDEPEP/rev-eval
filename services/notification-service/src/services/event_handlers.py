"""
Event Handlers for SQS Events

This module contains handlers for different event types received from SQS.
Each handler processes the event and triggers appropriate notifications via SES.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from src.services.email_service import email_service
from src.db.session import SessionLocal
from src.config.settings import settings

logger = logging.getLogger(__name__)


async def handle_test_assigned_event(event_data: Dict[str, Any]):
    """
    Handle TEST_ASSIGNED event.

    Sends an email notification via SES to the participant when a test is assigned.

    Event data structure:
    {
        "test_id": int,
        "test_name": str,
        "user_id": int,
        "user_email": str,
        "assigned_by_id": int,
        "submission_id": int,
        "assigned_at": str (ISO format),
        "due_date": str (ISO format) or None,
        "duration_minutes": int or None,
        "skills": List[str],
        "role": str,
        "curriculum": str,
        "active": bool
    }
    """
    try:
        logger.info(f"🎯 Handling TEST_ASSIGNED event")
        logger.info(f"   Test: {event_data.get('test_name')}")
        logger.info(f"   Participant: {event_data.get('user_email')}")
        logger.info(f"   Submission ID: {event_data.get('submission_id')}")

        # Extract event data
        test_name = event_data.get('test_name', 'Untitled Test')
        user_email = event_data.get('user_email')
        test_id = event_data.get('test_id')
        submission_id = event_data.get('submission_id')
        due_date = event_data.get('due_date')
        duration_minutes = event_data.get('duration_minutes', 60)
        skills = event_data.get('skills', [])
        role = event_data.get('role', '')
        curriculum = event_data.get('curriculum', '')
        assigned_at = event_data.get('assigned_at')

        # Validate required fields
        if not user_email:
            logger.error("❌ Missing user_email in event data")
            return

        if not test_id or not submission_id:
            logger.error("❌ Missing test_id or submission_id in event data")
            return

        # Format due date for display
        due_date_formatted = None
        if due_date:
            try:
                due_date_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                due_date_formatted = due_date_dt.strftime('%B %d, %Y at %I:%M %p')
            except Exception as e:
                logger.warning(f"⚠️  Failed to format due_date: {str(e)}")
                due_date_formatted = due_date

        # Format assigned date
        assigned_at_formatted = None
        if assigned_at:
            try:
                assigned_at_dt = datetime.fromisoformat(assigned_at.replace('Z', '+00:00'))
                assigned_at_formatted = assigned_at_dt.strftime('%B %d, %Y at %I:%M %p')
            except Exception as e:
                logger.warning(f"⚠️  Failed to format assigned_at: {str(e)}")
                assigned_at_formatted = assigned_at

        # Build test URL
        test_url = f"{settings.FRONTEND_URL}/associate/tests/{test_id}"

        # Build email HTML content
        skills_html = ""
        if skills:
            skills_items = "".join([f"<li>{skill}</li>" for skill in skills])
            skills_html = f"""
            <div style="margin: 20px 0;">
                <p style="margin: 5px 0; color: #555;"><strong>Skills being tested:</strong></p>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    {skills_items}
                </ul>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="margin: 0; font-size: 28px;">New Test Assigned</h1>
                </div>

                <div style="background-color: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px;">
                    <p style="font-size: 16px; margin-bottom: 20px;">Hello,</p>

                    <p style="font-size: 16px; margin-bottom: 20px;">
                        You have been assigned a new test: <strong>{test_name}</strong>
                    </p>

                    <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4F46E5;">
                        <h2 style="margin-top: 0; color: #4F46E5; font-size: 20px;">Test Details</h2>
                        <p style="margin: 10px 0;"><strong>Test Name:</strong> {test_name}</p>
                        {f'<p style="margin: 10px 0;"><strong>Role:</strong> {role}</p>' if role else ''}
                        {f'<p style="margin: 10px 0;"><strong>Curriculum:</strong> {curriculum}</p>' if curriculum else ''}
                        <p style="margin: 10px 0;"><strong>Duration:</strong> {duration_minutes} minutes</p>
                        {f'<p style="margin: 10px 0;"><strong>Due Date:</strong> {due_date_formatted}</p>' if due_date_formatted else ''}
                        {f'<p style="margin: 10px 0;"><strong>Assigned On:</strong> {assigned_at_formatted}</p>' if assigned_at_formatted else ''}
                    </div>

                    {skills_html}

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{test_url}"
                           style="display: inline-block; background-color: #4F46E5; color: white; padding: 15px 40px;
                                  text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                            Start Test
                        </a>
                    </div>

                    <p style="font-size: 14px; color: #666; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                        If you have any questions, please contact your trainer or administrator.
                    </p>

                    <p style="font-size: 14px; color: #666; margin-top: 10px;">
                        <strong>Rev EvalAI</strong> - AI-Powered Assessment Platform
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_content = f"""
New Test Assigned: {test_name}

Hello,

You have been assigned a new test: {test_name}

Test Details:
- Test Name: {test_name}
{f'- Role: {role}' if role else ''}
{f'- Curriculum: {curriculum}' if curriculum else ''}
- Duration: {duration_minutes} minutes
{f'- Due Date: {due_date_formatted}' if due_date_formatted else ''}
{f'- Assigned On: {assigned_at_formatted}' if assigned_at_formatted else ''}

{f'Skills being tested: {", ".join(skills)}' if skills else ''}

Start your test here: {test_url}

If you have any questions, please contact your trainer or administrator.

Rev EvalAI - AI-Powered Assessment Platform
        """

        subject = f"New Test Assigned: {test_name}"

        # Prepare context for logging
        context = {
            'test_name': test_name,
            'test_id': test_id,
            'submission_id': submission_id,
            'role': role,
            'curriculum': curriculum,
            'duration_minutes': duration_minutes,
            'skills': skills,
            'due_date': due_date_formatted,
            'assigned_at': assigned_at_formatted,
            'recipient_email': user_email
        }

        # Send email via SES using email service
        db = SessionLocal()
        try:
            result = email_service.send_email(
                db=db,
                to_email=user_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name='test_assigned',
                context=context
            )

            if result.get('success'):
                logger.info(f"✅ Test assignment email sent successfully to {user_email}")
                logger.info(f"   Message ID: {result.get('message_id')}")
                logger.info(f"   Log ID: {result.get('log_id')}")
                if result.get('simulated'):
                    logger.info(f"   Mode: SIMULATED (SES not configured)")
            else:
                logger.error(f"❌ Failed to send test assignment email to {user_email}")
                logger.error(f"   Error: {result.get('error_message')}")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Error in handle_test_assigned_event: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise  # Re-raise to mark message processing as failed


# Event handler registry
EVENT_HANDLERS = {
    'TEST_ASSIGNED': handle_test_assigned_event,
}
