"""Orchestrates Zillow enrichment for HAR listings."""

from datetime import datetime

import structlog

from src.enrichment.address_normalizer import AddressNormalizer, ParsedAddress
from src.enrichment.apify_client import ApifyZillowClient, ZillowResult
from src.models import Listing

logger = structlog.get_logger()


class ZillowEnricher:
    """Enriches HAR listings with Zillow property data."""

    def __init__(
        self,
        apify_client: ApifyZillowClient | None = None,
        normalizer: AddressNormalizer | None = None,
    ):
        self.apify_client = apify_client or ApifyZillowClient()
        self.normalizer = normalizer or AddressNormalizer()

    def enrich_listings(
        self,
        listings: list[Listing],
    ) -> list[tuple[Listing, ZillowResult | None]]:
        """
        Enrich a batch of listings with Zillow data.

        Skips listings that already have enrichment data.

        Args:
            listings: Listings to enrich.

        Returns:
            List of (listing, result) tuples. Result is None if enrichment
            was skipped or failed.
        """
        # Filter to only unenriched listings
        to_enrich = [item for item in listings if not item.zillow_fetched_at]

        if not to_enrich:
            logger.info("All listings already enriched, skipping")
            return [(item, None) for item in listings]

        logger.info(
            "Enriching listings with Zillow data",
            total=len(listings),
            to_enrich=len(to_enrich),
        )

        # Parse addresses and build search queries
        parsed_addresses: dict[int, ParsedAddress] = {}
        search_queries: list[str] = []
        query_to_listing_id: dict[int, int] = {}  # query index -> listing id

        for listing in to_enrich:
            parsed = self.normalizer.parse(listing.address)
            if parsed:
                parsed_addresses[listing.id] = parsed
                query_idx = len(search_queries)
                search_queries.append(parsed.search_query())
                query_to_listing_id[query_idx] = listing.id
            else:
                logger.warning(
                    "Could not parse address, skipping enrichment",
                    address=listing.address,
                )

        if not search_queries:
            logger.warning("No parseable addresses to enrich")
            return [(item, None) for item in listings]

        # Batch search via Apify
        try:
            raw_results = self.apify_client.search_by_addresses(search_queries)
        except Exception as e:
            logger.error("Apify batch search failed", error=str(e))
            # Mark all as attempted but failed
            now = datetime.utcnow()
            for listing in to_enrich:
                listing.enrichment_source = "har_only"
                listing.zillow_fetched_at = now
            return [(item, None) for item in listings]

        # Parse Apify results
        zillow_results = [
            self.apify_client.parse_result(item) for item in raw_results
        ]

        # Match Zillow results back to HAR listings by address
        matched = self._match_results(
            to_enrich, parsed_addresses, zillow_results
        )

        # Apply enrichment data to listings
        now = datetime.utcnow()
        results: list[tuple[Listing, ZillowResult | None]] = []

        for listing in listings:
            if listing.id in matched:
                result = matched[listing.id]
                listing.zillow_description = result.description
                listing.zillow_url = result.zillow_url
                listing.enrichment_source = "zillow"
                listing.zillow_fetched_at = now
                results.append((listing, result))
            elif listing in to_enrich:
                listing.enrichment_source = "har_only"
                listing.zillow_fetched_at = now
                results.append((listing, None))
            else:
                # Already enriched previously
                results.append((listing, None))

        enriched_count = sum(1 for _, r in results if r is not None)
        logger.info(
            "Enrichment complete",
            enriched=enriched_count,
            total=len(listings),
            match_rate=f"{enriched_count / len(to_enrich) * 100:.0f}%"
            if to_enrich
            else "N/A",
        )

        return results

    def _match_results(
        self,
        listings: list[Listing],
        parsed_addresses: dict[int, ParsedAddress],
        zillow_results: list[ZillowResult],
    ) -> dict[int, ZillowResult]:
        """
        Match Zillow results back to HAR listings using address matching.

        Returns dict mapping listing_id -> best ZillowResult match.
        """
        # Parse Zillow addresses
        zillow_parsed: list[tuple[ZillowResult, ParsedAddress | None]] = []
        for result in zillow_results:
            if not result.success:
                continue
            parsed = self.normalizer.parse(result.address)
            zillow_parsed.append((result, parsed))

        matched: dict[int, ZillowResult] = {}

        for listing in listings:
            if listing.id not in parsed_addresses:
                continue

            har_addr = parsed_addresses[listing.id]
            best_match: ZillowResult | None = None
            best_score = 0.0

            for result, zillow_addr in zillow_parsed:
                if zillow_addr is None:
                    continue

                is_match, score = self.normalizer.match(har_addr, zillow_addr)
                if is_match and score > best_score:
                    best_match = result
                    best_score = score

            if best_match:
                matched[listing.id] = best_match
                logger.debug(
                    "Matched listing to Zillow",
                    har_address=listing.address,
                    zillow_address=best_match.address,
                    confidence=best_score,
                )

        return matched
