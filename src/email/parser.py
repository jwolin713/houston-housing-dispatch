"""HAR email parser to extract listing data from email alerts."""

import re
from dataclasses import dataclass, field
from typing import Optional

import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


@dataclass
class ParsedListing:
    """A listing extracted from an HAR email alert."""

    address: str
    price: int
    bedrooms: int
    bathrooms: float
    sqft: Optional[int] = None
    year_built: Optional[int] = None
    neighborhood: Optional[str] = None
    property_type: Optional[str] = None
    har_link: str = ""
    description: Optional[str] = None
    image_urls: list[str] = field(default_factory=list)


class HAREmailParser:
    """Parser for HAR (Houston Association of Realtors) email alerts."""

    # Common HAR email patterns
    PRICE_PATTERN = re.compile(r"\$[\d,]+")
    BEDS_PATTERN = re.compile(r"(\d+)\s*(?:bed|br|bedroom)", re.IGNORECASE)
    BATHS_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)", re.IGNORECASE)
    SQFT_PATTERN = re.compile(r"([\d,]+)\s*(?:sq\.?\s*ft|sqft|sf)", re.IGNORECASE)
    YEAR_PATTERN = re.compile(r"(?:built|year)[:\s]*(\d{4})", re.IGNORECASE)
    HAR_LINK_PATTERN = re.compile(r"https?://(?:www\.)?har\.com/[^\s\"'<>]+")

    # Houston neighborhoods (common ones)
    NEIGHBORHOODS = [
        "Heights",
        "Montrose",
        "River Oaks",
        "West University",
        "West U",
        "Bellaire",
        "Memorial",
        "Galleria",
        "Midtown",
        "Downtown",
        "EaDo",
        "East Downtown",
        "Museum District",
        "Rice Military",
        "Washington Avenue",
        "Garden Oaks",
        "Oak Forest",
        "Meyerland",
        "Braeswood",
        "Tanglewood",
        "Spring Branch",
        "Katy",
        "Sugar Land",
        "The Woodlands",
        "Pearland",
        "Clear Lake",
        "League City",
        "Humble",
        "Kingwood",
        "Cypress",
    ]

    def __init__(self):
        self.neighborhood_pattern = re.compile(
            "|".join(re.escape(n) for n in self.NEIGHBORHOODS),
            re.IGNORECASE,
        )

    def parse_email(self, html_content: str) -> list[ParsedListing]:
        """
        Parse an HAR email and extract all listings.

        Args:
            html_content: Raw HTML content of the email

        Returns:
            List of ParsedListing objects
        """
        logger.debug("Parsing HAR email", content_length=len(html_content))

        soup = BeautifulSoup(html_content, "lxml")
        listings = []

        # Try multiple parsing strategies
        listings = self._parse_table_format(soup)
        if not listings:
            listings = self._parse_card_format(soup)
        if not listings:
            listings = self._parse_generic_format(soup)

        logger.info("Parsed listings from email", count=len(listings))
        return listings

    def _parse_table_format(self, soup: BeautifulSoup) -> list[ParsedListing]:
        """Parse HAR emails that use table-based layouts."""
        listings = []

        # Look for listing tables or rows
        for table in soup.find_all("table"):
            # Check if this table contains listing data
            text = table.get_text()
            if self.HAR_LINK_PATTERN.search(text) and self.PRICE_PATTERN.search(text):
                listing = self._extract_listing_from_element(table)
                if listing:
                    listings.append(listing)

        return listings

    def _parse_card_format(self, soup: BeautifulSoup) -> list[ParsedListing]:
        """Parse HAR emails that use card-based layouts."""
        listings = []

        # Look for div-based cards
        for div in soup.find_all("div", class_=re.compile(r"listing|property|card")):
            listing = self._extract_listing_from_element(div)
            if listing:
                listings.append(listing)

        return listings

    def _parse_generic_format(self, soup: BeautifulSoup) -> list[ParsedListing]:
        """Fallback parser that looks for HAR links and extracts nearby data."""
        listings = []

        # Find all HAR links
        har_links = self.HAR_LINK_PATTERN.findall(str(soup))
        seen_links = set()

        for link in har_links:
            if link in seen_links:
                continue
            seen_links.add(link)

            # Find the element containing this link
            link_elem = soup.find("a", href=link)
            if not link_elem:
                continue

            # Look at parent elements for listing data
            parent = link_elem.find_parent(["tr", "div", "td", "table"])
            if parent:
                listing = self._extract_listing_from_element(parent, har_link=link)
                if listing:
                    listings.append(listing)

        return listings

    def _extract_listing_from_element(
        self, element, har_link: Optional[str] = None
    ) -> Optional[ParsedListing]:
        """Extract listing data from an HTML element."""
        text = element.get_text(" ", strip=True)
        html = str(element)

        # Extract HAR link
        if not har_link:
            link_match = self.HAR_LINK_PATTERN.search(html)
            if link_match:
                har_link = link_match.group(0)

        if not har_link:
            return None

        # Extract price
        price_match = self.PRICE_PATTERN.search(text)
        if not price_match:
            return None
        price = int(price_match.group(0).replace("$", "").replace(",", ""))

        # Extract address - typically the first substantial text before price
        # or in a specific class/element
        address = self._extract_address(element, text)
        if not address:
            return None

        # Extract beds/baths
        beds = 0
        baths = 0.0
        beds_match = self.BEDS_PATTERN.search(text)
        baths_match = self.BATHS_PATTERN.search(text)
        if beds_match:
            beds = int(beds_match.group(1))
        if baths_match:
            baths = float(baths_match.group(1))

        # Extract sqft
        sqft = None
        sqft_match = self.SQFT_PATTERN.search(text)
        if sqft_match:
            sqft = int(sqft_match.group(1).replace(",", ""))

        # Extract year built
        year_built = None
        year_match = self.YEAR_PATTERN.search(text)
        if year_match:
            year = int(year_match.group(1))
            if 1800 < year < 2030:
                year_built = year

        # Extract neighborhood
        neighborhood = None
        neighborhood_match = self.neighborhood_pattern.search(text)
        if neighborhood_match:
            neighborhood = neighborhood_match.group(0)

        # Extract images
        image_urls = []
        for img in element.find_all("img"):
            src = img.get("src", "")
            if src and "har.com" in src and "photo" in src.lower():
                image_urls.append(src)

        # Extract property type
        property_type = self._extract_property_type(text)

        return ParsedListing(
            address=address,
            price=price,
            bedrooms=beds,
            bathrooms=baths,
            sqft=sqft,
            year_built=year_built,
            neighborhood=neighborhood,
            property_type=property_type,
            har_link=har_link,
            description=None,  # Raw HAR emails typically don't have full descriptions
            image_urls=image_urls,
        )

    def _extract_address(self, element, text: str) -> Optional[str]:
        """Extract address from element, trying multiple strategies."""
        # Strategy 1: Look for address-like elements
        for elem in element.find_all(["h2", "h3", "h4", "strong", "b"]):
            elem_text = elem.get_text(strip=True)
            if self._looks_like_address(elem_text):
                return self._clean_address(elem_text)

        # Strategy 2: Look for link text (often the address)
        for link in element.find_all("a"):
            link_text = link.get_text(strip=True)
            if self._looks_like_address(link_text):
                return self._clean_address(link_text)

        # Strategy 3: First line that looks like an address
        lines = text.split("\n")
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if self._looks_like_address(line):
                return self._clean_address(line)

        return None

    def _looks_like_address(self, text: str) -> bool:
        """Check if text looks like a street address."""
        if not text or len(text) < 10 or len(text) > 200:
            return False

        # Must contain a number followed by text (typical address format)
        if not re.match(r"\d+\s+\w+", text):
            return False

        # Common address keywords
        address_keywords = ["St", "Street", "Ave", "Avenue", "Blvd", "Boulevard",
                          "Dr", "Drive", "Ln", "Lane", "Rd", "Road", "Ct", "Court",
                          "Cir", "Circle", "Way", "Place", "Pl"]

        return any(keyword in text for keyword in address_keywords)

    def _clean_address(self, address: str) -> str:
        """Clean and normalize an address."""
        # Remove extra whitespace
        address = " ".join(address.split())

        # Remove common suffixes like "Houston, TX 77XXX"
        address = re.sub(r",?\s*Houston,?\s*TX\s*\d{5}.*$", "", address, flags=re.IGNORECASE)

        return address.strip()

    def _extract_property_type(self, text: str) -> Optional[str]:
        """Extract property type from text."""
        property_types = {
            "Single Family": ["single family", "single-family", "sfh"],
            "Townhouse": ["townhouse", "townhome", "town home"],
            "Condo": ["condo", "condominium"],
            "Multi-Family": ["multi-family", "multifamily", "duplex", "triplex", "fourplex"],
            "Land": ["lot", "land", "vacant"],
        }

        text_lower = text.lower()
        for prop_type, keywords in property_types.items():
            if any(kw in text_lower for kw in keywords):
                return prop_type

        return None
