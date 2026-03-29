# feat: Redesign Listing Scoring System

---
title: "feat: Redesign Listing Scoring System"
type: feat
status: completed
date: 2026-03-01
origin: docs/brainstorms/2026-03-01-scoring-system-redesign-brainstorm.md
---

## Overview

Redesign the listing scoring system to prioritize **character and editorial potential** over price, using Zillow-enriched data and AI-primary scoring aligned to the Curbed/Brownstoner voice guide.

The current system over-weights price (45% of score), resulting in newsletters featuring cheap but visually unappealing houses. This redesign shifts focus to "interesting houses that can become long-lasting homes."

## Problem Statement / Motivation

**Current state:**
- Price-based scoring dominates (30 points for underpriced + 15 for low $/sqft = 45%)
- AI scoring prompt mentions "investors" - conflicts with voice guide philosophy
- HAR email data is sparse, making quality assessment difficult
- Good listings with story potential are being missed

**Desired state:**
- Character/story potential drives selection
- Richer Zillow data enables better AI assessment
- Newsletters feature architecturally interesting properties regardless of price
- Editorial voice and scoring criteria are aligned

(see brainstorm: docs/brainstorms/2026-03-01-scoring-system-redesign-brainstorm.md)

## Proposed Solution

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Curator Pipeline (Daily)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Get Candidates (NEW/SCORED listings, limit 200)             │
│                          ↓                                       │
│  2. [NEW] Zillow Enrichment                                      │
│     ├── Normalize addresses (usaddress + rapidfuzz)             │
│     ├── Batch Apify lookup (maxcopell/zillow-detail-scraper)    │
│     └── Store: zillow_description, zillow_url, enrichment_source│
│                          ↓                                       │
│  3. AI Scoring (Voice-Aligned)                                   │
│     ├── Build prompt with voice guide philosophy                 │
│     ├── Claude scores 0-100 with reasoning                       │
│     └── Store: ai_score, ai_reasoning                           │
│                          ↓                                       │
│  4. Rule-Based Scoring (Guardrails Only)                        │
│     ├── Neighborhood context: 10 pts                             │
│     ├── Sanity checks: 5 pts                                     │
│     └── Price value (small bonus): 5 pts                         │
│                          ↓                                       │
│  5. Combined Score = (AI × 0.70) + (Rules × 0.30)               │
│                          ↓                                       │
│  6. Diversity Selection (unchanged)                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | Zillow via Apify | Richer descriptions; HAR scraping violates ToS |
| Apify actor | `maxcopell/zillow-detail-scraper` | Supports address lookup, $3/1000 results |
| Address matching | usaddress + rapidfuzz | 85%+ confidence threshold for matches |
| Scoring split | 70% AI / 30% rules | Editorial judgment is inherently holistic |
| Fallback | HAR-only scoring | Graceful degradation if enrichment fails |
| Caching | Cache indefinitely per listing | Enrich once; no TTL for v1 |
| Old scores | Clear on deployment | Prevents mixing old/new scale |

## Technical Approach

### Phase 1: Data Model & Configuration

**Add new fields to Listing model** ([models.py:82-83](src/models.py#L82-L83)):

```python
# Zillow enrichment fields
zillow_description = Column(Text, nullable=True)
zillow_url = Column(String(1000), nullable=True)
enrichment_source = Column(String(50), nullable=True)  # "har_only" | "zillow" | "zillow_partial"
zillow_fetched_at = Column(DateTime, nullable=True)

# AI scoring fields
ai_score = Column(Float, nullable=True)
ai_reasoning = Column(Text, nullable=True)
```

**Add Apify configuration** ([config.py:34-36](src/config.py#L34-L36)):

```python
# Zillow/Apify enrichment
apify_api_token: str = ""
apify_zillow_actor_id: str = "maxcopell/zillow-detail-scraper"
zillow_enrichment_enabled: bool = True
zillow_batch_size: int = 200  # Batch all candidates together
```

**Files:**
- [x] `src/models.py` - Add 6 new fields
- [x] `src/config.py` - Add 4 new settings
- [ ] Create migration (if using Alembic) or recreate DB

### Phase 2: Enrichment Module

**Create new enrichment package:**

```
src/enrichment/
├── __init__.py
├── address_normalizer.py   # usaddress + rapidfuzz matching
├── apify_client.py         # Apify API wrapper
└── zillow_enricher.py      # Orchestrates enrichment pipeline
```

**address_normalizer.py:**

```python
from dataclasses import dataclass
from typing import Optional, Tuple
import usaddress
from rapidfuzz import fuzz

@dataclass
class ParsedAddress:
    street_number: str
    street_name: str
    street_suffix: str
    unit_number: Optional[str]
    city: str
    state: str
    zipcode: str
    raw: str

    def normalized_key(self) -> str:
        """Key for exact matching: number|name|zip."""
        return f"{self.street_number}|{self.street_name.lower()}|{self.zipcode[:5]}"

class AddressNormalizer:
    MATCH_THRESHOLD = 85.0

    def parse(self, address: str) -> ParsedAddress:
        """Parse address string into structured components."""
        ...

    def match(self, addr1: ParsedAddress, addr2: ParsedAddress) -> Tuple[bool, float]:
        """Return (is_match, confidence) for two addresses."""
        # Must match: street number, zipcode (5-digit)
        # Fuzzy match: street name (85%+ threshold)
        ...
```

**apify_client.py** (following [instagram_client.py](src/publishers/instagram_client.py) pattern):

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
from tenacity import retry, stop_after_attempt, wait_exponential

@dataclass
class ZillowResult:
    success: bool
    address: str
    description: Optional[str] = None
    zillow_url: Optional[str] = None
    error: Optional[str] = None

class ApifyZillowClient:
    ACTOR_ID = "maxcopell/zillow-detail-scraper"

    def __init__(self, api_token: str):
        self.client = ApifyClient(
            token=api_token,
            max_retries=8,
            min_delay_between_retries_millis=1000
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def enrich_batch(self, addresses: List[str]) -> List[ZillowResult]:
        """Batch lookup addresses on Zillow via Apify."""
        run_input = {
            "propertyStatus": "FOR_SALE",
            "addresses": addresses
        }
        run = self.client.actor(self.ACTOR_ID).call(
            run_input=run_input,
            timeout_secs=600
        )
        # Parse results, match back to input addresses
        ...
```

**Files:**
- [x] `src/enrichment/__init__.py`
- [x] `src/enrichment/address_normalizer.py`
- [x] `src/enrichment/apify_client.py`
- [x] `src/enrichment/zillow_enricher.py`

### Phase 3: Rewrite AI Scoring Prompt

**New voice-aligned prompt** ([claude_client.py:134-159](src/ai/claude_client.py#L134-L159)):

```python
SCORING_SYSTEM_PROMPT = """You are an editorial curator for a Houston real estate newsletter
inspired by Curbed and Brownstoner. You're looking for interesting houses that can become
long-lasting homes.

This is NOT an investment newsletter. Don't prioritize:
- Flipping potential or ROI
- Being "underpriced" or a "deal"
- Generic new construction

DO prioritize:
- Architectural character and distinctive design
- Story potential (history, neighborhood context, notable features)
- Properties that would make compelling newsletter content
- Homes with "bones" - good structure that could become special
- Unique or quirky features worth highlighting

Think: "Would a Curbed reader stop scrolling for this house?"
"""

SCORING_USER_PROMPT = """Score these Houston listings for newsletter inclusion (0-100).

For each listing, consider:
1. Does it have architectural character or distinctive features?
2. Is there a story here? (neighborhood context, history, notable details)
3. Would it make compelling newsletter content?
4. Does it fit "interesting houses that can become long-lasting homes"?

Score HIGH (70-100): Character homes, notable architecture, story potential
Score MEDIUM (40-69): Decent homes but nothing distinctive
Score LOW (0-39): Generic, cookie-cutter, or investor specials

Return JSON array with: address, score (0-100), reasoning (1-2 sentences)

Listings:
{listings}
"""
```

**Files:**
- [x] `src/ai/claude_client.py` - Rewrite `score_listings()` method

### Phase 4: Rewrite Rule-Based Scorer

**New scoring weights** ([scorer.py:120-139](src/curation/scorer.py#L120-L139)):

| Component | Old Points | New Points | Purpose |
|-----------|------------|------------|---------|
| Price value | 30 | 5 | Small bonus, not primary |
| Size/value ratio | 15 | 0 | Remove entirely |
| Architecture (year) | 20 | 0 | AI handles this better |
| Features (keywords) | 20 | 0 | AI handles this better |
| Neighborhood | 15 | 10 | Context for selection |
| Sanity checks | 0 | 5 | Not overpriced, reasonable size |
| **Total** | **100** | **20** | Rules are guardrails only |

**New rule-based scorer:**

```python
class ListingScorer:
    def __init__(self, ai_weight: float = 0.7):  # Changed from 0.4
        self.ai_weight = ai_weight

    def _calculate_rule_score(self, listing: Listing) -> float:
        """Guardrail scoring - max 20 points."""
        score = 0.0

        # Neighborhood context (0-10 points)
        score += self._score_neighborhood(listing)

        # Sanity checks (0-5 points)
        score += self._score_sanity(listing)

        # Small price bonus (0-5 points)
        score += self._score_price_bonus(listing)

        return score

    def _score_neighborhood(self, listing: Listing) -> float:
        """Score neighborhood for editorial potential."""
        # Premium neighborhoods with strong identity: 10 pts
        # Known neighborhoods: 6 pts
        # Unknown: 3 pts
        ...

    def _score_sanity(self, listing: Listing) -> float:
        """Basic sanity checks."""
        # Not wildly overpriced for area: 3 pts
        # Reasonable size (>500 sqft): 2 pts
        ...

    def _score_price_bonus(self, listing: Listing) -> float:
        """Small bonus for good value, not primary driver."""
        # Significantly underpriced (<70% median): 5 pts
        # Moderately underpriced (<85%): 3 pts
        # Otherwise: 0 pts
        ...
```

**Files:**
- [x] `src/curation/scorer.py` - Rewrite scoring methods

### Phase 5: Integrate into Curator Pipeline

**Update curator flow** ([curator.py:65-107](src/curation/curator.py#L65-L107)):

```python
async def curate(self) -> CurationResult:
    # 1. Get candidates
    candidates = self._get_candidates()
    if not candidates:
        return CurationResult(success=False, message="No candidates")

    # 2. [NEW] Enrich with Zillow data
    if self.settings.zillow_enrichment_enabled:
        candidates = await self._enrich_with_zillow(candidates)

    # 3. Get AI scores (with new voice-aligned prompt)
    ai_scores = {}
    if self.settings.use_ai:
        ai_scores = await self._get_ai_scores(candidates)

    # 4. Batch score (70% AI + 30% rules)
    scored = self.scorer.batch_score(candidates, ai_scores)

    # ... rest unchanged
```

**New enrichment method:**

```python
async def _enrich_with_zillow(self, candidates: list[Listing]) -> list[Listing]:
    """Enrich listings with Zillow data, skip already enriched."""
    to_enrich = [c for c in candidates if not c.zillow_fetched_at]

    if not to_enrich:
        return candidates

    enricher = ZillowEnricher(self.apify_client)
    results = await enricher.enrich_batch(to_enrich)

    for listing, result in zip(to_enrich, results):
        if result.success:
            listing.zillow_description = result.description
            listing.zillow_url = result.zillow_url
            listing.enrichment_source = "zillow"
        else:
            listing.enrichment_source = "har_only"
        listing.zillow_fetched_at = datetime.utcnow()
        self.session.add(listing)

    self.session.commit()
    return candidates
```

**Files:**
- [x] `src/curation/curator.py` - Add enrichment step, update AI scoring call

## System-Wide Impact

### Interaction Graph

1. **Email parsing** → creates Listing with status=NEW
2. **Curator.curate()** → enriches, scores, selects
3. **Enrichment** → calls Apify API, updates Listing fields
4. **AI scoring** → calls Claude API, stores ai_score + ai_reasoning
5. **Generation** → uses enriched data + score for description generation
6. **Approval workflow** → unchanged, but receives better candidates

### Error Propagation

| Error | Source | Handling |
|-------|--------|----------|
| Apify API failure | enrichment | Fallback to HAR-only, log warning |
| Address parse failure | normalizer | Skip enrichment for that listing |
| No Zillow match | enrichment | Mark as har_only, continue scoring |
| Claude API failure | AI scoring | Fallback to 100% rule-based |
| Rate limit (429) | Apify/Claude | Retry with exponential backoff |

### State Lifecycle Risks

- **Partial enrichment:** If enrichment crashes mid-batch, some listings have Zillow data, others don't. Mitigated by `zillow_fetched_at` timestamp - can resume.
- **Score migration:** Old scores on different scale. Mitigated by clearing all scores on deployment.
- **Stale Zillow data:** Price changes not reflected. Accepted for v1; no re-enrichment.

### API Surface Parity

No external APIs affected. Internal changes only.

## Acceptance Criteria

### Functional Requirements

- [ ] Listings are enriched with Zillow descriptions before scoring
- [ ] AI scoring uses voice-aligned prompt (no "investor" language)
- [ ] Combined score is 70% AI + 30% rules
- [ ] Price-based scoring reduced from 45 points to 5 points
- [ ] Listings without Zillow data fall back to HAR-only scoring
- [ ] AI reasoning is stored for each scored listing

### Non-Functional Requirements

- [ ] Enrichment cost stays under $60/month (~$2/day)
- [ ] Curation pipeline completes within 10 minutes (was ~2 minutes)
- [ ] Apify failures don't block curation (graceful fallback)
- [ ] All existing tests pass after scorer rewrite

### Quality Gates

- [ ] Unit tests for address normalization (parse, match)
- [ ] Unit tests for Apify client (success, failure, partial)
- [ ] Unit tests for new scorer weights
- [ ] Integration test for full enrichment → scoring pipeline
- [ ] Manual review: top 20 listings from new scorer align with voice guide

## Success Metrics

1. **Character improvement:** Newsletters feature more architecturally interesting properties (subjective review)
2. **Price de-correlation:** Score and price have lower correlation than before
3. **Enrichment rate:** >80% of listings successfully enriched with Zillow data
4. **Cost efficiency:** Enrichment costs <$60/month
5. **Explainability:** AI reasoning explains why each listing scored high/low

## Dependencies & Risks

### Dependencies

| Dependency | Risk | Mitigation |
|------------|------|------------|
| Apify service availability | Medium | Retry logic, fallback to HAR-only |
| Zillow data coverage | Medium | Accept 80% match rate; HAR fallback |
| Claude API | Low | Existing retry logic in place |
| usaddress library | Low | Well-maintained, MIT licensed |
| rapidfuzz library | Low | Well-maintained, MIT licensed |

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Zillow ToS changes | Low | High | Monitor Apify actor updates |
| AI scores inconsistent | Medium | Medium | Few-shot examples in prompt |
| Address matching failures | Medium | Low | Fallback to HAR-only |
| Higher curation latency | High | Low | Accept 5-10 min runtime |

## New Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing
    "apify-client>=1.6.0",
    "usaddress>=0.5.10",
    "rapidfuzz>=3.5.0",
]
```

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-03-01-scoring-system-redesign-brainstorm.md](docs/brainstorms/2026-03-01-scoring-system-redesign-brainstorm.md)
- Key decisions carried forward: Zillow enrichment, 70/30 AI split, price de-emphasis, no image analysis

### Internal References

- Current scorer: [src/curation/scorer.py](src/curation/scorer.py)
- AI client: [src/ai/claude_client.py:118-169](src/ai/claude_client.py#L118-L169)
- Curator pipeline: [src/curation/curator.py:65-107](src/curation/curator.py#L65-L107)
- Voice guide: [src/generation/voice_guide.py](src/generation/voice_guide.py)
- Instagram client pattern: [src/publishers/instagram_client.py](src/publishers/instagram_client.py)

### External References

- Apify Python client: https://docs.apify.com/api/client/python
- Zillow scraper actor: https://apify.com/maxcopell/zillow-detail-scraper
- usaddress library: https://github.com/datamade/usaddress
- rapidfuzz library: https://github.com/rapidfuzz/rapidfuzz

### Related Learnings

- Voice guide solution: [docs/solutions/logic-errors/newsletter-voice-too-generic-salesy.md](docs/solutions/logic-errors/newsletter-voice-too-generic-salesy.md)
  - Key insight: Scoring feeds content generation. Poor candidates → generic output regardless of voice guide quality.
