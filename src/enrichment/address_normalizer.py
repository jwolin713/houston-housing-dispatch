"""Address normalization and matching for HAR-to-Zillow lookups."""

from dataclasses import dataclass

import structlog
import usaddress
from rapidfuzz import fuzz

logger = structlog.get_logger()

# Common street type abbreviations to normalize
STREET_TYPE_MAP = {
    "st": "street", "st.": "street",
    "ave": "avenue", "av": "avenue", "ave.": "avenue",
    "blvd": "boulevard", "blvd.": "boulevard",
    "dr": "drive", "dr.": "drive",
    "ln": "lane", "ln.": "lane",
    "rd": "road", "rd.": "road",
    "ct": "court", "ct.": "court",
    "cir": "circle", "cir.": "circle",
    "pl": "place", "pl.": "place",
    "pkwy": "parkway", "pky": "parkway",
    "hwy": "highway",
    "way": "way",
    "ter": "terrace", "terr": "terrace",
    "trl": "trail",
}

DIRECTIONAL_MAP = {
    "n": "north", "n.": "north",
    "s": "south", "s.": "south",
    "e": "east", "e.": "east",
    "w": "west", "w.": "west",
    "ne": "northeast", "nw": "northwest",
    "se": "southeast", "sw": "southwest",
}


@dataclass
class ParsedAddress:
    """Structured representation of a parsed address."""

    street_number: str
    street_name: str
    street_suffix: str
    direction_prefix: str
    unit_number: str | None
    city: str
    state: str
    zipcode: str
    raw: str

    def search_query(self) -> str:
        """Format address as a search query for Zillow."""
        parts = [self.street_number]
        if self.direction_prefix:
            parts.append(self.direction_prefix)
        parts.append(self.street_name)
        if self.street_suffix:
            parts.append(self.street_suffix)
        if self.unit_number:
            parts.append(f"#{self.unit_number}")

        street = " ".join(parts)
        location_parts = [street]
        if self.city:
            location_parts.append(self.city)
        if self.state:
            location_parts.append(self.state)
        if self.zipcode:
            location_parts.append(self.zipcode[:5])

        return ", ".join(location_parts)

    def normalized_key(self) -> str:
        """Generate a key for exact matching: number|name|zip."""
        return f"{self.street_number}|{self.street_name.lower()}|{self.zipcode[:5]}"


class AddressNormalizer:
    """Parse and match addresses across HAR and Zillow formats."""

    MATCH_THRESHOLD = 85.0

    def parse(self, address: str) -> ParsedAddress | None:
        """
        Parse an address string into structured components.

        Returns None if the address cannot be parsed.
        """
        try:
            tagged, address_type = usaddress.tag(address)
        except usaddress.RepeatedLabelError:
            logger.warning("Could not parse address", address=address)
            return None

        street_number = tagged.get("AddressNumber", "").strip()
        if not street_number:
            logger.warning("No street number found", address=address)
            return None

        street_name = tagged.get("StreetName", "").strip()
        raw_suffix = tagged.get("StreetNamePostType", "").strip()
        raw_direction = tagged.get("StreetNamePreDirectional", "").strip()

        return ParsedAddress(
            street_number=street_number,
            street_name=street_name,
            street_suffix=self._normalize_street_type(raw_suffix),
            direction_prefix=self._normalize_direction(raw_direction),
            unit_number=tagged.get("OccupancyIdentifier", "").strip() or None,
            city=tagged.get("PlaceName", "").strip().rstrip(","),
            state=tagged.get("StateName", "").strip(),
            zipcode=tagged.get("ZipCode", "").strip(),
            raw=address,
        )

    def match(
        self, addr1: ParsedAddress, addr2: ParsedAddress
    ) -> tuple[bool, float]:
        """
        Determine if two addresses match.

        Returns (is_match, confidence_score).
        """
        # Must have same street number
        if addr1.street_number != addr2.street_number:
            return (False, 0.0)

        # Must be in same ZIP if both have it
        if addr1.zipcode and addr2.zipcode:
            if addr1.zipcode[:5] != addr2.zipcode[:5]:
                return (False, 0.0)

        # Fuzzy match street name
        score = fuzz.token_sort_ratio(
            addr1.street_name.lower(),
            addr2.street_name.lower(),
        )

        if score < self.MATCH_THRESHOLD:
            return (False, score)

        # Check unit consistency
        if addr1.unit_number and addr2.unit_number:
            if addr1.unit_number.upper() != addr2.unit_number.upper():
                return (False, score * 0.5)

        return (True, score)

    @staticmethod
    def _normalize_street_type(suffix: str) -> str:
        """Normalize street type to full word."""
        cleaned = suffix.lower().strip().rstrip(".")
        return STREET_TYPE_MAP.get(cleaned, cleaned)

    @staticmethod
    def _normalize_direction(direction: str) -> str:
        """Expand directional abbreviations."""
        cleaned = direction.lower().strip().rstrip(".")
        return DIRECTIONAL_MAP.get(cleaned, cleaned)
