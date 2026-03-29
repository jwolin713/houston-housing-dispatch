"""Shared test fixtures."""

import pytest

from src.models import Listing, ListingStatus


@pytest.fixture
def sample_listing() -> Listing:
    """A typical Heights listing for testing."""
    return Listing(
        id=1,
        address="1234 Harvard St, Houston, TX 77008",
        price=650_000,
        bedrooms=3,
        bathrooms=2.0,
        sqft=1800,
        year_built=1935,
        neighborhood="Heights",
        property_type="Single Family",
        har_link="https://www.har.com/123",
        description_raw="Charming 1935 bungalow with original hardwood floors and a converted garage apartment.",
        status=ListingStatus.NEW,
    )


@pytest.fixture
def cheap_generic_listing() -> Listing:
    """A cheap but generic listing — should score lower in new system."""
    return Listing(
        id=2,
        address="9876 Generic Blvd, Houston, TX 77099",
        price=180_000,
        bedrooms=3,
        bathrooms=2.0,
        sqft=1400,
        year_built=1998,
        neighborhood="",
        property_type="Single Family",
        har_link="https://www.har.com/456",
        description_raw="Nice home in quiet neighborhood. Move-in ready.",
        status=ListingStatus.NEW,
    )


@pytest.fixture
def character_home_listing() -> Listing:
    """A character home with story potential."""
    return Listing(
        id=3,
        address="567 Montrose Blvd, Houston, TX 77006",
        price=750_000,
        bedrooms=4,
        bathrooms=3.0,
        sqft=2800,
        year_built=1925,
        neighborhood="Montrose",
        property_type="Single Family",
        har_link="https://www.har.com/789",
        description_raw="1925 Montrose Tudor with original leaded glass windows, converted attic studio, and mature pecan trees.",
        status=ListingStatus.NEW,
    )
