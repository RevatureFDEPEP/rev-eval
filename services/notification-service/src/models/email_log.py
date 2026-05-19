"""
Email Log Model

Tracks all emails sent through the notification service.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from src.db.init_db import Base


class EmailLog(Base):
    """
    Email delivery log for tracking sent emails and their status.
    """
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    template_name = Column(String(100), nullable=True)

    # Delivery status: 'sent', 'failed', 'bounced', 'complained'
    status = Column(String(50), nullable=False, default='sent')

    # SES Message ID for tracking
    ses_message_id = Column(String(255), nullable=True, index=True)

    # Error message if delivery failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Optional: store email context for debugging
    context_data = Column(Text, nullable=True)  # JSON string

    def __repr__(self):
        return f"<EmailLog(id={self.id}, to={self.recipient_email}, status={self.status})>"
