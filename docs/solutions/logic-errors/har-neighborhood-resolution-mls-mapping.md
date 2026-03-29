---
title: "HAR Neighborhood Resolution: MLS Subdivision Names Replaced with Recognized Neighborhoods"
date: "2026-03-01"
category: "logic-errors"
component: "email-parsing, enrichment-pipeline"
problem_type: "data-quality"
severity: "medium"
tags:
  - neighborhood-resolution
  - data-enrichment
  - email-parsing
  - zip-code-mapping
  - zillow-integration
related_files:
  - src/enrichment/neighborhood_resolver.py
  - src/enrichment/apify_client.py
  - src/enrichment/zillow_enricher.py
  - src/email/parser.py
  - src/models.py
  - src/email/processor.py
  - tests/test_neighborhood_resolver.py
related_docs:
  - docs/solutions/integration-issues/apify-zillow-detail-scraper-input-format.md
  - docs/solutions/logic-errors/newsletter-voice-too-generic-salesy.md
---

# HAR Neighborhood Resolution: MLS Subdivision Names Replaced with Recognized Neighborhoods

## Problem

HAR email alerts use the "Located in" field to identify a listing's location, but this field contains **MLS subdivision names** rather than recognized Houston neighborhoods:

| HAR "Located in" (MLS) | What readers expect |
|---|---|
| Somerset Green Sec 5 | Spring Branch |
| Harvard House Condo | Heights |
| Baker Add Homes | Rice Military |
| Contemporary Heights Sec 14 | Heights |
| Weslayan Condo | West University |
| Dallas Ave Twnhms | EaDo |

These MLS names appeared in the newsletter details line (`2 bed / 1 bath | 1,020 sqft | Weslayan Condo`) and confused readers.

## Root Cause

The HAR parser directly used the "Located in" field as the `neighborhood` value. This field is the legal MLS subdivision name, not the colloquial neighborhood. The parser had a fallback pattern match against known neighborhood names, but it rarely triggered because the MLS subdivision name was found first.

## Solution

Two-layer neighborhood resolution: Zillow neighborhood data (when available) with Houston zip code mapping as fallback.

### 1. NeighborhoodResolver (`src/enrichment/neighborhood_resolver.py`)

New class with:
- `HOUSTON_ZIP_TO_NEIGHBORHOOD` — ~100 Houston zip codes mapped to recognized neighborhoods
- `resolve(address, zillow_raw_data=None)` — priority: Zillow field > zip code lookup
- Zillow extraction checks: `neighborhood`, `neighborhoodRegion`, `subdivision`, and nested `resoFacts.subdivisionName`
- Zip extraction via regex `\b(77\d{3})\b` targeting Houston-area codes

### 2. HAR Parser Changes (`src/email/parser.py`)

- "Located in X" value stored as `subdivision` (preserves raw MLS name)
- `neighborhood` resolved via `_resolver.resolve(text)` using the full listing text (which contains the zip code)
- Existing `NEIGHBORHOODS` pattern match kept as final fallback

### 3. Zillow Enrichment (`src/enrichment/zillow_enricher.py`)

- During enrichment, calls resolver with `zillow_raw_data=result.raw_data`
- Zillow neighborhood overrides zip-based resolution (more specific)

### 4. Data Model (`src/models.py`)

- Added `subdivision` column to `Listing` to preserve raw HAR MLS name
- `neighborhood` now holds the resolved, human-friendly name

### Key Design Decisions

| Decision | Rationale |
|---|---|
| Zip regex `77\d{3}` | Targets Houston-area zips specifically |
| Zillow priority over zip | More specific and reliable |
| Preserve raw subdivision | Enables debugging and audit trail |
| No external API for fallback | Zip mapping is local — no cost or latency |
| Use full listing text for zip extraction | `_clean_address()` strips the zip from the stored address |

## Verification

- 17 unit tests in `tests/test_neighborhood_resolver.py` covering zip resolution, Zillow extraction, priority ordering, and edge cases
- Full test suite (49 tests) passes with zero regressions
- Example: `debug_email.html` listing at 77055 ("Somerset Green Sec 5") now resolves to "Spring Branch"

## Prevention

- **Validate Zillow neighborhoods**: Reject values matching MLS patterns (`Sec \d+`, `Phase \d+`, etc.) — if Zillow returns a subdivision code, fall through to zip
- **Monitor unknown neighborhoods**: Log when zip code lookup returns None — indicates a new Houston zip not in the mapping
- **Maintain zip mapping**: Review quarterly as Houston grows; new zips can be added to `HOUSTON_ZIP_TO_NEIGHBORHOOD`
- **Test with real HAR emails**: Integration tests against sample emails catch parser regressions before they reach production
