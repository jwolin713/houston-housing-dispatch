"""APScheduler job definitions for the newsletter pipeline."""

from datetime import datetime

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import get_settings

logger = structlog.get_logger()


def run_daily_pipeline():
    """
    Run the daily newsletter pipeline.

    This job:
    1. Fetches new emails from Gmail
    2. Parses listings
    3. Curates listings if enough quality ones exist
    4. Generates newsletter content
    5. Creates Substack draft
    6. Sends approval email
    """
    logger.info("Starting daily pipeline job")

    try:
        # Import here to avoid circular imports
        from src.database import get_db, init_db
        from src.email.processor import EmailProcessor
        from src.curation.curator import Curator
        from src.generation.generator import NewsletterGenerator
        from src.publishers.substack_client import SubstackPublisher
        from src.workflows.approval import ApprovalWorkflow
        from src.models import Newsletter, NewsletterStatus

        settings = get_settings()

        # Initialize database
        init_db()

        # Step 1: Fetch and process emails
        logger.info("Step 1: Processing emails")
        processor = EmailProcessor()
        email_stats = processor.process_emails(days_back=3)
        logger.info("Email processing complete", **email_stats)

        # Step 2: Check if we have enough listings
        curator = Curator()
        readiness = curator.check_readiness()

        if not readiness["ready"]:
            logger.info(
                "Not enough quality listings for newsletter",
                quality_count=readiness["quality_candidates"],
                required=readiness["minimum_required"],
            )
            return {
                "success": True,
                "action": "skipped",
                "reason": "insufficient_listings",
                "stats": readiness,
            }

        # Step 3: Curate listings
        logger.info("Step 2: Curating listings")
        with get_db() as db:
            selected = curator.curate(db)

            if not selected:
                logger.warning("Curation returned no listings")
                return {
                    "success": True,
                    "action": "skipped",
                    "reason": "curation_empty",
                }

            # Step 4: Generate newsletter content
            logger.info("Step 3: Generating newsletter")
            generator = NewsletterGenerator()
            content = generator.generate_newsletter(selected)

            # Step 5: Create newsletter record
            newsletter = Newsletter(
                title=content["title"],
                intro=content["intro"],
                content_markdown=content["markdown"],
                content_html=content["html"],
                status=NewsletterStatus.DRAFT,
            )
            db.add(newsletter)

            # Link listings to newsletter
            for listing in selected:
                listing.selected_for_newsletter_id = newsletter.id

            db.flush()

            # Step 6: Create Substack draft
            logger.info("Step 4: Creating Substack draft")
            publisher = SubstackPublisher()
            draft_result = publisher.create_draft(
                title=content["title"],
                content_html=content["html"],
            )

            if draft_result.success:
                newsletter.substack_draft_id = draft_result.draft_id
            else:
                logger.warning(
                    "Substack draft creation failed, continuing with approval",
                    error=draft_result.error,
                )

            # Step 7: Send for approval
            logger.info("Step 5: Sending for approval")
            workflow = ApprovalWorkflow()
            approval_result = workflow.send_for_approval(
                db,
                newsletter,
                base_url=settings.substack_publication_url.replace(
                    ".substack.com", "-api.vercel.app"
                ),  # Adjust based on your deployment
            )

        logger.info("Daily pipeline complete", newsletter_id=newsletter.id)

        return {
            "success": True,
            "action": "newsletter_created",
            "newsletter_id": newsletter.id,
            "listings_count": len(selected),
            "approval_sent": approval_result.get("success", False),
        }

    except Exception as e:
        logger.error("Daily pipeline failed", error=str(e))
        # Send alert
        from src.notifications.email_sender import EmailSender
        sender = EmailSender()
        sender.send_alert_email(
            subject="Daily Pipeline Failed",
            message=f"The daily newsletter pipeline failed: {str(e)}",
            details={"timestamp": datetime.utcnow().isoformat()},
        )
        return {
            "success": False,
            "error": str(e),
        }


def run_cleanup_job():
    """
    Run cleanup tasks:
    - Archive expired approval requests
    - Clean up old raw emails
    """
    logger.info("Starting cleanup job")

    try:
        from src.workflows.approval import ApprovalWorkflow

        # Archive expired newsletters
        workflow = ApprovalWorkflow()
        result = workflow.archive_expired()

        logger.info("Cleanup complete", archived=result["archived_count"])

        return result

    except Exception as e:
        logger.error("Cleanup job failed", error=str(e))
        return {"success": False, "error": str(e)}


def run_reminder_job():
    """Send reminders for newsletters approaching expiration."""
    logger.info("Starting reminder job")

    try:
        from src.workflows.approval import ApprovalWorkflow

        workflow = ApprovalWorkflow()
        result = workflow.check_pending_reminders()

        logger.info("Reminder job complete", reminders_sent=result["reminders_sent"])

        return result

    except Exception as e:
        logger.error("Reminder job failed", error=str(e))
        return {"success": False, "error": str(e)}


def run_health_check():
    """Run periodic health checks on external services."""
    logger.info("Running health checks")

    try:
        from src.monitoring.health_checks import HealthChecker

        checker = HealthChecker()
        results = checker.check_all()

        # Alert if any checks failed
        if not results["all_healthy"]:
            from src.notifications.email_sender import EmailSender
            sender = EmailSender()
            sender.send_alert_email(
                subject="Health Check Failed",
                message="One or more health checks failed.",
                details=results["checks"],
            )

        return results

    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {"success": False, "error": str(e)}


class PipelineScheduler:
    """Manages the APScheduler for running pipeline jobs."""

    def __init__(self):
        self.settings = get_settings()
        self.scheduler = BackgroundScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Configure scheduled jobs."""
        # Daily pipeline at configured hour (default 8 AM)
        self.scheduler.add_job(
            run_daily_pipeline,
            trigger=CronTrigger(
                hour=self.settings.curation_hour,
                minute=0,
                timezone=self.settings.timezone,
            ),
            id="daily_pipeline",
            name="Daily Newsletter Pipeline",
            replace_existing=True,
        )

        # Cleanup job every 6 hours
        self.scheduler.add_job(
            run_cleanup_job,
            trigger=CronTrigger(hour="*/6", minute=30),
            id="cleanup",
            name="Cleanup Expired Items",
            replace_existing=True,
        )

        # Reminder job every 2 hours
        self.scheduler.add_job(
            run_reminder_job,
            trigger=CronTrigger(hour="*/2", minute=15),
            id="reminders",
            name="Send Approval Reminders",
            replace_existing=True,
        )

        # Health check every hour
        self.scheduler.add_job(
            run_health_check,
            trigger=CronTrigger(minute=0),
            id="health_check",
            name="Health Check",
            replace_existing=True,
        )

    def start(self):
        """Start the scheduler."""
        logger.info("Starting scheduler")
        self.scheduler.start()

    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler")
        self.scheduler.shutdown()

    def run_now(self, job_id: str):
        """Manually trigger a job."""
        job = self.scheduler.get_job(job_id)
        if job:
            logger.info("Manually running job", job_id=job_id)
            job.func()
        else:
            logger.error("Job not found", job_id=job_id)

    def get_jobs(self) -> list[dict]:
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in self.scheduler.get_jobs()
        ]
