"""Approval workflow orchestration."""

from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from src.auth.tokens import TokenManager
from src.config import get_settings
from src.database import get_db
from src.models import Newsletter, NewsletterStatus
from src.notifications.email_sender import EmailSender
from src.publishers.substack_client import ManualFallbackPublisher, SubstackPublisher

logger = structlog.get_logger()


class ApprovalWorkflow:
    """
    Orchestrates the newsletter approval workflow.

    Handles the state transitions:
    - draft -> pending_approval (when approval email sent)
    - pending_approval -> publishing (when user approves)
    - publishing -> published (when publish succeeds)
    - pending_approval -> rejected (when user rejects)
    - pending_approval -> archived (when timeout)
    """

    def __init__(
        self,
        publisher: Optional[SubstackPublisher] = None,
        email_sender: Optional[EmailSender] = None,
        token_manager: Optional[TokenManager] = None,
    ):
        """
        Initialize the workflow.

        Args:
            publisher: SubstackPublisher instance
            email_sender: EmailSender instance
            token_manager: TokenManager instance
        """
        self.settings = get_settings()
        self.publisher = publisher or SubstackPublisher()
        self.email_sender = email_sender or EmailSender()
        self.token_manager = token_manager or TokenManager()
        self._fallback_publisher = ManualFallbackPublisher()

    def send_for_approval(
        self,
        db: Session,
        newsletter: Newsletter,
        base_url: str = "http://localhost:8000",
    ) -> dict:
        """
        Send a newsletter for approval.

        Args:
            db: Database session
            newsletter: The newsletter to send for approval
            base_url: Base URL for approval links

        Returns:
            Dict with success status and details
        """
        logger.info("Sending newsletter for approval", newsletter_id=newsletter.id)

        # Generate approval tokens
        tokens = self.token_manager.create_approval_tokens(
            resource_id=newsletter.id,
            resource_type="newsletter",
        )

        # Build URLs
        approve_url = f"{base_url}/approve/newsletter/{tokens['approve_token']}?action=approve"
        reject_url = f"{base_url}/approve/newsletter/{tokens['reject_token']}?action=reject"
        preview_url = f"{base_url}/approve/preview/{newsletter.id}"

        # Update newsletter with token info
        newsletter.approval_token = tokens["approve_token"]
        newsletter.approval_expires_at = self.token_manager.get_token_expiry()
        newsletter.status = NewsletterStatus.PENDING_APPROVAL

        # Send email
        email_sent = self.email_sender.send_approval_email(
            newsletter_id=newsletter.id,
            title=newsletter.title,
            preview_html=newsletter.content_html or newsletter.content_markdown or "",
            approve_url=approve_url,
            reject_url=reject_url,
            preview_url=preview_url,
        )

        if not email_sent:
            logger.error("Failed to send approval email", newsletter_id=newsletter.id)
            return {
                "success": False,
                "error": "Failed to send approval email",
            }

        logger.info(
            "Newsletter sent for approval",
            newsletter_id=newsletter.id,
            expires_at=newsletter.approval_expires_at.isoformat(),
        )

        return {
            "success": True,
            "newsletter_id": newsletter.id,
            "expires_at": newsletter.approval_expires_at.isoformat(),
            "preview_url": preview_url,
        }

    def approve(
        self,
        db: Session,
        newsletter: Newsletter,
    ) -> dict:
        """
        Approve and publish a newsletter.

        Implements two-phase commit:
        1. Mark as 'publishing'
        2. Publish to Substack
        3. Mark as 'published'

        Args:
            db: Database session
            newsletter: The newsletter to approve

        Returns:
            Dict with success status and details
        """
        logger.info("Approving newsletter", newsletter_id=newsletter.id)

        # Optimistic locking - check version
        current_version = newsletter.version

        # Phase 1: Mark as publishing
        newsletter.status = NewsletterStatus.PUBLISHING
        newsletter.approved_at = datetime.utcnow()
        newsletter.version += 1
        db.flush()

        # Check for concurrent modification
        db.refresh(newsletter)
        if newsletter.version != current_version + 1:
            logger.warning(
                "Concurrent modification detected",
                newsletter_id=newsletter.id,
            )
            return {
                "success": False,
                "error": "Newsletter was modified by another request",
            }

        # Phase 2: Publish to Substack
        try:
            # Check Substack health first
            health = self.publisher.check_health()

            if health.get("healthy"):
                result = self.publisher.publish_draft(newsletter.substack_draft_id)
            else:
                logger.warning(
                    "Substack unhealthy, using fallback",
                    newsletter_id=newsletter.id,
                )
                result = self._fallback_publisher.create_draft(
                    title=newsletter.title,
                    content_html=newsletter.content_html,
                )

            if not result.success:
                # Rollback to pending_approval
                newsletter.status = NewsletterStatus.PENDING_APPROVAL
                newsletter.approved_at = None
                newsletter.version += 1

                return {
                    "success": False,
                    "error": f"Publish failed: {result.error}",
                }

            # Phase 3: Mark as published
            newsletter.status = NewsletterStatus.PUBLISHED
            newsletter.published_at = datetime.utcnow()
            newsletter.substack_post_url = result.post_url
            newsletter.version += 1

            logger.info(
                "Newsletter published",
                newsletter_id=newsletter.id,
                post_url=result.post_url,
            )

            # Mark listings as used
            for listing in newsletter.listings:
                from src.models import ListingStatus
                listing.status = ListingStatus.USED

            return {
                "success": True,
                "newsletter_id": newsletter.id,
                "post_url": result.post_url,
            }

        except Exception as e:
            logger.error(
                "Publish failed with exception",
                newsletter_id=newsletter.id,
                error=str(e),
            )

            # Rollback
            newsletter.status = NewsletterStatus.PENDING_APPROVAL
            newsletter.approved_at = None
            newsletter.version += 1

            return {
                "success": False,
                "error": str(e),
            }

    def reject(
        self,
        db: Session,
        newsletter: Newsletter,
        feedback: Optional[str] = None,
    ) -> dict:
        """
        Reject a newsletter.

        Args:
            db: Database session
            newsletter: The newsletter to reject
            feedback: Optional rejection feedback

        Returns:
            Dict with success status
        """
        logger.info(
            "Rejecting newsletter",
            newsletter_id=newsletter.id,
            feedback=feedback,
        )

        newsletter.status = NewsletterStatus.REJECTED
        newsletter.rejection_feedback = feedback
        newsletter.version += 1

        # Return listings to scored state for next curation
        for listing in newsletter.listings:
            from src.models import ListingStatus
            listing.status = ListingStatus.SCORED
            listing.selected_for_newsletter_id = None

        return {
            "success": True,
            "newsletter_id": newsletter.id,
        }

    def archive_expired(self) -> dict:
        """
        Archive newsletters that have expired without approval.

        Returns:
            Dict with count of archived newsletters
        """
        logger.info("Checking for expired newsletters")

        archived_count = 0

        with get_db() as db:
            expired = (
                db.query(Newsletter)
                .filter(
                    Newsletter.status == NewsletterStatus.PENDING_APPROVAL,
                    Newsletter.approval_expires_at < datetime.utcnow(),
                )
                .all()
            )

            for newsletter in expired:
                newsletter.status = NewsletterStatus.ARCHIVED
                newsletter.version += 1

                # Return listings
                for listing in newsletter.listings:
                    from src.models import ListingStatus
                    listing.status = ListingStatus.SCORED
                    listing.selected_for_newsletter_id = None

                archived_count += 1

                logger.info(
                    "Newsletter archived due to timeout",
                    newsletter_id=newsletter.id,
                )

        return {
            "archived_count": archived_count,
        }

    def check_pending_reminders(self, base_url: str = "http://localhost:8000") -> dict:
        """
        Send reminders for newsletters approaching expiration.

        Returns:
            Dict with count of reminders sent
        """
        from datetime import timedelta

        reminder_threshold = datetime.utcnow() + timedelta(hours=6)
        reminder_sent = 0

        with get_db() as db:
            approaching = (
                db.query(Newsletter)
                .filter(
                    Newsletter.status == NewsletterStatus.PENDING_APPROVAL,
                    Newsletter.approval_expires_at < reminder_threshold,
                    Newsletter.approval_expires_at > datetime.utcnow(),
                )
                .all()
            )

            for newsletter in approaching:
                # Re-send approval email as reminder
                self.email_sender.send_alert_email(
                    subject=f"Reminder: Newsletter expires soon",
                    message=f"Newsletter '{newsletter.title}' will expire in less than 6 hours.",
                    details={
                        "Newsletter ID": newsletter.id,
                        "Expires": newsletter.approval_expires_at.isoformat(),
                        "Preview": f"{base_url}/approve/preview/{newsletter.id}",
                    },
                )
                reminder_sent += 1

        return {
            "reminders_sent": reminder_sent,
        }
