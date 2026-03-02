"""Curator that orchestrates the full curation pipeline."""

from datetime import datetime

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
    """Orchestrates the listing curation pipeline.

    Pipeline steps:
    1. Get candidate listings (NEW/SCORED)
    2. Enrich with Zillow data (if enabled)
    3. AI scoring with voice-aligned prompt
    4. Rule-based guardrail scoring
    5. Combine scores (70% AI + 30% rules)
    6. Diversity selection
    """

    def __init__(
        self,
        scorer: ListingScorer | None = None,
        selector: DiversitySelector | None = None,
        claude_client: ClaudeClient | None = None,
        use_ai_scoring: bool = True,
    ):
        self.settings = get_settings()
        self.scorer = scorer or ListingScorer()
        self.selector = selector or DiversitySelector(
            target_count=self.settings.max_listings_per_newsletter,
        )
        self.claude_client = claude_client or ClaudeClient()
        self.use_ai_scoring = use_ai_scoring

    def curate(
        self,
        db: Session | None = None,
    ) -> list[Listing]:
        """
        Run the full curation pipeline.

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

        # 2. Enrich with Zillow data (if enabled and configured)
        if self.settings.zillow_enrichment_enabled and self.settings.apify_api_token:
            self._enrich_with_zillow(candidates, db)

        # 3. Get AI scores if enabled
        ai_scores = {}
        if self.use_ai_scoring and candidates:
            ai_scores = self._get_ai_scores(candidates)

        # 4. Score all candidates (70% AI + 30% rules)
        scored = self.scorer.batch_score(candidates, ai_scores)

        # 5. Update scores in database
        for listing, score in scored:
            listing.score = score
            listing.status = ListingStatus.SCORED

        # 6. Select diverse set
        selected = self.selector.select(scored)

        # 7. Mark selected listings
        for listing in selected:
            listing.status = ListingStatus.SELECTED

        # 8. Mark non-selected as skipped
        selected_ids = {listing.id for listing in selected}
        for listing, _ in scored:
            if listing.id not in selected_ids:
                listing.status = ListingStatus.SKIPPED

        # 9. Log stats
        stats = self.selector.get_selection_stats(selected)
        enriched_count = sum(
            1 for listing in selected if listing.enrichment_source == "zillow"
        )
        stats["enriched_with_zillow"] = enriched_count
        logger.info("Curation complete", **stats)

        return selected

    def _get_candidates(self, db: Session) -> list[Listing]:
        """Get listings that are candidates for curation."""
        return (
            db.query(Listing)
            .filter(Listing.status.in_([ListingStatus.NEW, ListingStatus.SCORED]))
            .order_by(Listing.received_at.desc())
            .limit(200)
            .all()
        )

    def _enrich_with_zillow(
        self, candidates: list[Listing], db: Session
    ) -> None:
        """Enrich candidates with Zillow data. Skips already-enriched listings."""
        from src.enrichment.zillow_enricher import ZillowEnricher

        to_enrich = [c for c in candidates if not c.zillow_fetched_at]
        if not to_enrich:
            logger.info("All candidates already enriched, skipping")
            return

        try:
            enricher = ZillowEnricher()
            results = enricher.enrich_listings(to_enrich)

            # Store AI reasoning from enrichment if available
            for listing, result in results:
                db.add(listing)

            db.flush()
            logger.info(
                "Zillow enrichment complete",
                enriched=sum(1 for _, r in results if r is not None),
                total=len(to_enrich),
            )

        except Exception as e:
            logger.error(
                "Zillow enrichment failed, continuing with HAR data only",
                error=str(e),
            )
            # Mark all as attempted so we don't retry immediately
            now = datetime.utcnow()
            for listing in to_enrich:
                if not listing.enrichment_source:
                    listing.enrichment_source = "har_only"
                    listing.zillow_fetched_at = now
            db.flush()

    def _get_ai_scores(self, listings: list[Listing]) -> dict[str, float]:
        """Get AI scores for listings using voice-aligned prompt."""
        logger.info("Getting AI scores", count=len(listings))

        # Prepare listing data for Claude — include Zillow data if available
        listing_data = []
        for listing in listings:
            data = {
                "address": listing.address,
                "price": listing.price,
                "bedrooms": listing.bedrooms,
                "bathrooms": listing.bathrooms,
                "sqft": listing.sqft,
                "year_built": listing.year_built,
                "neighborhood": listing.neighborhood,
                "property_type": listing.property_type,
            }

            # Use Zillow description if available, fall back to HAR
            description = listing.zillow_description or listing.description_raw or ""
            data["description"] = description[:1500]

            if listing.zillow_url:
                data["zillow_url"] = listing.zillow_url

            listing_data.append(data)

        try:
            scored_data = self.claude_client.score_listings(listing_data)

            # Build address -> score mapping and store reasoning
            ai_scores = {}
            for item in scored_data:
                address = item.get("address")
                score = item.get("ai_score", 50)
                reasoning = item.get("ai_reasoning", "")
                if address:
                    ai_scores[address] = float(score)

                    # Store reasoning on the listing model
                    for listing in listings:
                        if listing.address == address:
                            listing.ai_score = float(score)
                            listing.ai_reasoning = reasoning
                            break

            logger.info("AI scoring complete", scores_received=len(ai_scores))
            return ai_scores

        except Exception as e:
            logger.error("AI scoring failed, falling back to rule-based", error=str(e))
            return {}

    def check_readiness(self) -> dict:
        """Check if we have enough quality listings for a newsletter."""
        with get_db() as db:
            candidates = self._get_candidates(db)
            scored = self.scorer.batch_score(candidates)

            # With new scoring (0-20 rule-based), threshold > 5 still works
            quality_count = sum(1 for _, score in scored if score > 5)

            ready = quality_count >= self.settings.min_listings_to_publish

            return {
                "ready": ready,
                "total_candidates": len(candidates),
                "quality_candidates": quality_count,
                "minimum_required": self.settings.min_listings_to_publish,
                "checked_at": datetime.utcnow().isoformat(),
            }

    def get_curated_preview(self, limit: int = 5) -> list[dict]:
        """Get a preview of what would be curated without committing."""
        with get_db() as db:
            candidates = self._get_candidates(db)
            scored = self.scorer.batch_score(candidates)
            selected = self.selector.select(scored)

            return [
                {
                    "address": listing.address,
                    "price": listing.price,
                    "neighborhood": listing.neighborhood,
                    "score": listing.score,
                    "enrichment_source": listing.enrichment_source,
                    "ai_reasoning": listing.ai_reasoning,
                }
                for listing in selected[:limit]
            ]
