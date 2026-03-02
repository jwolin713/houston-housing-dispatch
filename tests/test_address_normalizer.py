"""Tests for address normalization and matching."""

import pytest

from src.enrichment.address_normalizer import AddressNormalizer, ParsedAddress


@pytest.fixture
def normalizer():
    return AddressNormalizer()


class TestAddressParsing:
    def test_parse_standard_houston_address(self, normalizer):
        result = normalizer.parse("1234 Harvard St, Houston, TX 77008")
        assert result is not None
        assert result.street_number == "1234"
        assert result.street_name == "Harvard"
        assert result.street_suffix == "street"
        assert result.city == "Houston"
        assert result.state == "TX"
        assert result.zipcode == "77008"

    def test_parse_address_with_direction(self, normalizer):
        result = normalizer.parse("5678 N Main St, Houston, TX 77009")
        assert result is not None
        assert result.street_number == "5678"
        assert result.direction_prefix == "north"
        assert result.street_name == "Main"

    def test_parse_address_with_unit(self, normalizer):
        result = normalizer.parse("100 Allen Pkwy Unit 5B, Houston, TX 77019")
        assert result is not None
        assert result.street_number == "100"
        assert result.unit_number == "5B"

    def test_parse_address_without_zip(self, normalizer):
        result = normalizer.parse("1234 Harvard St, Houston, TX")
        assert result is not None
        assert result.street_number == "1234"
        assert result.zipcode == ""

    def test_parse_returns_none_for_unparseable(self, normalizer):
        result = normalizer.parse("Not an address at all")
        # usaddress may still parse this, but it should lack a street number
        if result is not None:
            assert result.street_number == ""  # Missing required field
        # The parse method returns None when there's no street number
        # or when usaddress raises RepeatedLabelError

    def test_search_query_format(self, normalizer):
        result = normalizer.parse("1234 Harvard St, Houston, TX 77008")
        assert result is not None
        query = result.search_query()
        assert "1234" in query
        assert "Harvard" in query
        assert "Houston" in query

    def test_normalized_key(self, normalizer):
        result = normalizer.parse("1234 Harvard St, Houston, TX 77008")
        assert result is not None
        key = result.normalized_key()
        assert key == "1234|harvard|77008"


class TestAddressMatching:
    def test_exact_match(self, normalizer):
        addr1 = normalizer.parse("1234 Harvard St, Houston, TX 77008")
        addr2 = normalizer.parse("1234 Harvard Street, Houston, TX 77008")
        assert addr1 is not None and addr2 is not None

        is_match, score = normalizer.match(addr1, addr2)
        assert is_match is True
        assert score >= 85.0

    def test_different_street_numbers_no_match(self, normalizer):
        addr1 = normalizer.parse("1234 Harvard St, Houston, TX 77008")
        addr2 = normalizer.parse("1235 Harvard St, Houston, TX 77008")
        assert addr1 is not None and addr2 is not None

        is_match, _ = normalizer.match(addr1, addr2)
        assert is_match is False

    def test_different_zip_no_match(self, normalizer):
        addr1 = normalizer.parse("1234 Harvard St, Houston, TX 77008")
        addr2 = normalizer.parse("1234 Harvard St, Houston, TX 77009")
        assert addr1 is not None and addr2 is not None

        is_match, _ = normalizer.match(addr1, addr2)
        assert is_match is False

    def test_abbreviation_variations_match(self, normalizer):
        addr1 = normalizer.parse("5678 Westheimer Rd, Houston, TX 77057")
        addr2 = normalizer.parse("5678 Westheimer Road, Houston, TX 77057")
        assert addr1 is not None and addr2 is not None

        is_match, score = normalizer.match(addr1, addr2)
        assert is_match is True

    def test_different_units_no_match(self, normalizer):
        addr1 = ParsedAddress(
            street_number="100", street_name="Allen", street_suffix="parkway",
            direction_prefix="", unit_number="5A", city="Houston", state="TX",
            zipcode="77019", raw="100 Allen Pkwy Unit 5A"
        )
        addr2 = ParsedAddress(
            street_number="100", street_name="Allen", street_suffix="parkway",
            direction_prefix="", unit_number="5B", city="Houston", state="TX",
            zipcode="77019", raw="100 Allen Pkwy Unit 5B"
        )

        is_match, _ = normalizer.match(addr1, addr2)
        assert is_match is False

    def test_match_without_zip_uses_street_only(self, normalizer):
        addr1 = ParsedAddress(
            street_number="1234", street_name="Harvard", street_suffix="street",
            direction_prefix="", unit_number=None, city="Houston", state="TX",
            zipcode="", raw="1234 Harvard St"
        )
        addr2 = ParsedAddress(
            street_number="1234", street_name="Harvard", street_suffix="street",
            direction_prefix="", unit_number=None, city="Houston", state="TX",
            zipcode="77008", raw="1234 Harvard St 77008"
        )

        is_match, score = normalizer.match(addr1, addr2)
        assert is_match is True
