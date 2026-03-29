"""Tests for neighborhood resolution from Zillow data and zip codes."""

import pytest

from src.enrichment.neighborhood_resolver import NeighborhoodResolver


@pytest.fixture
def resolver():
    return NeighborhoodResolver()


class TestZipCodeResolution:
    def test_heights_zip(self, resolver):
        assert resolver.resolve("1100 Harvard St, Houston TX 77008") == "Heights"

    def test_montrose_zip(self, resolver):
        assert resolver.resolve("12 Hyde Park Blvd, Houston TX 77006") == "Montrose"

    def test_river_oaks_zip(self, resolver):
        assert resolver.resolve("2440 Inwood Dr, Houston TX 77019") == "River Oaks"

    def test_spring_branch_zip(self, resolver):
        assert resolver.resolve("947 Blackshire Ln, Houston TX 77055") == "Spring Branch"

    def test_eado_zip(self, resolver):
        assert resolver.resolve("2503 Dallas St, Houston TX 77003") == "EaDo"

    def test_west_university_zip(self, resolver):
        assert resolver.resolve("5200 Weslayan St, Houston TX 77005") == "West University"

    def test_galleria_zip(self, resolver):
        assert resolver.resolve("2829 Timmons Ln, Houston TX 77027") == "Galleria"

    def test_katy_zip(self, resolver):
        assert resolver.resolve("1234 Some St, Katy TX 77494") == "Katy"

    def test_unknown_zip_returns_none(self, resolver):
        assert resolver.resolve("123 Main St, Smalltown TX 12345") is None

    def test_no_zip_returns_none(self, resolver):
        assert resolver.resolve("123 Main St") is None

    def test_zip_in_messy_text(self, resolver):
        """Zip extraction works even from full listing text."""
        text = "New Listing 947 Blackshire Ln Houston TX 77055 3 bedrooms $859,000"
        assert resolver.resolve(text) == "Spring Branch"


class TestZillowNeighborhoodExtraction:
    def test_zillow_neighborhood_field(self, resolver):
        raw_data = {"neighborhood": "Montrose"}
        result = resolver.resolve("123 Main St", zillow_raw_data=raw_data)
        assert result == "Montrose"

    def test_zillow_neighborhood_region_field(self, resolver):
        raw_data = {"neighborhoodRegion": "Heights"}
        result = resolver.resolve("123 Main St", zillow_raw_data=raw_data)
        assert result == "Heights"

    def test_zillow_reso_facts_subdivision(self, resolver):
        raw_data = {"resoFacts": {"subdivisionName": "River Oaks"}}
        result = resolver.resolve("123 Main St", zillow_raw_data=raw_data)
        assert result == "River Oaks"

    def test_zillow_takes_priority_over_zip(self, resolver):
        """Zillow neighborhood should override zip-based resolution."""
        raw_data = {"neighborhood": "Museum District"}
        # 77006 would map to Montrose, but Zillow says Museum District
        result = resolver.resolve(
            "123 Main St, Houston TX 77006", zillow_raw_data=raw_data
        )
        assert result == "Museum District"

    def test_zillow_empty_string_falls_through(self, resolver):
        raw_data = {"neighborhood": "  "}
        result = resolver.resolve("123 Main St, Houston TX 77008", zillow_raw_data=raw_data)
        assert result == "Heights"  # Falls through to zip

    def test_zillow_none_falls_through(self, resolver):
        raw_data = {"neighborhood": None}
        result = resolver.resolve("123 Main St, Houston TX 77008", zillow_raw_data=raw_data)
        assert result == "Heights"  # Falls through to zip
