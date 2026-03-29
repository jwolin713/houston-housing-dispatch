---
title: "feat: Improve Newsletter Writing Style"
type: feat
status: completed
date: 2026-03-01
origin: docs/brainstorms/2026-03-01-newsletter-writing-style-brainstorm.md
---

# feat: Improve Newsletter Writing Style

## Overview

Transform Houston Housing Dispatch newsletter output from generic real estate copy to a knowledgeable insider voice—like Curbed, Brownstoner, or local food critics (Alison Cook, Erica Chen). The implementation uses a two-part approach: enhanced voice guide + prompts, plus an editorial layer with full rewrite capability.

## Problem Statement / Motivation

Current newsletter output feels too generic and salesy despite the existing voice guide. Root causes:

- Prompts don't enforce neighborhood context—descriptions focus on property features, not what it's like to live there
- Examples aren't distinctive enough—need sharper, more opinionated samples
- No editorial cohesion—each listing stands alone with no narrative thread
- Wrong grouping—price tiers don't match how readers think (they search by neighborhood)

**Core philosophy:** "Interesting houses that can become long-lasting homes" (see brainstorm: docs/brainstorms/2026-03-01-newsletter-writing-style-brainstorm.md)

## Proposed Solution

### Part 1: Enhanced Voice Guide + Prompts

1. **Rewrite `voice_guide.py`**
   - Add Curbed/Brownstoner-style examples with sharper insider language
   - Include neighborhood-specific context examples
   - Expand "phrases to avoid" list
   - Add "phrases that work" with insider vocabulary

2. **Rewrite AI prompts in `claude_client.py`**
   - Enforce neighborhood context in every description
   - Require one unique/memorable detail per listing
   - Reference inspiration publications in system prompt
   - Better few-shot examples

3. **Change grouping logic**
   - Group listings by neighborhood (not price tier)
   - Add neighborhood intro sentences

### Part 2: Editorial Layer

1. **Add editor pass after generation**
   - Full editorial control to rewrite descriptions
   - Add connecting sentences between neighborhood sections
   - Strengthen intro paragraph based on full content
   - Ensure consistent voice throughout

2. **Implement safeguards**
   - Validate factual details unchanged (price, address, beds/baths)
   - Scan for banned generic phrases
   - Fallback to pre-edit content on API failure

## Technical Considerations

### Files to Modify

| File | Changes |
|------|---------|
| `src/generation/voice_guide.py` | Rewrite examples, expand avoid list, add "phrases that work" |
| `src/ai/claude_client.py` | Rewrite prompts, add `edit_newsletter()` method |
| `src/generation/generator.py` | Add editorial pass, change to neighborhood grouping |
| `src/generation/template_generator.py` | Expand NEIGHBORHOOD_CONTEXT, update grouping |

### Architecture: Editorial Pass Design

```
Pre-Edit Content                    Editorial Pass                     Post-Edit Content
┌─────────────────┐                ┌─────────────────┐               ┌─────────────────┐
│ intro           │───────────────▶│                 │──────────────▶│ revised intro   │
│ sections[]      │                │ EDITOR PROMPT   │               │ revised sections│
│  └─ neighborhood│                │ + Voice Guide   │               │  └─ transitions │
│     └─ listings │                │ + Constraints   │               │     └─ rewrites │
│        └─ desc  │                │                 │               │        └─ desc  │
└─────────────────┘                └─────────────────┘               └─────────────────┘
                                          ▲
                                          │
                              ┌───────────┴───────────┐
                              │ IMMUTABLE FIELDS      │
                              │ (passed separately)   │
                              │ - price               │
                              │ - address             │
                              │ - beds/baths/sqft     │
                              │ - year_built          │
                              │ - HAR link            │
                              └───────────────────────┘
```

### Editor Prompt Structure

```python
EDITOR_SYSTEM_PROMPT = """
You are the editor of Houston Housing Dispatch, a real estate newsletter with the voice of
a knowledgeable Houston insider—think Curbed, Brownstoner, or a local food critic like
Alison Cook or Erica Chen.

Your job is to polish this newsletter draft into a cohesive, engaging read:

VOICE GUIDELINES:
- Conversational insider tone—like a friend who knows Houston neighborhoods deeply
- Observational and specific—notice details others miss
- Practical focus—parking, layout, condition, what matters to buyers
- Light editorial wit—occasional commentary without snark

WHAT YOU CAN CHANGE:
- Rewrite listing descriptions to be more distinctive and insider-voiced
- Add connecting sentences between neighborhood sections
- Strengthen the intro to hook readers
- Improve flow and variety in sentence structure
- Remove any generic real estate language that slipped through

WHAT YOU CANNOT CHANGE (these are factual and must be preserved exactly):
- Prices
- Addresses
- Bedroom/bathroom counts
- Square footage
- Year built
- HAR links
- Neighborhood names

PHRASES TO ELIMINATE:
{avoid_phrases}

OUTPUT FORMAT:
Return the complete newsletter in markdown with all sections intact.
"""
```

### Factual Validation

After editorial pass, validate immutable fields:

```python
def _validate_editorial_output(self, original: dict, edited: str) -> bool:
    """Ensure factual details unchanged after editorial pass."""
    for listing in original['listings']:
        # Check price appears unchanged
        price_str = f"${listing['price']:,}"
        if price_str not in edited:
            raise EditorialValidationError(f"Price {price_str} missing from edited content")

        # Check address unchanged
        if listing['address'] not in edited:
            raise EditorialValidationError(f"Address {listing['address']} missing")

        # Check beds/baths pattern
        beds_baths = f"{listing['bedrooms']} bed"
        if beds_baths not in edited:
            raise EditorialValidationError(f"Bedroom count missing for {listing['address']}")

    return True
```

### Error Handling

| Failure Mode | Behavior |
|--------------|----------|
| Editorial API fails | Fall back to pre-edit content, log warning |
| Factual validation fails | Retry once, then fall back to pre-edit |
| Generic phrase detected | Flag in approval email, don't block |
| Token limit exceeded | Process in chunks (5-7 listings), final cohesion pass |

## System-Wide Impact

- **Interaction graph**: Generation pipeline adds one new API call (editorial pass) after existing description calls
- **Error propagation**: Editorial failures gracefully degrade to pre-edit content; existing approval flow unchanged
- **State lifecycle**: No new database state; `generated_description` field stores final (post-edit) version
- **API surface parity**: Both AI generator and template generator should support neighborhood grouping

## Acceptance Criteria

### Voice Quality
- [ ] Newsletter reads like a knowledgeable friend, not a real estate agent
- [ ] No generic phrases from avoid list appear in final output
- [ ] Each description includes neighborhood context or unique detail
- [ ] Intro paragraph hooks readers with what's interesting this week

### Structure
- [ ] Listings grouped by neighborhood (not price tier)
- [ ] Each neighborhood section has contextual intro sentence
- [ ] Connecting sentences between neighborhood transitions

### Technical
- [ ] Editorial pass implemented with full rewrite capability
- [ ] Factual validation prevents price/address changes
- [ ] Fallback to pre-edit content on API failure
- [ ] Generic phrase scanner flags violations in approval email

### User Review
- [ ] New voice guide examples reviewed and approved before implementation
- [ ] Sample output compared against Curbed/Brownstoner quality bar

## Implementation Phases

### Phase 1: Voice Guide Enhancement

**Goal:** Create the voice foundation before touching code.

- [x] Draft 12-15 new listing description examples in Curbed/Brownstoner style
- [x] Draft 5-6 new intro paragraph examples
- [x] Expand avoid phrases list (add 10-15 more generic terms)
- [x] Create "phrases that work" list with insider vocabulary
- [x] **User review:** Present draft examples for iteration

**Files:** `voice_guide.py` (draft only, not implemented)

### Phase 2: Prompt Rewrite + Grouping

**Goal:** Improve generation quality at the source.

- [x] Rewrite `generate_listing_description()` prompt with new examples
- [x] Rewrite `generate_newsletter_intro()` prompt
- [x] Reference inspiration publications in system prompts
- [x] Implement `_group_by_neighborhood()` to replace price tier grouping
- [x] Add neighborhood intro sentence generation
- [x] Expand `NEIGHBORHOOD_CONTEXT` dict to 30+ neighborhoods

**Files:** `claude_client.py:171-255`, `generator.py:148-167`, `template_generator.py:27-38`

### Phase 3: Editorial Layer

**Goal:** Add polish and cohesion pass.

- [x] Implement `ClaudeClient.edit_newsletter()` method
- [x] Create editor system prompt with voice guide and constraints
- [x] Pass immutable fields separately from editable content
- [x] Implement `_validate_editorial_output()` for factual checking
- [x] Add fallback logic for API failures
- [x] Integrate editorial pass into `NewsletterGenerator.generate_newsletter()`

**Files:** `claude_client.py` (new method), `generator.py:34-92`

### Phase 4: Validation + Polish

**Goal:** Ensure quality and catch regressions.

- [x] Implement generic phrase scanner
- [ ] Add phrase violations to approval email
- [ ] Test with 3-5 real newsletter generations
- [ ] Compare output quality against pre-change baseline
- [ ] Document any edge cases discovered

**Files:** `generator.py`, `approval.py` (approval email template)

## Success Metrics

- Newsletter passes manual "Curbed test" (reads like an insider publication)
- Zero generic phrases from avoid list in published newsletters
- Every listing has neighborhood context or unique detail
- User reports positive reader feedback on voice change

## Dependencies & Risks

| Risk | Mitigation |
|------|------------|
| Editorial pass introduces factual errors | Validation step compares immutable fields |
| Voice examples don't match user's vision | Phase 1 includes user review before implementation |
| API costs increase significantly | Monitor; editorial pass is single call per newsletter |
| Large newsletters exceed token limits | Chunking logic processes 5-7 listings at a time |

## Sources & References

### Origin
- **Brainstorm document:** [docs/brainstorms/2026-03-01-newsletter-writing-style-brainstorm.md](docs/brainstorms/2026-03-01-newsletter-writing-style-brainstorm.md)
- Key decisions carried forward: knowledgeable insider voice, neighborhood grouping, full editorial control, user review of examples

### Internal References
- Voice guide: [src/generation/voice_guide.py](src/generation/voice_guide.py)
- Listing prompt: [src/ai/claude_client.py:171-212](src/ai/claude_client.py#L171-L212)
- Intro prompt: [src/ai/claude_client.py:214-255](src/ai/claude_client.py#L214-L255)
- Generation pipeline: [src/generation/generator.py:34-92](src/generation/generator.py#L34-L92)
- Neighborhood grouping: [src/generation/generator.py:148-167](src/generation/generator.py#L148-L167)

### External References
- Voice inspiration: Curbed, The Infatuation, Brownstoner
- Houston critics: Alison Cook, Erica Chen
