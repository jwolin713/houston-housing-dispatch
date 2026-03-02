"""Property scoring algorithm for newsletter curation.

Redesigned to prioritize editorial character over price. Rules serve as
guardrails (max 20 points) while AI scoring drives selection (70/30 split).

See: docs/brainstorms/2026-03-01-scoring-system-redesign-brainstorm.md
"""

from dataclasses import dataclass

import structlog

from src.models import Listing

logger = structlog.get_logger()


@dataclass
class NeighborhoodData:
    """Median price and desirability data for a neighborhood."""

    median_price: int
    is_premium: bool = False


# Houston neighborhood price data (approximate medians)
NEIGHBORHOOD_DATA: dict[str, NeighborhoodData] = {
    # Premium neighborhoods - strong editorial identity
    "River Oaks": NeighborhoodData(median_price=2_500_000, is_premium=True),
    "West University": NeighborhoodData(median_price=1_400_000, is_premium=True),
    "West U": NeighborhoodData(median_price=1_400_000, is_premium=True),
    "Tanglewood": NeighborhoodData(median_price=1_800_000, is_premium=True),
    "Memorial": NeighborhoodData(median_price=900_000, is_premium=True),
    "Bellaire": NeighborhoodData(median_price=700_000, is_premium=True),
    # Desirable inner loop neighborhoods
    "Heights": NeighborhoodData(median_price=650_000, is_premium=True),
    "Montrose": NeighborhoodData(median_price=600_000, is_premium=True),
    "Museum District": NeighborhoodData(median_price=500_000, is_premium=True),
    "Rice Military": NeighborhoodData(median_price=550_000, is_premium=True),
    "Washington Avenue": NeighborhoodData(median_price=500_000, is_premium=False),
    "Midtown": NeighborhoodData(median_price=400_000, is_premium=False),
    "EaDo": NeighborhoodData(median_price=450_000, is_premium=False),
    "East Downtown": NeighborhoodData(median_price=450_000, is_premium=False),
    # Other desirable areas
    "Garden Oaks": NeighborhoodData(median_price=550_000, is_premium=False),
    "Oak Forest": NeighborhoodData(median_price=500_000, is_premium=False),
    "Meyerland": NeighborhoodData(median_price=450_000, is_premium=False),
    "Braeswood": NeighborhoodData(median_price=400_000, is_premium=False),
    "Spring Branch": NeighborhoodData(median_price=400_000, is_premium=False),
    "Galleria": NeighborhoodData(median_price=350_000, is_premium=False),
    "Downtown": NeighborhoodData(median_price=350_000, is_premium=False),
    # Suburbs
    "Katy": NeighborhoodData(median_price=380_000, is_premium=False),
    "Sugar Land": NeighborhoodData(median_price=400_000, is_premium=False),
    "The Woodlands": NeighborhoodData(median_price=450_000, is_premium=False),
    "Pearland": NeighborhoodData(median_price=350_000, is_premium=False),
    "Clear Lake": NeighborhoodData(median_price=350_000, is_premium=False),
    "League City": NeighborhoodData(median_price=350_000, is_premium=False),
    "Humble": NeighborhoodData(median_price=300_000, is_premium=False),
    "Kingwood": NeighborhoodData(median_price=350_000, is_premium=False),
    "Cypress": NeighborhoodData(median_price=380_000, is_premium=False),
}

# Default for unknown neighborhoods
DEFAULT_NEIGHBORHOOD_DATA = NeighborhoodData(median_price=400_000, is_premium=False)


class ListingScorer:
    """Scores listings for newsletter curation.

    AI-primary scoring (default 70% AI, 30% rules). Rules serve as guardrails
    only — max 20 points across neighborhood context, sanity checks, and a
    small price bonus. The AI handles holistic editorial judgment.
    """

    def __init__(self, ai_weight: float = 0.7):
        """
        Initialize the scorer.

        Args:
            ai_weight: Weight for AI scores (0-1). Rule-based gets (1 - ai_weight).
                       Default 0.7 for AI-primary scoring.
        """
        self.ai_weight = ai_weight

    def score(self, listing: Listing, ai_score: float | None = None) -> float:
        """
        Calculate a composite score for a listing.

        When AI score is available: final = (AI * 0.7) + (rules * 0.3)
        When AI score is unavailable: final = rules only (max 20)

        Args:
            listing: The listing to score
            ai_score: Optional AI-generated score (0-100)

        Returns:
            Score from 0-100
        """
        rule_score = self._calculate_rule_score(listing)

        if ai_score is not None and self.ai_weight > 0:
            # Scale rule score (0-20) to 0-100 for fair blending
            rule_score_normalized = rule_score * 5.0  # 20 * 5 = 100
            final_score = (
                ai_score * self.ai_weight
                + rule_score_normalized * (1 - self.ai_weight)
            )
        else:
            # No AI score — use rule score scaled to 0-100
            final_score = rule_score * 5.0

        logger.debug(
            "Scored listing",
            address=listing.address,
            rule_score=rule_score,
            ai_score=ai_score,
            final_score=final_score,
        )

        return min(100.0, max(0.0, final_score))

    def _calculate_rule_score(self, listing: Listing) -> float:
        """Calculate guardrail score (max 20 points).

        Components:
        - Neighborhood editorial potential: 0-10 points
        - Sanity checks: 0-5 points
        - Small price bonus: 0-5 points
        """
        score = 0.0
        score += self._score_neighborhood(listing)
        score += self._score_sanity(listing)
        score += self._score_price_bonus(listing)
        return score

    def _score_neighborhood(self, listing: Listing) -> float:
        """Score neighborhood for editorial potential (0-10 points).

        Premium neighborhoods with strong identity score highest because
        they generate the best insider-voice content.
        """
        neighborhood = listing.neighborhood or ""
        data = NEIGHBORHOOD_DATA.get(neighborhood)

        if data and data.is_premium:
            return 10  # Strong editorial identity
        elif data:
            return 6   # Known neighborhood
        return 3  # Unknown — might still be interesting

    def _score_sanity(self, listing: Listing) -> float:
        """Basic sanity checks (0-5 points).

        Filters out obvious junk without being price-driven.
        """
        score = 0.0
        neighborhood = listing.neighborhood or ""
        data = NEIGHBORHOOD_DATA.get(neighborhood, DEFAULT_NEIGHBORHOOD_DATA)

        # Not wildly overpriced for area (3 points)
        if listing.price > 0:
            ratio = listing.price / data.median_price
            if ratio <= 2.0:
                score += 3  # Reasonable for area

        # Has reasonable size (2 points)
        if listing.sqft and listing.sqft >= 500:
            score += 2

        return score

    def _score_price_bonus(self, listing: Listing) -> float:
        """Small bonus for notable value — not a primary driver (0-5 points)."""
        neighborhood = listing.neighborhood or ""
        data = NEIGHBORHOOD_DATA.get(neighborhood, DEFAULT_NEIGHBORHOOD_DATA)

        if listing.price <= 0:
            return 0

        ratio = listing.price / data.median_price

        if ratio < 0.7:
            return 5  # Significantly underpriced — notable
        elif ratio < 0.85:
            return 3  # Moderately underpriced
        return 0

    def batch_score(
        self,
        listings: list[Listing],
        ai_scores: dict[str, float] | None = None,
    ) -> list[tuple[Listing, float]]:
        """
        Score a batch of listings.

        Args:
            listings: List of listings to score
            ai_scores: Optional dict mapping address to AI score

        Returns:
            List of (listing, score) tuples, sorted by score descending
        """
        ai_scores = ai_scores or {}

        scored = []
        for listing in listings:
            ai_score = ai_scores.get(listing.address)
            score = self.score(listing, ai_score)
            scored.append((listing, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        return scored
