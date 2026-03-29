"""Resolve human-friendly neighborhood names from addresses and Zillow data.

The HAR MLS "Located in" field gives subdivision names (e.g., "Somerset Green
Sec 5") that nobody recognizes. This module resolves real neighborhood names
using Zillow data when available, with a Houston zip code mapping as fallback.
"""

import re
from typing import Any

import structlog

logger = structlog.get_logger()

# Houston zip code → recognized neighborhood name.
# When a zip spans multiple neighborhoods, we pick the most commonly
# associated one. This is intentionally a "good enough" mapping — the
# Zillow neighborhood field is the preferred source when available.
HOUSTON_ZIP_TO_NEIGHBORHOOD: dict[str, str] = {
    # Inner Loop - Core
    "77002": "Downtown",
    "77003": "EaDo",
    "77004": "Third Ward",
    "77005": "West University",
    "77006": "Montrose",
    "77007": "Rice Military",
    "77008": "Heights",
    "77009": "Heights",
    "77010": "Downtown",
    "77019": "River Oaks",
    "77098": "Montrose",
    # Inner Loop - Established
    "77018": "Garden Oaks",
    "77022": "Near Northside",
    "77024": "Memorial",
    "77025": "Braeswood",
    "77026": "Fifth Ward",
    "77027": "Galleria",
    "77030": "Medical Center",
    "77035": "Meyerland",
    "77036": "Sharpstown",
    "77042": "Westchase",
    "77043": "Spring Branch",
    "77054": "Medical Center",
    "77055": "Spring Branch",
    "77056": "Galleria",
    "77057": "Galleria",
    "77096": "Meyerland",
    # Bellaire (independent city)
    "77401": "Bellaire",
    # Suburbs - Katy
    "77449": "Katy",
    "77450": "Katy",
    "77493": "Katy",
    "77494": "Katy",
    # Suburbs - Sugar Land
    "77478": "Sugar Land",
    "77479": "Sugar Land",
    "77498": "Sugar Land",
    # Suburbs - The Woodlands
    "77380": "The Woodlands",
    "77381": "The Woodlands",
    "77382": "The Woodlands",
    "77384": "The Woodlands",
    "77385": "The Woodlands",
    # Suburbs - Humble / Kingwood
    "77338": "Humble",
    "77339": "Kingwood",
    "77345": "Kingwood",
    "77346": "Kingwood",
    # Suburbs - Cypress
    "77429": "Cypress",
    "77433": "Cypress",
    # Suburbs - South
    "77581": "Pearland",
    "77584": "Pearland",
    "77058": "Clear Lake",
    "77059": "Clear Lake",
    "77062": "Clear Lake",
    "77573": "League City",
    # Other notable areas
    "77011": "East End",
    "77012": "Magnolia Park",
    "77016": "Acres Homes",
    "77020": "Denver Harbor",
    "77021": "Third Ward",
    "77023": "East End",
    "77028": "Kashmere Gardens",
    "77033": "South Park",
    "77034": "Ellington",
    "77040": "Northwest Houston",
    "77041": "Northwest Houston",
    "77044": "Lake Houston",
    "77045": "Sunnyside",
    "77046": "Afton Oaks",
    "77047": "South Houston",
    "77048": "South Houston",
    "77051": "South Park",
    "77053": "Fort Bend",
    "77060": "North Houston",
    "77061": "Gulfgate",
    "77063": "Sharpstown",
    "77064": "Willowbrook",
    "77065": "Cypress",
    "77066": "North Houston",
    "77067": "North Houston",
    "77068": "Champions",
    "77069": "Champions",
    "77070": "Willowbrook",
    "77071": "Sharpstown",
    "77072": "Alief",
    "77074": "Sharpstown",
    "77075": "South Belt",
    "77076": "North Houston",
    "77077": "Energy Corridor",
    "77079": "Energy Corridor",
    "77080": "Spring Branch",
    "77081": "Meyerland",
    "77082": "Westchase",
    "77083": "Alief",
    "77084": "Bear Creek",
    "77085": "South Houston",
    "77086": "North Houston",
    "77087": "South Houston",
    "77088": "Acres Homes",
    "77089": "South Belt",
    "77090": "Champions",
    "77091": "Garden Oaks",
    "77092": "Spring Branch",
    "77093": "North Houston",
    "77094": "Energy Corridor",
    "77095": "Cypress",
    "77099": "Westchase",
}

_ZIP_PATTERN = re.compile(r"\b(77\d{3})\b")


class NeighborhoodResolver:
    """Resolves recognized neighborhood names from Zillow data or zip codes."""

    def resolve(
        self,
        address: str,
        zillow_raw_data: dict[str, Any] | None = None,
    ) -> str | None:
        """Resolve a human-friendly neighborhood name.

        Priority:
        1. Zillow neighborhood field (most accurate)
        2. Houston zip code mapping (reliable fallback)

        Args:
            address: Full address string (must include zip for fallback).
            zillow_raw_data: Raw dict from Apify Zillow scraper, if available.

        Returns:
            Recognized neighborhood name, or None if unresolvable.
        """
        # Try Zillow first
        if zillow_raw_data:
            zillow_neighborhood = self._extract_zillow_neighborhood(
                zillow_raw_data
            )
            if zillow_neighborhood:
                logger.debug(
                    "Resolved neighborhood from Zillow",
                    neighborhood=zillow_neighborhood,
                    address=address,
                )
                return zillow_neighborhood

        # Fallback to zip code
        neighborhood = self._resolve_from_zip(address)
        if neighborhood:
            logger.debug(
                "Resolved neighborhood from zip code",
                neighborhood=neighborhood,
                address=address,
            )
        return neighborhood

    def _extract_zillow_neighborhood(
        self, raw_data: dict[str, Any]
    ) -> str | None:
        """Extract neighborhood name from Zillow raw API data."""
        # The Apify Zillow detail scraper can return neighborhood in
        # several possible fields depending on the listing
        for key in ("neighborhood", "neighborhoodRegion", "subdivision"):
            value = raw_data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Check nested resoFacts
        reso_facts = raw_data.get("resoFacts")
        if isinstance(reso_facts, dict):
            for key in ("subdivisionName", "neighborhood"):
                value = reso_facts.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return None

    def _resolve_from_zip(self, address: str) -> str | None:
        """Extract zip code from address and look up neighborhood."""
        match = _ZIP_PATTERN.search(address)
        if not match:
            return None
        return HOUSTON_ZIP_TO_NEIGHBORHOOD.get(match.group(1))
