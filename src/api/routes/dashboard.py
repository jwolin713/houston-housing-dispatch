"""Dashboard endpoints for system status and management."""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.database import get_db
from src.models import Listing, ListingStatus, Newsletter, NewsletterStatus

logger = structlog.get_logger()
router = APIRouter()


class DashboardStats(BaseModel):
    """Dashboard statistics model."""

    listings_total: int
    listings_new: int
    listings_scored: int
    listings_selected: int
    newsletters_total: int
    newsletters_pending: int
    newsletters_published: int
    last_newsletter_date: Optional[str]
    last_ingestion_date: Optional[str]


@router.get("/stats")
async def get_dashboard_stats() -> DashboardStats:
    """Get dashboard statistics."""
    with get_db() as db:
        # Listing stats
        listings_total = db.query(Listing).count()
        listings_new = (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.NEW)
            .count()
        )
        listings_scored = (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.SCORED)
            .count()
        )
        listings_selected = (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.SELECTED)
            .count()
        )

        # Newsletter stats
        newsletters_total = db.query(Newsletter).count()
        newsletters_pending = (
            db.query(Newsletter)
            .filter(
                Newsletter.status.in_([
                    NewsletterStatus.DRAFT,
                    NewsletterStatus.PENDING_APPROVAL,
                ])
            )
            .count()
        )
        newsletters_published = (
            db.query(Newsletter)
            .filter(Newsletter.status == NewsletterStatus.PUBLISHED)
            .count()
        )

        # Last dates
        last_newsletter = (
            db.query(Newsletter)
            .filter(Newsletter.status == NewsletterStatus.PUBLISHED)
            .order_by(Newsletter.published_at.desc())
            .first()
        )
        last_listing = (
            db.query(Listing)
            .order_by(Listing.received_at.desc())
            .first()
        )

        return DashboardStats(
            listings_total=listings_total,
            listings_new=listings_new,
            listings_scored=listings_scored,
            listings_selected=listings_selected,
            newsletters_total=newsletters_total,
            newsletters_pending=newsletters_pending,
            newsletters_published=newsletters_published,
            last_newsletter_date=(
                last_newsletter.published_at.isoformat()
                if last_newsletter and last_newsletter.published_at
                else None
            ),
            last_ingestion_date=(
                last_listing.received_at.isoformat()
                if last_listing
                else None
            ),
        )


@router.get("/recent-newsletters")
async def get_recent_newsletters(limit: int = Query(10, ge=1, le=50)):
    """Get recent newsletters."""
    with get_db() as db:
        newsletters = (
            db.query(Newsletter)
            .order_by(Newsletter.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": n.id,
                "title": n.title,
                "status": n.status.value,
                "created_at": n.created_at.isoformat(),
                "published_at": n.published_at.isoformat() if n.published_at else None,
                "listing_count": len(n.listings),
            }
            for n in newsletters
        ]


@router.get("/pending-approval")
async def get_pending_approval():
    """Get newsletters pending approval."""
    with get_db() as db:
        pending = (
            db.query(Newsletter)
            .filter(
                Newsletter.status.in_([
                    NewsletterStatus.DRAFT,
                    NewsletterStatus.PENDING_APPROVAL,
                ])
            )
            .order_by(Newsletter.created_at.desc())
            .all()
        )

        return [
            {
                "id": n.id,
                "title": n.title,
                "status": n.status.value,
                "created_at": n.created_at.isoformat(),
                "expires_at": (
                    n.approval_expires_at.isoformat()
                    if n.approval_expires_at
                    else None
                ),
                "listing_count": len(n.listings),
            }
            for n in pending
        ]


@router.post("/trigger-pipeline")
async def trigger_pipeline():
    """Manually trigger the newsletter pipeline."""
    from src.scheduler.jobs import run_daily_pipeline

    logger.info("Manually triggering pipeline via API")
    result = run_daily_pipeline()
    return result


@router.post("/send-approval/{newsletter_id}")
async def send_approval_email(newsletter_id: int):
    """Send approval email for an existing newsletter."""
    from src.config import get_settings
    from src.workflows.approval import ApprovalWorkflow

    settings = get_settings()
    with get_db() as db:
        newsletter = db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
        if not newsletter:
            return {"success": False, "error": "Newsletter not found"}

        workflow = ApprovalWorkflow()
        base_url = f"https://web-production-77eff.up.railway.app"
        result = workflow.send_for_approval(db, newsletter, base_url=base_url)
        return result


@router.post("/reset-listings")
async def reset_listing_statuses():
    """Reset all selected/scored listings back to 'new' so the pipeline can re-curate."""
    with get_db() as db:
        updated = (
            db.query(Listing)
            .filter(
                Listing.status.in_([
                    ListingStatus.SCORED,
                    ListingStatus.SELECTED,
                ])
            )
            .update(
                {Listing.status: ListingStatus.NEW, Listing.selected_for_newsletter_id: None},
                synchronize_session="fetch",
            )
        )
        return {"success": True, "reset_count": updated}


@router.get("/recent-listings")
async def get_recent_listings(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
):
    """Get recent listings."""
    with get_db() as db:
        query = db.query(Listing).order_by(Listing.received_at.desc())

        if status:
            try:
                status_enum = ListingStatus(status)
                query = query.filter(Listing.status == status_enum)
            except ValueError:
                pass

        listings = query.limit(limit).all()

        return [
            {
                "id": l.id,
                "address": l.address,
                "price": l.price,
                "neighborhood": l.neighborhood,
                "status": l.status.value,
                "score": l.score,
                "received_at": l.received_at.isoformat(),
            }
            for l in listings
        ]
