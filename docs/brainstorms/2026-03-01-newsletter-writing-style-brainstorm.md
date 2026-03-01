# Brainstorm: Improve Newsletter Writing Style

**Date:** 2026-03-01
**Status:** Ready for planning

---

## What We're Building

Improve the Houston Housing Dispatch newsletter writing style to feel like a knowledgeable Houston insider—not generic real estate copy. The goal is content that reads like Curbed, Brownstoner, or a local food critic (Alison Cook, Erica Chen): authoritative, opinionated, and deeply familiar with the city.

**Two-part approach:**
1. **Enhanced Voice Guide + Prompts** — Rewrite voice examples and AI prompts to enforce the insider tone
2. **Editorial Layer** — Add an AI "editor" pass to polish content and add connecting tissue

---

## Why This Approach

The current system has a voice guide, but output still feels too generic/salesy. The root causes:

- **Prompts don't enforce neighborhood context** — Descriptions focus on property features, not what it's like to live there
- **Examples aren't distinctive enough** — Need sharper, more opinionated samples
- **No editorial cohesion** — Each listing stands alone; no narrative thread through the newsletter
- **Wrong grouping** — Price tiers don't match how readers think (they search by neighborhood)

Combining better prompts with an editorial pass addresses both the input quality and the output polish.

---

## Key Decisions

### Tone & Voice
- **Knowledgeable insider** — Someone who's watched Houston neighborhoods evolve
- **Inspirations:** Curbed, The Infatuation, Brownstoner, Alison Cook, Erica Chen
- **Not:** Salesy, generic, investor-focused

### What Descriptions Should Highlight
1. **Neighborhood context** — What's nearby, walkability, vibe of the area
2. **Unique features** — Architectural quirks, history, memorable details
3. **Value angle (sparingly)** — Not every listing; this isn't a deals newsletter

### Core Philosophy
> "Interesting houses that can become long-lasting homes"

Not about price-first or investment returns. About character, quality, and fit.

### Audience
- First-time buyers navigating Houston for the first time
- Move-up buyers who know the market and want something better
- Design-conscious buyers who appreciate architecture and renovation quality
- **Not:** Investors/flippers

### Newsletter Structure Changes
- **Group by neighborhood** (not price tier) — Readers search by area
- **Stronger intro hooks** — Set context for what's interesting this week
- **More editorial voice throughout** — Connecting tissue between sections

---

## Implementation Components

### Part 1: Voice Guide + Prompt Rewrite

1. **Rewrite `voice_guide.py`**
   - Add Curbed/Brownstoner-style example descriptions
   - Include neighborhood-specific context examples
   - Sharper "phrases to avoid" list
   - Add "phrases that work" with insider language

2. **Rewrite AI prompts in `claude_client.py`**
   - Enforce neighborhood context in every description
   - Require one unique/memorable detail per listing
   - Reference inspiration publications in system prompt
   - Better few-shot examples

3. **Update template generator**
   - Richer neighborhood context snippets
   - Better property-type descriptions
   - Remove generic fallback language

4. **Change grouping logic**
   - Group listings by neighborhood instead of price tier
   - Add neighborhood intro sentences

### Part 2: Editorial Layer

1. **Add editor pass after generation**
   - Review all descriptions for generic language
   - Add connecting sentences between neighborhood sections
   - Strengthen intro paragraph based on full content
   - Ensure consistent voice throughout

2. **Editor prompt design**
   - "You are the editor of Houston Housing Dispatch..."
   - Reference the same voice inspirations
   - Focus on cohesion and narrative flow

---

## Resolved Questions

1. **How much API cost is acceptable for the editorial pass?**
   - **Decision:** Worth it. Quality matters more than cost.

2. **Should the editorial pass rewrite descriptions, or just add connecting tissue?**
   - **Decision:** Full editorial control. Editor can rewrite everything with a cohesive narrative voice.

3. **Do you want to review/approve the new voice guide examples before implementation?**
   - **Decision:** Yes. Write a draft of new examples and iterate together before implementing.

---

## Success Criteria

- Newsletter reads like a knowledgeable friend, not a real estate agent
- Each neighborhood section has context about the area
- Intro paragraph hooks readers with what's interesting this week
- Descriptions highlight unique features, not just bed/bath counts
- No generic phrases ("won't last long", "move-in ready", etc.)
- Readers feel like they're getting insider perspective on Houston real estate
