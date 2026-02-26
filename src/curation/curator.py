"""Curator that orchestrates the full curation pipeline."""

from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from src.ai.claude_client import ClaudeClient
from src.config import get_settings
from src.curation.scorer import ListingScorer
from src.curation.selector import DiversitySelector
from src.database import get_db
from src.models import Listing, ListingStatus

logger = structlog.get_logger()


class Curator:
    """Orchestrates the listing curation pipeline."""

    def __init__(
        self,
        scorer: Optional[ListingScorer] = None,
        selector: Optional[DiversitySelector] = None,
        claude_client: Optional[ClaudeClient] = None,
        use_ai_scoring: bool = True,
    ):
        """
        Initialize the curator.

        Args:
            scorer: ListingScorer instance (creates default if None)
            selector: DiversitySelector instance (creates default if None)
            claude_client: ClaudeClient instance (creates default if None)
            use_ai_scoring: Whether to use AI for additional scoring
        """
        self.settings = get_settings()
        self.scorer = scorer or ListingScorer()
        self.selector = selector or DiversitySelector(
            target_count=self.settings.max_listings_per_newsletter,
        )
        self.claude_client = claude_client or ClaudeClient()
        self.use_ai_scoring = use_ai_scoring

    def curate(
        self,
        db: Optional[Session] = None,
    ) -> list[Listing]:
        """
        Run the full curation pipeline.

        Args:
            db: Optional database session (creates one if None)

        Returns:
            List of selected listings ready for content generation
        """
        if db:
            return self._curate_with_session(db)

        with get_db() as db:
            return self._curate_with_session(db)

    def _curate_with_session(self, db: Session) -> list[Listing]:
        """Run curation with a database session."""
        logger.info("Starting curation pipeline")

        # 1. Get unprocessed listings
        candidates = self._get_candidates(db)
        if not candidates:
            logger.warning("No candidate listings found")
            return []

        logger.info("Found candidate listings", count=len(candidates))

        # 2. Get AI scores if enabled
        ai_scores = {}
        if self.use_ai_scoring and candidates:
            ai_scores = self._get_ai_scores(candidates)

        # 3. Score all candidates
        scored = self.scorer.batch_score(candidates, ai_scores)

        # 4. Update scores in database
        for listing, score in scored:
            listing.score = score
            listing.status = ListingStatus.SCORED

        # 5. Select diverse set
        selected = self.selector.select(scored)

        # 6. Mark selected listings
        for listing in selected:
            listing.status = ListingStatus.SELECTED

        # 7. Mark non-selected as skipped
        selected_ids = {l.id for l in selected}
        for listing, _ in scored:
            if listing.id not in selected_ids:
                listing.status = ListingStatus.SKIPPED

        # 8. Log stats
        stats = self.selector.get_selection_stats(selected)
        logger.info("Curation complete", **stats)

        return selected

    def _get_candidates(self, db: Session) -> list[Listing]:
        """Get listings that are candidates for curation."""
        return (
            db.query(Listing)
            .filter(Listing.status.in_([ListingStatus.NEW, ListingStatus.SCORED]))
            .order_by(Listing.received_at.desc())
            .limit(200)  # Reasonable limit for AI scoring
            .all()
        )

    def _get_ai_scores(self, listings: list[Listing]) -> dict[str, float]:
        """Get AI scores for listings."""
        logger.info("Getting AI scores", count=len(listings))

        # Prepare listing data for Claude
        listing_data = [
            {
                "address": l.address,
                "price": l.price,
                "bedrooms": l.bedrooms,
                "bathrooms": l.bathrooms,
                "sqft": l.sqft,
                "year_built": l.year_built,
                "neighborhood": l.neighborhood,
                "property_type": l.property_type,
                "description": (l.description_raw or "")[:500],  # Truncate for token limits
            }
            for l in listings
        ]

        try:
            scored_data = self.claude_client.score_listings(listing_data)

            # Build address -> score mapping
            ai_scores = {}
            for item in scored_data:
                address = item.get("address")
                score = item.get("ai_score", item.get("score", 50))
                if address:
                    ai_scores[address] = float(score)

            logger.info("AI scoring complete", scores_received=len(ai_scores))
            return ai_scores

        except Exception as e:
            logger.error("AI scoring failed, falling back to rule-based", error=str(e))
            return {}

    def check_readiness(self) -> dict:
        """
        Check if we have enough quality listings for a newsletter.

        Returns:
            Dict with readiness status and stats
        """
        with get_db() as db:
            # Count candidates
            candidates = self._get_candidates(db)

            # Quick score without AI
            scored = self.scorer.batch_score(candidates)

            # Count high-quality listings (score > 40)
            quality_count = sum(1 for _, score in scored if score > 40)

            ready = quality_count >= self.settings.min_listings_to_publish

            return {
                "ready": ready,
                "total_candidates": len(candidates),
                "quality_candidates": quality_count,
                "minimum_required": self.settings.min_listings_to_publish,
                "checked_at": datetime.utcnow().isoformat(),
            }

    def get_curated_preview(self, limit: int = 5) -> list[dict]:
        """
        Get a preview of what would be curated without committing.

        Args:
            limit: Number of top listings to preview

        Returns:
            List of listing dicts with scores
        """
        with get_db() as db:
            candidates = self._get_candidates(db)
            scored = self.scorer.batch_score(candidates)
            selected = self.selector.select(scored)

            return [
                {
                    "address": l.address,
                    "price": l.price,
                    "neighborhood": l.neighborhood,
                    "score": l.score,
                }
                for l in selected[:limit]
            ]
