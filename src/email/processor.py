"""Email processor that orchestrates fetching, parsing, and storing listings."""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db
from src.email.gmail_client import EmailMessage, GmailClient
from src.email.parser import HAREmailParser, ParsedListing
from src.models import Listing, ListingStatus, RawEmail

logger = structlog.get_logger()


class EmailProcessor:
    """Orchestrates the email ingestion pipeline."""

    def __init__(self):
        self.settings = get_settings()
        self.gmail_client = GmailClient()
        self.parser = HAREmailParser()

    def process_emails(
        self,
        days_back: int = 7,
        max_emails: int = 50,
    ) -> dict:
        """
        Main entry point: fetch, parse, and store new listings.

        Args:
            days_back: How many days back to look for emails
            max_emails: Maximum emails to process in one run

        Returns:
            Summary dict with counts
        """
        logger.info(
            "Starting email processing",
            days_back=days_back,
            max_emails=max_emails,
        )

        # Calculate date range
        after_date = datetime.utcnow() - timedelta(days=days_back)

        # Fetch emails
        emails = self.gmail_client.fetch_emails(
            max_results=max_emails,
            after_date=after_date,
        )

        stats = {
            "emails_fetched": len(emails),
            "emails_processed": 0,
            "emails_skipped": 0,
            "listings_parsed": 0,
            "listings_new": 0,
            "listings_updated": 0,
            "errors": 0,
        }

        with get_db() as db:
            for email in emails:
                try:
                    result = self._process_single_email(db, email)
                    if result["processed"]:
                        stats["emails_processed"] += 1
                        stats["listings_parsed"] += result["listings_parsed"]
                        stats["listings_new"] += result["listings_new"]
                        stats["listings_updated"] += result["listings_updated"]
                    else:
                        stats["emails_skipped"] += 1
                except Exception as e:
                    logger.error(
                        "Failed to process email",
                        email_id=email.id,
                        error=str(e),
                    )
                    stats["errors"] += 1

        logger.info("Email processing complete", **stats)
        return stats

    def _process_single_email(
        self,
        db: Session,
        email: EmailMessage,
    ) -> dict:
        """Process a single email message."""
        result = {
            "processed": False,
            "listings_parsed": 0,
            "listings_new": 0,
            "listings_updated": 0,
        }

        # Check if already processed
        existing = db.query(RawEmail).filter(RawEmail.email_id == email.id).first()
        if existing and existing.parse_status == "success":
            logger.debug("Email already processed", email_id=email.id)
            return result

        # Store raw email for debugging/reprocessing
        raw_email = self._store_raw_email(db, email, existing)

        # Parse listings from email
        try:
            listings = self.parser.parse_email(email.body_html or email.body_text)
            result["listings_parsed"] = len(listings)

            # Store each listing
            for parsed in listings:
                new, updated = self._store_listing(db, parsed, email.id)
                if new:
                    result["listings_new"] += 1
                elif updated:
                    result["listings_updated"] += 1

            # Mark as successfully processed
            raw_email.parse_status = "success"
            raw_email.processed_at = datetime.utcnow()
            result["processed"] = True

            logger.info(
                "Processed email",
                email_id=email.id,
                subject=email.subject,
                listings=len(listings),
            )

        except Exception as e:
            raw_email.parse_status = "error"
            raw_email.parse_error = str(e)
            logger.error(
                "Failed to parse email",
                email_id=email.id,
                error=str(e),
            )
            raise

        return result

    def _store_raw_email(
        self,
        db: Session,
        email: EmailMessage,
        existing: Optional[RawEmail],
    ) -> RawEmail:
        """Store raw email content."""
        if existing:
            existing.raw_content = email.body_html or email.body_text
            return existing

        raw_email = RawEmail(
            email_id=email.id,
            subject=email.subject,
            sender=email.sender,
            received_at=email.received_at,
            raw_content=email.body_html or email.body_text,
            parse_status="pending",
        )
        db.add(raw_email)
        return raw_email

    def _store_listing(
        self,
        db: Session,
        parsed: ParsedListing,
        email_id: str,
    ) -> tuple[bool, bool]:
        """
        Store or update a listing in the database.

        Returns:
            Tuple of (is_new, is_updated)
        """
        # Check for existing listing by address
        existing = db.query(Listing).filter(Listing.address == parsed.address).first()

        if existing:
            # Update if price changed or more data available
            updated = False

            if existing.price != parsed.price:
                existing.price = parsed.price
                updated = True
                logger.info(
                    "Listing price updated",
                    address=parsed.address,
                    old_price=existing.price,
                    new_price=parsed.price,
                )

            # Update other fields if previously missing
            if not existing.sqft and parsed.sqft:
                existing.sqft = parsed.sqft
                updated = True

            if not existing.year_built and parsed.year_built:
                existing.year_built = parsed.year_built
                updated = True

            if not existing.neighborhood and parsed.neighborhood:
                existing.neighborhood = parsed.neighborhood
                updated = True

            if not existing.subdivision and parsed.subdivision:
                existing.subdivision = parsed.subdivision
                updated = True

            if parsed.image_urls and (not existing.image_urls or len(parsed.image_urls) > len(existing.image_urls or [])):
                existing.image_urls = parsed.image_urls
                updated = True

            return False, updated

        # Create new listing
        listing = Listing(
            address=parsed.address,
            price=parsed.price,
            bedrooms=parsed.bedrooms,
            bathrooms=parsed.bathrooms,
            sqft=parsed.sqft,
            year_built=parsed.year_built,
            neighborhood=parsed.neighborhood,
            subdivision=parsed.subdivision,
            property_type=parsed.property_type,
            har_link=parsed.har_link,
            description_raw=parsed.description,
            image_urls=parsed.image_urls,
            email_id=email_id,
            received_at=datetime.utcnow(),
            parsed_at=datetime.utcnow(),
            status=ListingStatus.NEW,
        )
        db.add(listing)

        logger.info(
            "New listing stored",
            address=parsed.address,
            price=parsed.price,
            neighborhood=parsed.neighborhood,
        )

        return True, False

    def get_unprocessed_listings(self, db: Session, limit: int = 100) -> list[Listing]:
        """Get listings that haven't been scored/curated yet."""
        return (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.NEW)
            .order_by(Listing.received_at.desc())
            .limit(limit)
            .all()
        )

    def reprocess_failed_emails(self) -> dict:
        """Reprocess emails that failed parsing."""
        logger.info("Reprocessing failed emails")
        stats = {"reprocessed": 0, "success": 0, "still_failed": 0}

        with get_db() as db:
            failed_emails = (
                db.query(RawEmail)
                .filter(RawEmail.parse_status == "error")
                .all()
            )

            for raw_email in failed_emails:
                stats["reprocessed"] += 1
                try:
                    listings = self.parser.parse_email(raw_email.raw_content)

                    for parsed in listings:
                        self._store_listing(db, parsed, raw_email.email_id)

                    raw_email.parse_status = "success"
                    raw_email.processed_at = datetime.utcnow()
                    raw_email.parse_error = None
                    stats["success"] += 1

                except Exception as e:
                    raw_email.parse_error = str(e)
                    stats["still_failed"] += 1
                    logger.error(
                        "Reprocessing still failed",
                        email_id=raw_email.email_id,
                        error=str(e),
                    )

        logger.info("Reprocessing complete", **stats)
        return stats
