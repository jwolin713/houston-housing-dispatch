"""Diversity-aware listing selector for balanced newsletters."""

from collections import defaultdict
from typing import Optional

import structlog

from src.models import Listing

logger = structlog.get_logger()


class DiversitySelector:
    """Selects listings while maintaining neighborhood and price diversity."""

    def __init__(
        self,
        max_per_neighborhood: int = 3,
        target_count: int = 18,
        price_buckets: int = 4,
    ):
        """
        Initialize the selector.

        Args:
            max_per_neighborhood: Maximum listings from any single neighborhood
            target_count: Target number of listings to select
            price_buckets: Number of price tiers to balance
        """
        self.max_per_neighborhood = max_per_neighborhood
        self.target_count = target_count
        self.price_buckets = price_buckets

    def select(
        self,
        scored_listings: list[tuple[Listing, float]],
        min_count: Optional[int] = None,
        max_count: Optional[int] = None,
    ) -> list[Listing]:
        """
        Select listings with diversity constraints.

        Args:
            scored_listings: List of (listing, score) tuples, pre-sorted by score descending
            min_count: Minimum listings to return (default: target_count - 5)
            max_count: Maximum listings to return (default: target_count + 2)

        Returns:
            Selected listings in recommended order
        """
        min_count = min_count or max(self.target_count - 5, 5)
        max_count = max_count or self.target_count + 2

        if not scored_listings:
            logger.warning("No listings to select from")
            return []

        # Track selections
        selected: list[Listing] = []
        neighborhood_counts: dict[str, int] = defaultdict(int)
        price_tier_counts: dict[int, int] = defaultdict(int)

        # Calculate price tiers
        prices = [l.price for l, _ in scored_listings if l.price > 0]
        if not prices:
            return []

        price_ranges = self._calculate_price_tiers(prices)

        logger.debug(
            "Starting selection",
            candidates=len(scored_listings),
            target=self.target_count,
            price_tiers=price_ranges,
        )

        # First pass: select top listings respecting constraints
        for listing, score in scored_listings:
            if len(selected) >= max_count:
                break

            neighborhood = listing.neighborhood or "Unknown"
            price_tier = self._get_price_tier(listing.price, price_ranges)

            # Check neighborhood constraint
            if neighborhood_counts[neighborhood] >= self.max_per_neighborhood:
                logger.debug(
                    "Skipping due to neighborhood limit",
                    address=listing.address,
                    neighborhood=neighborhood,
                )
                continue

            # Add listing
            selected.append(listing)
            neighborhood_counts[neighborhood] += 1
            price_tier_counts[price_tier] += 1

        # If we don't have enough, relax constraints
        if len(selected) < min_count:
            logger.info(
                "Relaxing constraints to meet minimum",
                current=len(selected),
                minimum=min_count,
            )
            for listing, score in scored_listings:
                if len(selected) >= min_count:
                    break
                if listing not in selected:
                    selected.append(listing)

        # Reorder for good newsletter flow
        ordered = self._order_for_newsletter(selected, price_ranges)

        logger.info(
            "Selection complete",
            selected=len(ordered),
            neighborhoods=len(neighborhood_counts),
            neighborhood_distribution=dict(neighborhood_counts),
        )

        return ordered

    def _calculate_price_tiers(self, prices: list[int]) -> list[tuple[int, int]]:
        """Calculate price tier ranges."""
        sorted_prices = sorted(prices)
        n = len(sorted_prices)

        if n < self.price_buckets:
            # Not enough listings for full buckets
            return [(0, max(sorted_prices) + 1)]

        tiers = []
        bucket_size = n // self.price_buckets

        for i in range(self.price_buckets):
            start_idx = i * bucket_size
            end_idx = (i + 1) * bucket_size if i < self.price_buckets - 1 else n

            low = sorted_prices[start_idx]
            high = sorted_prices[end_idx - 1] if end_idx <= n else sorted_prices[-1]

            tiers.append((low, high + 1))

        return tiers

    def _get_price_tier(self, price: int, tiers: list[tuple[int, int]]) -> int:
        """Get the tier index for a price."""
        for i, (low, high) in enumerate(tiers):
            if low <= price < high:
                return i
        return len(tiers) - 1

    def _order_for_newsletter(
        self,
        listings: list[Listing],
        price_ranges: list[tuple[int, int]],
    ) -> list[Listing]:
        """
        Order listings for good newsletter flow.

        Strategy:
        - Group by neighborhood
        - Within groups, order by price (interesting variety)
        - Interleave groups to avoid monotony
        """
        # Group by neighborhood
        by_neighborhood: dict[str, list[Listing]] = defaultdict(list)
        for listing in listings:
            neighborhood = listing.neighborhood or "Other"
            by_neighborhood[neighborhood].append(listing)

        # Sort within each neighborhood by price
        for listings_list in by_neighborhood.values():
            listings_list.sort(key=lambda x: x.price, reverse=True)

        # Interleave neighborhoods
        ordered = []
        neighborhoods = list(by_neighborhood.keys())

        # Start with premium neighborhoods if available
        premium = ["Heights", "Montrose", "River Oaks", "West University", "West U", "Memorial"]
        neighborhoods.sort(key=lambda n: (n not in premium, n))

        idx = 0
        while any(by_neighborhood.values()):
            n = neighborhoods[idx % len(neighborhoods)]
            if by_neighborhood[n]:
                ordered.append(by_neighborhood[n].pop(0))
            idx += 1

            # Remove empty neighborhoods
            if not by_neighborhood[n]:
                neighborhoods.remove(n)
                if not neighborhoods:
                    break

        return ordered

    def get_selection_stats(
        self,
        selected: list[Listing],
    ) -> dict:
        """Get statistics about the selected listings."""
        if not selected:
            return {"count": 0}

        prices = [l.price for l in selected]
        neighborhoods = [l.neighborhood or "Unknown" for l in selected]
        sqfts = [l.sqft for l in selected if l.sqft]

        by_neighborhood = defaultdict(int)
        for n in neighborhoods:
            by_neighborhood[n] += 1

        return {
            "count": len(selected),
            "price_min": min(prices),
            "price_max": max(prices),
            "price_avg": sum(prices) // len(prices),
            "sqft_avg": sum(sqfts) // len(sqfts) if sqfts else None,
            "neighborhoods": dict(by_neighborhood),
            "unique_neighborhoods": len(by_neighborhood),
        }
