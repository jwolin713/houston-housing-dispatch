"""Alert management for system notifications."""

from datetime import datetime
from typing import Optional

import structlog

from src.config import get_settings
from src.notifications.email_sender import EmailSender

logger = structlog.get_logger()


class AlertManager:
    """Manages system alerts and notifications."""

    def __init__(self, email_sender: Optional[EmailSender] = None):
        self.settings = get_settings()
        self.email_sender = email_sender or EmailSender()

    def alert_error(self, title: str, message: str, details: Optional[dict] = None):
        """Send an error alert."""
        logger.error(title, message=message, **(details or {}))
        self.email_sender.send_alert_email(
            subject=f"Error: {title}",
            message=message,
            details=details,
        )

    def alert_warning(self, title: str, message: str, details: Optional[dict] = None):
        """Send a warning alert."""
        logger.warning(title, message=message, **(details or {}))
        self.email_sender.send_alert_email(
            subject=f"Warning: {title}",
            message=message,
            details=details,
        )

    def alert_cookie_expiring(self, days_remaining: int):
        """Alert that Substack cookies are expiring soon."""
        self.alert_warning(
            title="Substack Cookies Expiring",
            message=f"Substack cookies will expire in approximately {days_remaining} days. "
                   "Please refresh cookies to avoid service interruption.",
            details={
                "days_remaining": days_remaining,
                "action_required": "Run: houston-dispatch cookies capture",
            },
        )

    def alert_no_listings(self, days_without: int):
        """Alert that no new listings have been received."""
        self.alert_warning(
            title="No New Listings",
            message=f"No new HAR listings have been received for {days_without} days.",
            details={
                "days_without_listings": days_without,
                "possible_causes": [
                    "Gmail label filter changed",
                    "HAR stopped sending alerts",
                    "Email parsing errors",
                ],
            },
        )

    def alert_pipeline_failure(self, stage: str, error: str):
        """Alert that the pipeline failed at a stage."""
        self.alert_error(
            title=f"Pipeline Failed: {stage}",
            message=f"The newsletter pipeline failed during the {stage} stage.",
            details={
                "stage": stage,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    def alert_substack_auth_failure(self):
        """Alert that Substack authentication failed."""
        self.alert_error(
            title="Substack Authentication Failed",
            message="Substack API returned authentication error. Cookies may be expired.",
            details={
                "action_required": "Refresh cookies immediately",
                "command": "houston-dispatch cookies capture",
            },
        )
