"""
Notification API Routes

Endpoints for sending emails and managing notifications.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
import jwt
import logging

from src.db.session import get_db
from src.schemas.email_schema import (
    SendEmailRequest,
    SendTemplatedEmailRequest,
    InviteUserEmailRequest,
    TestAssignmentEmailRequest,
    EmailResponse,
    EmailLogResponse
)
from src.services.email_service import email_service
from src.services.template_service import template_service
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/api/notifications", tags=["notifications"])


@router.post("/send", response_model=EmailResponse)
def send_email(
    request: SendEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Send a generic email with custom HTML content.
    """
    result = email_service.send_email(
        db=db,
        to_email=request.recipient_email,
        subject=request.subject,
        html_content=request.html_content,
        text_content=request.text_content,
        template_name=request.template_name
    )

    return EmailResponse(**result)


@router.post("/send-templated", response_model=EmailResponse)
def send_templated_email(
    request: SendTemplatedEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Send an email using a template.
    """
    try:
        # Add current year to context
        context = {**request.context, "current_year": datetime.now().year}

        # Render template
        html_content, text_content = template_service.render_template(
            template_name=request.template_name,
            context=context
        )

        # Send email
        result = email_service.send_email(
            db=db,
            to_email=request.recipient_email,
            subject=context.get("subject", "Notification from Rev EvalAI"),
            html_content=html_content,
            text_content=text_content,
            template_name=request.template_name,
            context=context
        )

        return EmailResponse(**result)

    except Exception as e:
        logger.error(f"Error sending templated email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.post("/invite", response_model=EmailResponse)
def send_invite_email(
    request: InviteUserEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Send a user invitation email with registration link.
    """
    try:
        # Build registration URL
        registration_url = f"{settings.FRONTEND_URL}/auth/register/{request.invite_token}"

        # Prepare context
        context = {
            "first_name": request.first_name,
            "last_name": request.last_name or "",
            "registration_url": registration_url,
            "current_year": datetime.now().year
        }

        # Render template
        html_content, text_content = template_service.render_template(
            template_name="invite_user",
            context=context
        )

        # Send email
        result = email_service.send_email(
            db=db,
            to_email=request.email,
            subject=f"You're invited to join Rev EvalAI, {request.first_name}!",
            html_content=html_content,
            text_content=text_content,
            template_name="invite_user",
            context=context
        )

        return EmailResponse(**result)

    except Exception as e:
        logger.error(f"Error sending invite email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send invite email: {str(e)}"
        )


@router.post("/test-assigned", response_model=EmailResponse)
def send_test_assignment_email(
    request: TestAssignmentEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Send a test assignment notification email.
    """
    try:
        # Build test URL
        test_url = f"{settings.FRONTEND_URL}/associate/tests/{request.test_id}"

        # Prepare context
        context = {
            "first_name": request.participant_email.split('@')[0].title(),  # Extract name from email
            "test_name": request.test_name,
            "role": request.role,
            "curriculum": request.curriculum,
            "skills": request.skills,
            "duration_minutes": request.duration_minutes,
            "deadline": request.deadline,
            "test_url": test_url,
            "current_year": datetime.now().year
        }

        # Render template
        html_content, text_content = template_service.render_template(
            template_name="test_assigned",
            context=context
        )

        # Send email
        result = email_service.send_email(
            db=db,
            to_email=request.participant_email,
            subject=f"New Test Assigned: {request.test_name}",
            html_content=html_content,
            text_content=text_content,
            template_name="test_assigned",
            context=context
        )

        return EmailResponse(**result)

    except Exception as e:
        logger.error(f"Error sending test assignment email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test assignment email: {str(e)}"
        )


@router.get("/logs", response_model=list[EmailLogResponse])
def get_email_logs(
    recipient_email: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get email delivery logs with optional filters.
    """
    logs = email_service.get_email_logs(
        db=db,
        recipient_email=recipient_email,
        status=status,
        limit=limit,
        offset=offset
    )

    return [EmailLogResponse.model_validate(log) for log in logs]


@router.post("/validate-invite-token")
def validate_invite_token(token: str):
    """
    Validate an invitation token and return email if valid.
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.INVITE_TOKEN_SECRET,
            algorithms=["HS256"]
        )

        # Check if token is expired
        if payload.get("exp") and payload["exp"] < datetime.utcnow().timestamp():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation token has expired"
            )

        # Return email from token
        return {
            "valid": True,
            "email": payload.get("email"),
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name")
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation token"
        )
