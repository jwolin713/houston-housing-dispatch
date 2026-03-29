# Scoring System Redesign Brainstorm

**Date:** 2026-03-01
**Status:** Ready for planning

## What We're Building

A redesigned listing scoring system that prioritizes **character and editorial potential** over price, using Zillow-enriched data and AI-primary scoring aligned to the Curbed/Brownstoner voice guide.

### Problem Statement

The current scoring system over-emphasizes price (45% of score tied to price/value metrics), resulting in newsletters featuring cheap but visually unappealing houses that lack character. Good listings with story potential are being missed.

### Target Outcome

Newsletters featuring "interesting houses that can become long-lasting homes" - properties with architectural character, neighborhood context, and story potential, regardless of whether they're the cheapest in their area.

## Why This Approach

### Approach Selected: Full Pipeline Redesign

We chose a clean slate redesign over incremental enhancement because:

1. **Current limitations are structural** - The 45% price weighting is baked into the rule architecture
2. **Voice guide alignment requires holistic assessment** - Rules can't capture "would this make compelling content?"
3. **Zillow enrichment changes the data model** - Better to design around richer data from the start
4. **AI-primary scoring needs different prompt architecture** - Not just tweaking weights

### Alternatives Considered

- **Incremental Enhancement:** Lower risk but inherits current limitations
- **AI-Only Scoring:** Simplest but lacks guardrails and debuggability

## Key Decisions

### 1. Data Enrichment
- **Decision:** Enrich ALL listings with Zillow data via Apify before scoring
- **Rationale:** Richer descriptions enable better AI assessment; HAR emails have limited text
- **Cost:** ~$30-60/month for 200 listings/day
- **Fallback:** If Zillow data unavailable, score with HAR data only (graceful degradation)

### 2. Scoring Model
- **Decision:** AI-primary scoring (70% AI, 30% rules)
- **Rationale:** Editorial judgment ("is this newsletter-worthy?") is inherently holistic
- **Rules become guardrails:** Filter obvious junk, ensure diversity, basic sanity checks

### 3. AI Prompt Alignment
- **Decision:** Rewrite AI prompt to align with voice guide philosophy
- **Key criteria:**
  - "Interesting houses that can become long-lasting homes"
  - Story potential (notable history, neighborhood context, architectural quirks)
  - Character and distinctiveness over investment potential
  - NOT about flipping, ROI, or "deals"
- **Remove:** Current prompt mentions "investors" - conflicts with voice

### 4. Price De-emphasis
- **Decision:** Reduce price-based scoring from 45 points to ~15 points
- **New weighting (rules portion):**
  - Neighborhood context: 10 points
  - Basic sanity checks: 5 points (not overpriced for area)
  - Price value: 5 points (small bonus for good value, not primary driver)

### 5. Image Analysis
- **Decision:** Skip for now (cost-prohibitive at $180-900/month)
- **Future consideration:** Could add later for top candidates only

### 6. No HAR Scraping
- **Decision:** Do NOT scrape HAR website for full descriptions
- **Rationale:** Violates HAR Terms of Service
- **Alternative:** Zillow via Apify is acceptable third-party enrichment

## Open Questions (To Resolve in Planning)

1. **Address matching:** How should we normalize HAR addresses to match Zillow? Options: address parsing library, fuzzy matching, or Zillow search API. *Deferred to planning phase for investigation.*

2. **Apify integration:** Should we batch Zillow lookups or do them individually? What's the rate limit? *Investigate Apify API documentation in planning.*

3. **Caching:** Should we cache Zillow data to avoid re-fetching for listings that span multiple days? *Investigate current data flow in planning.*

## Out of Scope

- Image/photo analysis (future enhancement)
- Scraping HAR for additional data
- Changes to the diversity selector or newsletter ordering
- Changes to the approval workflow

## Success Criteria

1. Newsletters feature more architecturally interesting properties
2. Fewer "cheap but boring" listings make the cut
3. Selected listings align with Curbed/Brownstoner editorial voice
4. Scoring is explainable ("why did this score high?")
5. Cost stays under $100/month for data enrichment

## Technical Notes

### Files to Modify
- `src/curation/scorer.py` - Rewrite scoring logic
- `src/ai/claude_client.py` - New voice-aligned scoring prompt
- `src/curation/curator.py` - Add Zillow enrichment step
- `src/config.py` - Add Apify configuration

### New Dependencies
- Apify client library or HTTP calls to Apify API
- Address normalization library (TBD)

### Data Model Changes
- Add `zillow_description`, `zillow_url` fields to Listing model
- Add `enrichment_source` field to track data provenance
