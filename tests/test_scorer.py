"""Tests for the redesigned scoring system."""

import pytest

from src.curation.scorer import ListingScorer
from src.models import Listing, ListingStatus


@pytest.fixture
def scorer():
    return ListingScorer(ai_weight=0.7)


class TestRuleBasedScoring:
    """Test the guardrail rule-based scoring (max 20 points)."""

    def test_premium_neighborhood_scores_10(self, scorer, sample_listing):
        score = scorer._score_neighborhood(sample_listing)
        assert score == 10  # Heights is premium

    def test_known_neighborhood_scores_6(self, scorer):
        listing = Listing(
            address="test", price=400_000, bedrooms=3, bathrooms=2,
            neighborhood="Garden Oaks", har_link="test",
            status=ListingStatus.NEW,
        )
        score = scorer._score_neighborhood(listing)
        assert score == 6

    def test_unknown_neighborhood_scores_3(self, scorer, cheap_generic_listing):
        score = scorer._score_neighborhood(cheap_generic_listing)
        assert score == 3  # Empty neighborhood

    def test_sanity_reasonable_price_and_size(self, scorer, sample_listing):
        score = scorer._score_sanity(sample_listing)
        assert score == 5  # 3 (reasonable price) + 2 (reasonable size)

    def test_sanity_no_sqft(self, scorer):
        listing = Listing(
            address="test", price=400_000, bedrooms=3, bathrooms=2,
            sqft=None, neighborhood="Heights", har_link="test",
            status=ListingStatus.NEW,
        )
        score = scorer._score_sanity(listing)
        assert score == 3  # Only price check passes

    def test_sanity_tiny_unit(self, scorer):
        listing = Listing(
            address="test", price=400_000, bedrooms=1, bathrooms=1,
            sqft=300, neighborhood="Heights", har_link="test",
            status=ListingStatus.NEW,
        )
        score = scorer._score_sanity(listing)
        assert score == 3  # Only price check passes, sqft too small

    def test_price_bonus_significantly_underpriced(self, scorer):
        listing = Listing(
            address="test", price=300_000, bedrooms=3, bathrooms=2,
            neighborhood="Heights", har_link="test",
            status=ListingStatus.NEW,
        )
        # Heights median is 650k, 300k/650k = 0.46 < 0.7
        score = scorer._score_price_bonus(listing)
        assert score == 5

    def test_price_bonus_moderately_underpriced(self, scorer):
        listing = Listing(
            address="test", price=500_000, bedrooms=3, bathrooms=2,
            neighborhood="Heights", har_link="test",
            status=ListingStatus.NEW,
        )
        # Heights median is 650k, 500k/650k = 0.77 < 0.85
        score = scorer._score_price_bonus(listing)
        assert score == 3

    def test_price_bonus_none_for_normal_price(self, scorer, sample_listing):
        # 650k in Heights = exactly at median
        score = scorer._score_price_bonus(sample_listing)
        assert score == 0

    def test_rule_score_max_is_20(self, scorer):
        listing = Listing(
            address="test", price=300_000, bedrooms=3, bathrooms=2,
            sqft=1800, neighborhood="Heights", har_link="test",
            status=ListingStatus.NEW,
        )
        rule_score = scorer._calculate_rule_score(listing)
        assert rule_score <= 20
        # Should be 10 (premium) + 5 (sanity) + 5 (underpriced) = 20
        assert rule_score == 20


class TestCompositeScoring:
    """Test the 70/30 AI/rules composite scoring."""

    def test_ai_primary_weighting(self, scorer, sample_listing):
        # AI score = 80, rule score = 15 (neighborhood 10 + sanity 5)
        # Rule normalized = 15 * 5 = 75
        # Final = (80 * 0.7) + (75 * 0.3) = 56 + 22.5 = 78.5
        score = scorer.score(sample_listing, ai_score=80.0)
        assert 78.0 <= score <= 79.0

    def test_no_ai_score_uses_rules_only(self, scorer, sample_listing):
        # Rule score = 15, normalized = 15 * 5 = 75
        score = scorer.score(sample_listing, ai_score=None)
        assert score == 75.0

    def test_high_ai_low_rules(self, scorer, cheap_generic_listing):
        # AI loves it = 90, but rules are low (unknown neighborhood)
        # Rules: 3 (unknown neighborhood) + 3 (sanity price) + 2 (sanity size) + 5 (underpriced) = 13
        # Rules normalized: 13 * 5 = 65
        # Final: (90 * 0.7) + (65 * 0.3) = 63 + 19.5 = 82.5
        score = scorer.score(cheap_generic_listing, ai_score=90.0)
        assert score > 80

    def test_low_ai_high_rules(self, scorer, sample_listing):
        # AI doesn't like it = 20, but rules are good
        # Rules: 10 + 5 + 0 = 15, normalized = 75
        # Final: (20 * 0.7) + (75 * 0.3) = 14 + 22.5 = 36.5
        score = scorer.score(sample_listing, ai_score=20.0)
        assert 36.0 <= score <= 37.0

    def test_score_clamped_to_0_100(self, scorer, sample_listing):
        score = scorer.score(sample_listing, ai_score=150.0)
        assert score <= 100.0

        score = scorer.score(sample_listing, ai_score=-50.0)
        assert score >= 0.0


class TestBatchScoring:
    """Test batch scoring and sorting."""

    def test_batch_sorts_by_score_descending(
        self, scorer, sample_listing, cheap_generic_listing, character_home_listing
    ):
        listings = [cheap_generic_listing, sample_listing, character_home_listing]
        ai_scores = {
            sample_listing.address: 75.0,
            cheap_generic_listing.address: 30.0,
            character_home_listing.address: 90.0,
        }

        scored = scorer.batch_score(listings, ai_scores)

        assert len(scored) == 3
        # Character home should be first (highest AI score)
        assert scored[0][0].address == character_home_listing.address
        # Cheap generic should be last (lowest AI score)
        assert scored[2][0].address == cheap_generic_listing.address

    def test_batch_without_ai_scores(
        self, scorer, sample_listing, cheap_generic_listing
    ):
        scored = scorer.batch_score(
            [sample_listing, cheap_generic_listing], ai_scores=None
        )
        assert len(scored) == 2
        # All scores should be based on rules only
        for _, score in scored:
            assert score <= 100.0


class TestScoringPhilosophy:
    """Test that the new scoring reflects editorial priorities over price."""

    def test_character_home_beats_cheap_generic(self, scorer):
        """A character home with AI backing should beat a cheap generic listing."""
        character = Listing(
            address="456 Montrose Blvd", price=750_000, bedrooms=4,
            bathrooms=3, sqft=2800, year_built=1925,
            neighborhood="Montrose", har_link="test",
            status=ListingStatus.NEW,
        )
        cheap = Listing(
            address="789 Suburb Dr", price=180_000, bedrooms=3,
            bathrooms=2, sqft=1400, year_built=1998,
            neighborhood="", har_link="test",
            status=ListingStatus.NEW,
        )

        ai_scores = {
            character.address: 85.0,  # AI recognizes character
            cheap.address: 35.0,      # AI sees nothing special
        }

        scored = scorer.batch_score([character, cheap], ai_scores)
        assert scored[0][0].address == character.address
        assert scored[0][1] > scored[1][1]

    def test_price_alone_not_enough(self, scorer):
        """A cheap listing with low AI score should not rank highly."""
        cheap = Listing(
            address="test", price=150_000, bedrooms=3, bathrooms=2,
            sqft=1400, neighborhood="Heights", har_link="test",
            status=ListingStatus.NEW,
        )

        # Even with great price, if AI scores low, overall should be low
        score = scorer.score(cheap, ai_score=20.0)
        assert score < 50  # Should not be in top half
