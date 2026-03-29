---
title: Generic AI Newsletter Output Lacking Local Voice and Editorial Authenticity
slug: newsletter-voice-too-generic-salesy
date: 2026-03-01
category: logic-errors
tags: [ai-prompts, voice-guide, editorial-style, newsletter-generation, content-tone, houston-local]
component: src/generation
severity: medium
symptoms:
  - Newsletter output reads as generic real estate marketing copy
  - Listings lack neighborhood-specific context and local knowledge
  - Salesy phrases dominate instead of authentic editorial voice
  - Content grouped by price tiers rather than meaningful geographic areas
  - Missing the "knowledgeable insider" tone of respected local publications
  - AI-generated descriptions lack factual grounding and validation
root_cause: Insufficient voice guidance and prompt engineering for AI content generation, with no editorial validation pass or generic phrase detection to enforce authentic Houston insider perspective
---

# Generic AI Newsletter Output Lacking Local Voice and Editorial Authenticity

## Problem

The Houston Housing Dispatch newsletter output felt too generic and salesy despite having a voice guide. Four root causes were identified:

1. **Prompts didn't enforce neighborhood context** - Listing descriptions could be written without any reference to what it's like to actually live in that neighborhood
2. **Examples weren't distinctive enough** - The voice guide lacked enough concrete examples in the Curbed/Brownstoner insider style
3. **No editorial cohesion between listings** - Each listing was generated independently without narrative flow or transitions between sections
4. **Wrong grouping strategy** - Listings were grouped by price tiers (Under $300K, $300K-$400K, etc.) instead of by neighborhood, which is how local readers actually think about Houston real estate

**Core philosophy violated:** "Interesting houses that can become long-lasting homes" — not investment returns or flipping potential.

---

## Solution

### Part 1: Enhanced Voice Guide + Prompts

**File: `src/generation/voice_guide.py`**

The voice guide was rewritten with substantial new content:

**12 Curbed/Brownstoner-style listing examples** covering Heights, Montrose, EaDo, Midtown, West U, Bellaire, Meyerland, River Oaks, Southampton, Garden Oaks, and Oak Forest:

```python
listing_examples: list[str] = field(default_factory=lambda: [
    # Heights / Historic
    "The kind of Heights bungalow that used to go for under $400K—back when that "
    "was a lot for the neighborhood. This one's been updated without erasing its "
    "history: original pine floors sanded back to life, period-appropriate trim "
    "work, and a kitchen that acknowledges microwaves exist. The lot's tight but "
    "the mature pecan in back provides actual shade, not just landscaping.",

    # Meyerland post-Harvey
    "Meyerland house that flooded in Harvey and was rebuilt properly—not just "
    "dried out and flipped. We checked: new foundation, new electrical, new HVAC, "
    "elevated two feet above the old slab. The neighborhood's still recovering, "
    "but the house itself is functionally new construction at half the price.",
    # ... 10 more examples
])
```

**6 intro paragraph examples** with insider hooks:

```python
intro_examples: list[str] = field(default_factory=lambda: [
    "From a Heights Victorian that predates most of the neighborhood to new EaDo "
    "lofts with downtown views, this week's mix actually feels like Houston—diverse, "
    "spread out, and hard to categorize...",

    "If you've been doom-scrolling through gray paint and LVP flooring, this week's "
    "a palate cleanser. Original hardwoods in Bellaire, transom windows in the "
    "Heights, and a Garden Oaks A-frame that's been teasing the neighborhood for "
    "years...",
    # ... 4 more examples
])
```

**Expanded avoid_phrases to 32 items:**

```python
avoid_phrases: list[str] = field(default_factory=lambda: [
    "won't last long", "move-in ready", "must see", "stunning", "gorgeous",
    "beautiful home", "perfect for entertaining", "great location",
    "dream home", "amazing opportunity", "rare find", "don't miss out",
    "entertainer's paradise", "open concept living", "shows like a model",
    "lovingly maintained", "charming", "exquisite", "impeccable",
    "breathtaking", "spectacular", "one-of-a-kind", "luxury living",
    # ... more
])
```

**Added phrases_that_work dictionary** with categorized insider vocabulary:

```python
phrases_that_work: dict[str, list[str]] = field(default_factory=lambda: {
    "architecture": [
        "the kind of [feature] that would cost six figures to reproduce",
        "bones are solid",
        "functionally new construction",
    ],
    "neighborhood_context": [
        "the quiet side of [street]",
        "before the neighborhood got loud about being a neighborhood",
        "[Neighborhood] lifers have been watching this one",
    ],
    "practical": [
        "the lot is the play here",
        "bring your architect",
        "needs everything, but the bones are there",
    ],
    "honest_assessments": [
        "it's tiny, but...",
        "the house is fine; the lot is the story",
        "layout's weird in a good way",
    ],
})
```

**File: `src/ai/claude_client.py`**

**Rewrote `generate_listing_description()` prompt** with mandatory neighborhood context:

```python
def generate_listing_description(self, listing: dict, voice_examples: list[str], avoid_phrases: list[str] | None = None) -> str:
    neighborhood = listing.get('neighborhood', 'N/A')
    neighborhood_context = ""
    if neighborhood and neighborhood != 'N/A':
        neighborhood_context = f"""
NEIGHBORHOOD CONTEXT REQUIREMENT:
You MUST include context about {neighborhood}. What's it like to live there?
What's nearby? What's the character of the streets? This is non-negotiable."""

    system = """You are writing for the Houston Housing Dispatch newsletter.

VOICE: Knowledgeable Houston insider—like Curbed, Brownstoner, or local food critics
like Alison Cook and Erica Chen. Someone who's watched neighborhoods evolve and
knows every street in the Inner Loop.
...
CRITICAL: Every description MUST include neighborhood context. Don't just describe
the house—describe what it's like to live in that location."""
```

### Part 2: Editorial Layer

**File: `src/ai/claude_client.py`**

**Added `edit_newsletter()` method** for full editorial pass:

```python
def edit_newsletter(self, content: str, listings: list[dict], avoid_phrases: list[str]) -> str:
    """
    Editorial pass to polish and unify newsletter content.
    Full editorial control to rewrite descriptions, add transitions,
    and ensure consistent insider voice throughout.
    """
    # Build immutable facts reference for the editor
    immutable_facts = []
    for listing in listings:
        facts = {
            "address": listing.get("address"),
            "price": f"${listing.get('price', 0):,}",
            "beds": listing.get("bedrooms"),
            # ...
        }
        immutable_facts.append(facts)

    prompt = f"""Edit this Houston Housing Dispatch newsletter draft.

You have FULL EDITORIAL CONTROL to:
- Rewrite listing descriptions to be more distinctive and insider-voiced
- Add connecting sentences between neighborhood sections
- Strengthen the intro paragraph

IMMUTABLE FACTS (must preserve exactly):
{immutable_facts}
..."""
```

**File: `src/generation/generator.py`**

**Implemented `_run_editorial_pass()` with retry and fallback:**

```python
def _run_editorial_pass(self, content: str, listings: list[Listing]) -> tuple[str, bool]:
    """Run editorial pass with fallback on failure."""
    try:
        edited = self.claude.edit_newsletter(
            content=content,
            listings=listing_dicts,
            avoid_phrases=self.voice.avoid_phrases,
        )

        # Validate factual accuracy
        if self._validate_editorial_output(listings, edited):
            return edited, True
        else:
            # Retry once
            edited = self.claude.edit_newsletter(...)
            if self._validate_editorial_output(listings, edited):
                return edited, True
            else:
                return content, False  # Fall back to pre-edit
    except Exception as e:
        return content, False  # Fall back to pre-edit
```

**Added `_validate_editorial_output()` for factual checking:**

```python
def _validate_editorial_output(self, listings: list[Listing], edited_content: str) -> bool:
    """Validate that editorial pass preserved factual details."""
    for listing in listings:
        price_str = f"${listing.price:,}"
        if price_str not in edited_content:
            return False
        if listing.address not in edited_content:
            return False
        if f"{listing.bedrooms} bed" not in edited_content.lower():
            return False
    return True
```

**Added `_scan_for_generic_phrases()` for quality warnings:**

```python
def _scan_for_generic_phrases(self, content: str) -> list[dict]:
    """Scan content for generic phrases that slipped through."""
    warnings = []
    for phrase in self.voice.avoid_phrases:
        if phrase.lower() in content.lower():
            warnings.append({"phrase": phrase, "context": "..."})
    return warnings
```

**Changed `_group_by_neighborhood()` to replace price tier grouping:**

```python
def _group_by_neighborhood(self, listings: list[Listing]) -> dict[str, list[Listing]]:
    """Group listings by neighborhood, maintaining order."""
    # Sort neighborhoods with premium ones first
    premium = [
        "Heights", "Montrose", "River Oaks", "West University", "West U",
        "Memorial", "Museum District", "Bellaire", "Meyerland", "Garden Oaks",
        "Oak Forest", "EaDo", "Midtown", "Southampton", "Tanglewood",
    ]
    # ...
```

**File: `src/generation/template_generator.py`**

**Added 35+ neighborhood contexts** for the template fallback generator.

---

## Verification

The implementation can be verified through:

1. **Unit tests for voice guide** - Confirm listing_examples has 12 entries, intro_examples has 6 entries, avoid_phrases has 32 entries

2. **Integration test for editorial pass** - Generate a newsletter with `skip_editorial=False` and verify:
   - `editorial_applied` returns `True` in the result dict
   - All prices, addresses, and bed/bath counts from input listings appear in output
   - `phrase_warnings` list is returned

3. **Validation logic test** - Mock a bad editorial output missing a price or address and confirm `_validate_editorial_output()` returns `False` and triggers retry

4. **Grouping test** - Pass listings from multiple neighborhoods and verify output is grouped by neighborhood (Heights, Montrose, etc.) not by price tier

5. **Generic phrase scan** - Include a listing with "stunning" in the raw description, generate newsletter, and verify `phrase_warnings` catches it

---

## Prevention Strategies

### How to Maintain Voice Quality Going Forward

**Quarterly Voice Audits**
Schedule quarterly reviews of newsletter output against the voice guide. Compare recent newsletters to the exemplar pieces. Look for drift patterns: gradual introduction of generic phrases, loss of neighborhood specificity, or creeping salesiness.

**Editorial Feedback Loop**
Maintain a running document of "voice wins" and "voice misses" from each newsletter. When the editorial pass catches a generic phrase, document what the AI wrote and what it was changed to. These corrections become training examples for prompt refinement.

**Prompt Version Control**
Treat AI prompts as code. Version them, review changes, and require approval before modifications. A small "improvement" to prompt wording can inadvertently flatten the voice.

### When to Update the Voice Guide Examples

**Trigger Events for Updates:**
- After covering a new neighborhood type (e.g., first historic district, first new construction area)
- When market conditions shift significantly
- After receiving reader feedback about tone mismatches
- Every 6 months minimum, even without triggers

### How to Expand Neighborhood Context Coverage

**Expansion Prioritization**
Rank neighborhoods by listing frequency. Prioritize building context for areas that appear most often.

**Local Knowledge Capture**
When the human editor adds neighborhood context during editorial review, capture that knowledge back into the reference profiles.

---

## Best Practices

### Writing Voice Guide Examples That Work

**Show, Don't Tell**
Bad: "Use warm, inviting language."
Good: Include a complete listing description that demonstrates warmth without ever using the word "warm."

**Contrast Pairs**
For every exemplar, include an anti-example:

```
AVOID: "This stunning home features an open floor plan perfect for entertaining!"
USE: "The dining room flows into the kitchen through a wide archway—enough space
     for a crowd, but the built-in breakfast nook still feels private."
```

### Structuring AI Prompts for Style Consistency

**Layered Prompt Architecture**
1. System-level: Publication identity and non-negotiable constraints
2. Style-level: Voice guide examples and anti-patterns
3. Task-level: Specific listing details and neighborhood context
4. Validation-level: Factual constraints that cannot be altered

**Explicit Prohibitions**
List banned phrases directly in the prompt.

**Neighborhood Injection Pattern**
Structure prompts to require neighborhood context as a mandatory field.

### Designing Editorial Passes with Validation

**Three-Pass Structure**
1. Pass 1: Factual Validation (prices, addresses, counts)
2. Pass 2: Voice Alignment (generic phrase scan, neighborhood context check)
3. Pass 3: Cohesion Review (narrative flow, transitions)

---

## Testing Recommendations

### Sample Assertions for Factual Validation

```python
def validate_listing_facts(generated: dict, source: dict) -> list[str]:
    """Return list of validation errors, empty if valid."""
    errors = []

    if generated["price"] != source["price"]:
        errors.append(f"Price mismatch: ${generated['price']} vs ${source['price']}")

    if generated["address"].lower() != source["address"].lower():
        errors.append(f"Address mismatch")

    if generated["bedrooms"] != source["bedrooms"]:
        errors.append(f"Bedroom count mismatch")

    return errors


def validate_no_generic_phrases(text: str) -> list[str]:
    """Return list of banned phrases found in text."""
    banned = [
        "won't last long", "priced to sell", "dream home", "stunning",
        "must see", "turnkey", "move-in ready", "perfect for entertaining",
    ]
    return [phrase for phrase in banned if phrase in text.lower()]
```

### Manual Review Checklist

**Pre-Publication Newsletter Review**

Factual Accuracy:
- [ ] All prices match source data exactly
- [ ] All addresses are correct and complete
- [ ] Bedroom and bathroom counts are accurate

Voice Quality:
- [ ] No generic real estate phrases
- [ ] Each listing includes neighborhood-specific context
- [ ] Descriptions feel observational, not promotional
- [ ] Consistent authorial voice throughout

Cohesion:
- [ ] Transitions between sections work
- [ ] No repetitive phrasing across listings
- [ ] Newsletter has a coherent narrative thread

---

## Related Documentation

### Planning & Design Documents

- **Brainstorm:** [docs/brainstorms/2026-03-01-newsletter-writing-style-brainstorm.md](../../brainstorms/2026-03-01-newsletter-writing-style-brainstorm.md)
- **Implementation Plan:** [docs/plans/2026-03-01-feat-newsletter-writing-style-improvement-plan.md](../../plans/2026-03-01-feat-newsletter-writing-style-improvement-plan.md)
- **Voice Examples Draft:** [docs/drafts/voice-examples-draft.md](../../drafts/voice-examples-draft.md)

### Implementation Files

- `src/generation/voice_guide.py` - Enhanced voice guide for AI content generation
- `src/ai/claude_client.py` - AI prompts and editorial pass method
- `src/generation/generator.py` - Core newsletter generation with editorial integration
- `src/generation/template_generator.py` - Template generation with 35+ neighborhood contexts

### Related Project Documentation

- **Project README:** [README.md](../../../README.md)
- **Original Automation Plan:** [docs/plans/2026-02-25-feat-houston-housing-dispatch-automation-plan.md](../../plans/2026-02-25-feat-houston-housing-dispatch-automation-plan.md)
