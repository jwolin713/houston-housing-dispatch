"""Property scoring algorithm for newsletter curation."""

from dataclasses import dataclass
from typing import Optional

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
    # Premium neighborhoods
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

# Keywords that indicate interesting features
POSITIVE_KEYWORDS = [
    "pool", "renovated", "remodeled", "updated", "views", "corner lot",
    "guest house", "garage apartment", "downtown views", "skyline",
    "original hardwood", "chef's kitchen", "wine cellar", "elevator",
    "smart home", "solar", "generator", "gated", "waterfront",
    "acreage", "estate", "historic", "mid-century", "modern",
]


class ListingScorer:
    """Scores listings for newsletter interest and curation."""

    def __init__(self, ai_weight: float = 0.4):
        """
        Initialize the scorer.

        Args:
            ai_weight: How much to weight AI scores (0-1). Rule-based gets (1 - ai_weight).
        """
        self.ai_weight = ai_weight

    def score(self, listing: Listing, ai_score: Optional[float] = None) -> float:
        """
        Calculate a composite score for a listing.

        Args:
            listing: The listing to score
            ai_score: Optional AI-generated score (0-100)

        Returns:
            Score from 0-100
        """
        # Calculate rule-based score
        rule_score = self._calculate_rule_score(listing)

        # Combine with AI score if available
        if ai_score is not None and self.ai_weight > 0:
            final_score = (
                rule_score * (1 - self.ai_weight) +
                ai_score * self.ai_weight
            )
        else:
            final_score = rule_score

        logger.debug(
            "Scored listing",
            address=listing.address,
            rule_score=rule_score,
            ai_score=ai_score,
            final_score=final_score,
        )

        return min(100, max(0, final_score))

    def _calculate_rule_score(self, listing: Listing) -> float:
        """Calculate score based on rule-based heuristics."""
        score = 0.0

        # 1. Price value (underpriced for area) - up to 30 points
        score += self._score_price_value(listing)

        # 2. Architectural interest (age) - up to 20 points
        score += self._score_architecture(listing)

        # 3. Unique features (keywords) - up to 20 points
        score += self._score_features(listing)

        # 4. Neighborhood desirability - up to 15 points
        score += self._score_neighborhood(listing)

        # 5. Size/value ratio - up to 15 points
        score += self._score_size_value(listing)

        return score

    def _score_price_value(self, listing: Listing) -> float:
        """Score based on price relative to area median."""
        neighborhood = listing.neighborhood or ""
        data = NEIGHBORHOOD_DATA.get(neighborhood, DEFAULT_NEIGHBORHOOD_DATA)

        if listing.price <= 0:
            return 0

        ratio = listing.price / data.median_price

        if ratio < 0.7:
            return 30  # Significantly underpriced
        elif ratio < 0.85:
            return 20  # Moderately underpriced
        elif ratio < 1.0:
            return 10  # Slightly underpriced
        elif ratio > 1.5:
            return 5   # Premium/luxury gets some points for interest
        return 0

    def _score_architecture(self, listing: Listing) -> float:
        """Score based on architectural interest (age)."""
        if not listing.year_built:
            return 5  # Small bonus for unknown (might be interesting)

        year = listing.year_built
        current_year = 2026

        if year < 1930:
            return 20  # Very historic
        elif year < 1950:
            return 15  # Historic
        elif year < 1970:
            return 10  # Mid-century
        elif year > current_year - 2:
            return 15  # New construction
        elif year > current_year - 5:
            return 10  # Recent construction

        return 0

    def _score_features(self, listing: Listing) -> float:
        """Score based on unique features mentioned in description."""
        description = (listing.description_raw or "").lower()

        # Count keyword matches
        matches = sum(1 for kw in POSITIVE_KEYWORDS if kw in description)

        # Cap at 20 points (2 points per keyword match, max 10 matches)
        return min(20, matches * 2)

    def _score_neighborhood(self, listing: Listing) -> float:
        """Score based on neighborhood desirability."""
        neighborhood = listing.neighborhood or ""
        data = NEIGHBORHOOD_DATA.get(neighborhood)

        if data and data.is_premium:
            return 15
        elif data:
            return 8
        return 3  # Unknown neighborhood gets small bonus

    def _score_size_value(self, listing: Listing) -> float:
        """Score based on price per square foot value."""
        if not listing.sqft or listing.sqft <= 0 or listing.price <= 0:
            return 0

        price_per_sqft = listing.price / listing.sqft

        # Houston averages around $200-250/sqft for decent areas
        if price_per_sqft < 150:
            return 15  # Great value
        elif price_per_sqft < 200:
            return 10  # Good value
        elif price_per_sqft < 250:
            return 5   # Fair value
        elif price_per_sqft > 500:
            return 5   # Luxury premium (interesting for different reasons)

        return 0

    def batch_score(
        self,
        listings: list[Listing],
        ai_scores: Optional[dict[str, float]] = None,
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

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored
