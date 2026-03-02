"""Apify client for Zillow property data enrichment."""

from dataclasses import dataclass, field
from typing import Any

import structlog
from apify_client import ApifyClient
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings

logger = structlog.get_logger()


@dataclass
class ZillowResult:
    """Result from a single Zillow property lookup."""

    success: bool
    address: str
    description: str | None = None
    zillow_url: str | None = None
    home_type: str | None = None
    year_built: int | None = None
    lot_size: str | None = None
    raw_data: dict = field(default_factory=dict)
    error: str | None = None


class ApifyZillowClient:
    """Wrapper for Apify Zillow scraper actors."""

    def __init__(
        self,
        api_token: str | None = None,
        actor_id: str | None = None,
    ):
        settings = get_settings()
        self.api_token = api_token or settings.apify_api_token
        self.actor_id = actor_id or settings.apify_zillow_actor_id

        if not self.api_token:
            raise ValueError(
                "Apify API token required. Set APIFY_API_TOKEN in .env"
            )

        self.client = ApifyClient(token=self.api_token)

    def check_health(self) -> dict:
        """Verify Apify API connectivity."""
        try:
            user = self.client.user().get()
            return {
                "healthy": True,
                "username": user.get("username", "unknown"),
            }
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=5, max=60),
    )
    def search_by_addresses(
        self,
        search_queries: list[str],
        timeout_secs: int = 600,
    ) -> list[dict[str, Any]]:
        """
        Search Zillow for properties by address queries.

        Args:
            search_queries: List of address strings to search.
            timeout_secs: Maximum time for the Apify run.

        Returns:
            List of raw result dicts from Apify.
        """
        logger.info(
            "Starting Apify Zillow search",
            query_count=len(search_queries),
            actor=self.actor_id,
        )

        run_input = {
            "addresses": search_queries,
            "propertyStatus": "FOR_SALE",
        }

        run = self.client.actor(self.actor_id).call(
            run_input=run_input,
            timeout_secs=timeout_secs,
        )

        # Collect results from the dataset
        items = list(
            self.client.dataset(run["defaultDatasetId"]).iterate_items()
        )

        logger.info(
            "Apify run complete",
            results_count=len(items),
            run_id=run.get("id"),
        )

        return items

    def parse_result(self, item: dict[str, Any]) -> ZillowResult:
        """
        Parse a raw Apify result into a ZillowResult.

        Handles the maxcopell/zillow-detail-scraper output schema where
        `address` is a dict with streetAddress/city/state/zipcode.
        """
        # Skip invalid results (bad addresses)
        if item.get("isValid") is False:
            return ZillowResult(
                success=False,
                address=item.get("addressOrUrlFromInput", ""),
                error=item.get("invalidReason", "Invalid address"),
            )

        # Address can be a dict or string depending on the actor
        raw_address = item.get("address")
        if isinstance(raw_address, dict):
            parts = [
                raw_address.get("streetAddress", ""),
                raw_address.get("city", ""),
                raw_address.get("state", ""),
                raw_address.get("zipcode", ""),
            ]
            address = ", ".join(p for p in parts if p)
        else:
            address = raw_address or item.get("streetAddress", "")

        description = (
            item.get("description")
            or item.get("homeDescription")
            or ""
        )

        zillow_url = (
            item.get("url")
            or item.get("hdpUrl")
            or item.get("detailUrl")
            or ""
        )
        if zillow_url and not zillow_url.startswith("http"):
            zillow_url = f"https://www.zillow.com{zillow_url}"

        return ZillowResult(
            success=bool(address and description),
            address=address,
            description=description if description else None,
            zillow_url=zillow_url if zillow_url else None,
            home_type=item.get("homeType") or item.get("propertyType"),
            year_built=item.get("yearBuilt"),
            lot_size=item.get("lotSize") or item.get("lotAreaValue"),
            raw_data=item,
        )
