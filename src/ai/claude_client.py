"""Claude API client wrapper for AI-powered operations."""

from typing import Any

import anthropic
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings

logger = structlog.get_logger()


class ClaudeClient:
    """Wrapper for Anthropic's Claude API."""

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    @property
    def client(self) -> anthropic.Anthropic:
        """Get the Anthropic client, initializing if needed."""
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a completion from Claude.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Returns:
            The generated text response
        """
        logger.debug(
            "Calling Claude API",
            model=self.settings.claude_model,
            prompt_length=len(prompt),
        )

        messages = [{"role": "user", "content": prompt}]

        response = self.client.messages.create(
            model=self.settings.claude_model,
            max_tokens=max_tokens,
            system=system if system else "",
            messages=messages,
            temperature=temperature,
        )

        result = response.content[0].text

        logger.debug(
            "Claude API response",
            response_length=len(result),
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        return result

    def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> Any:
        """
        Generate a JSON completion from Claude.

        Args:
            prompt: The user prompt (should request JSON output)
            system: Optional system prompt
            max_tokens: Maximum tokens in response

        Returns:
            Parsed JSON response
        """
        import json

        # Add JSON instruction to system prompt
        json_instruction = "\n\nYou must respond with valid JSON only. No markdown, no explanation, just JSON."
        json_system = (system or "") + json_instruction

        result = self.complete(
            prompt=prompt,
            system=json_system.strip(),
            max_tokens=max_tokens,
            temperature=0.3,  # Lower temperature for structured output
        )

        # Clean up response - remove markdown code blocks if present
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]

        return json.loads(result.strip())

    def score_listings(
        self,
        listings: list[dict],
    ) -> list[dict]:
        """
        Use Claude to score listings for newsletter editorial interest.

        Scoring is aligned with the Houston Housing Dispatch voice guide:
        "Interesting houses that can become long-lasting homes."

        Args:
            listings: List of listing dicts with address, price, details, etc.

        Returns:
            List of dicts with 'address', 'ai_score', and 'ai_reasoning' fields
        """
        if not listings:
            return []

        import json

        listings_text = json.dumps(listings, indent=2, default=str)

        prompt = f"""Score these Houston listings for newsletter inclusion (0-100).

For each listing, consider:
1. Does it have architectural character or distinctive features?
2. Is there a story here? (neighborhood context, history, notable details)
3. Would it make compelling newsletter content?
4. Does it fit "interesting houses that can become long-lasting homes"?

Score HIGH (70-100): Character homes, notable architecture, story potential, quirky or distinctive
Score MEDIUM (40-69): Decent homes but nothing particularly distinctive
Score LOW (0-39): Generic, cookie-cutter, bland new construction, or investor specials

Return a JSON array matching the input order:
[
  {{"address": "...", "score": 85, "reasoning": "1925 Heights bungalow with original hardwoods..."}},
  ...
]

Listings:
{listings_text}
"""

        system = """You are an editorial curator for the Houston Housing Dispatch, a real estate \
newsletter inspired by Curbed and Brownstoner. You're looking for interesting houses that can \
become long-lasting homes.

This is NOT an investment newsletter. Do NOT prioritize:
- Flipping potential or ROI
- Being "underpriced" or a "deal"
- Generic new construction without character

DO prioritize:
- Architectural character and distinctive design
- Story potential (history, neighborhood context, notable features)
- Properties that would make compelling, specific newsletter content
- Homes with "bones" - good structure that could become special
- Unique or quirky features worth highlighting
- Neighborhood identity and walkability context

Think: "Would a Curbed reader stop scrolling for this house?"
"""

        result = self.complete_json(prompt, system=system)

        # Normalize result into consistent format
        scored = []
        for i, item in enumerate(result):
            fallback_addr = listings[i].get("address", "") if i < len(listings) else ""
            scored.append({
                "address": item.get("address", fallback_addr),
                "ai_score": float(item.get("score", 50)),
                "ai_reasoning": item.get("reasoning", ""),
            })

        return scored

    def generate_listing_description(
        self,
        listing: dict,
        voice_examples: list[str],
        avoid_phrases: list[str] | None = None,
    ) -> str:
        """
        Generate a newsletter description for a single listing.

        Args:
            listing: Dict with listing details
            voice_examples: Example descriptions to match style
            avoid_phrases: List of generic phrases to avoid

        Returns:
            Generated description text
        """
        examples_text = "\n\n".join(f"Example {i+1}:\n{ex}" for i, ex in enumerate(voice_examples))

        # Build avoid phrases string
        avoid_str = ""
        if avoid_phrases:
            avoid_str = f"\n\nPHRASES TO NEVER USE: {', '.join(avoid_phrases[:15])}"

        neighborhood = listing.get('neighborhood', 'N/A')
        neighborhood_context = ""
        if neighborhood and neighborhood != 'N/A':
            neighborhood_context = f"""
NEIGHBORHOOD CONTEXT REQUIREMENT:
You MUST include context about {neighborhood}. What's it like to live there?
What's nearby? What's the character of the streets? This is non-negotiable."""

        prompt = f"""Write a newsletter description for this Houston listing.

LISTING DETAILS:
- Address: {listing.get('address')}
- Price: ${listing.get('price', 0):,}
- Beds: {listing.get('bedrooms')} / Baths: {listing.get('bathrooms')}
- Sqft: {listing.get('sqft', 'N/A')}
- Year built: {listing.get('year_built', 'N/A')}
- Neighborhood: {neighborhood}
- Type: {listing.get('property_type', 'N/A')}
- HAR description: {listing.get('description_raw', 'N/A')}
{neighborhood_context}

REQUIREMENTS:
1. Lead with what makes this property notable or interesting
2. Include at least ONE specific, memorable detail (architectural feature, practical quirk, honest observation)
3. Connect to the neighborhood—what's it like to actually live there?
4. 2-4 sentences, observational insider tone

EXAMPLE DESCRIPTIONS TO MATCH:

{examples_text}
{avoid_str}

Write the description now (just the description, no header or price):"""

        system = """You are writing for the Houston Housing Dispatch newsletter.

VOICE: Knowledgeable Houston insider—like Curbed, Brownstoner, or local food critics
like Alison Cook and Erica Chen. Someone who's watched neighborhoods evolve and
knows every street in the Inner Loop.

PHILOSOPHY: "Interesting houses that can become long-lasting homes"
Not investment returns or flipping potential. Character, quality, and fit.

TONE:
- Conversational insider (like texts from a friend who knows Houston real estate)
- Observational (notice details others miss)
- Practical (parking, layout, condition, what actually matters)
- Light editorial wit (occasional commentary without snark)

CRITICAL: Every description MUST include neighborhood context. Don't just describe
the house—describe what it's like to live in that location.

NEVER USE: "stunning," "gorgeous," "won't last long," "move-in ready," "must see,"
"perfect for entertaining," "close to everything," "dream home," or any generic
real estate agent speak."""

        return self.complete(prompt, system=system, max_tokens=500, temperature=0.8)

    def generate_all_listing_descriptions(
        self,
        listings: list[dict],
        voice_examples: list[str],
        avoid_phrases: list[str] | None = None,
    ) -> list[str]:
        """
        Generate descriptions for ALL listings in a single call.

        This produces better results than individual calls because the model
        can vary sentence structure, openers, and rhythm across listings,
        avoiding the repetitive patterns that emerge from isolated generation.

        Args:
            listings: List of listing dicts
            voice_examples: Example descriptions to match style
            avoid_phrases: List of generic phrases to avoid

        Returns:
            List of description strings, one per listing (same order as input)
        """
        if not listings:
            return []

        examples_text = "\n\n".join(f"Example {i+1}:\n{ex}" for i, ex in enumerate(voice_examples))

        avoid_str = ""
        if avoid_phrases:
            avoid_str = f"\n\nPHRASES TO NEVER USE: {', '.join(avoid_phrases[:20])}"

        # Build listing details block
        listings_block = []
        for i, listing in enumerate(listings, 1):
            neighborhood = listing.get('neighborhood', 'N/A')
            block = f"""LISTING {i}:
- Address: {listing.get('address')}
- Price: ${listing.get('price', 0):,}
- Beds: {listing.get('bedrooms')} / Baths: {listing.get('bathrooms')}
- Sqft: {listing.get('sqft', 'N/A')}
- Year built: {listing.get('year_built', 'N/A')}
- Neighborhood: {neighborhood}
- Type: {listing.get('property_type', 'N/A')}
- HAR description: {listing.get('description_raw', 'N/A')}"""
            listings_block.append(block)

        all_listings_text = "\n\n".join(listings_block)

        prompt = f"""Write newsletter descriptions for these {len(listings)} Houston listings.

{all_listings_text}

REQUIREMENTS FOR EACH DESCRIPTION:
1. 2-4 sentences, observational insider tone
2. Lead with what makes the property notable or interesting
3. Include at least ONE specific, memorable detail
4. Connect to the neighborhood—what's it like to actually live there?

CRITICAL — VARIETY AND FLOW:
You are writing these as part of ONE newsletter. Readers will see them all together.
- VARY your sentence openers. Do NOT start multiple descriptions the same way.
- VARY sentence length and rhythm. Mix short punchy sentences with longer ones.
- VARY your angle of approach: lead with the building on one, the neighborhood on another, the lot on a third, an honest observation on a fourth.
- If two listings are in the same neighborhood, differentiate them—don't repeat the same neighborhood context.
- Avoid structural repetition. If one listing uses "[Feature], which means [benefit]", don't use that pattern again.

EXAMPLE DESCRIPTIONS TO MATCH (for voice, not structure—don't copy these patterns verbatim):

{examples_text}
{avoid_str}

FORMAT: Return each description separated by "---". Just the descriptions, no headers, prices, or listing numbers. The order must match the listing order above."""

        system = """You are writing for the Houston Housing Dispatch newsletter.

VOICE: Knowledgeable Houston insider—like Curbed, Brownstoner, or local food critics
like Alison Cook and Erica Chen. Someone who's watched neighborhoods evolve and
knows every street in the Inner Loop.

PHILOSOPHY: "Interesting houses that can become long-lasting homes"
Not investment returns or flipping potential. Character, quality, and fit.

TONE:
- Conversational insider (like texts from a friend who knows Houston real estate)
- Observational (notice details others miss)
- Practical (parking, layout, condition, what actually matters)
- Light editorial wit (occasional commentary without snark)

CRITICAL RULES:
1. Every description MUST include neighborhood context.
2. Each description must feel different from the others—vary your sentence structure,
   openers, length, and approach. A reader should never think "this sounds like the
   last one." Think of each listing as a different paragraph in a magazine feature.
3. NEVER USE: "stunning," "gorgeous," "won't last long," "move-in ready," "must see,"
   "perfect for entertaining," "close to everything," "dream home," or any generic
   real estate agent speak."""

        # Scale max_tokens based on listing count (roughly 150 tokens per listing + overhead)
        max_tokens = min(len(listings) * 200 + 200, 8000)

        result = self.complete(prompt, system=system, max_tokens=max_tokens, temperature=0.8)

        # Parse the "---" separated descriptions
        descriptions = [d.strip() for d in result.split("---") if d.strip()]

        # If parsing didn't produce the right count, try to salvage
        if len(descriptions) != len(listings):
            logger.warning(
                "Batch description count mismatch",
                expected=len(listings),
                got=len(descriptions),
            )
            # Pad with empty strings or truncate
            while len(descriptions) < len(listings):
                descriptions.append("")
            descriptions = descriptions[:len(listings)]

        return descriptions

    def generate_newsletter_intro(
        self,
        listings: list[dict],
        voice_examples: list[str],
    ) -> str:
        """
        Generate the newsletter intro paragraph.

        Args:
            listings: List of selected listings
            voice_examples: Example intro paragraphs

        Returns:
            Generated intro text
        """
        # Summarize neighborhoods and price ranges
        neighborhoods = list(set(l.get("neighborhood") for l in listings if l.get("neighborhood")))
        prices = [l.get("price", 0) for l in listings]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        # Find notable properties for the intro
        notable_properties = []
        for listing in listings[:5]:
            notable = f"{listing.get('neighborhood', 'Unknown')}: ${listing.get('price', 0):,}"
            if listing.get('year_built'):
                notable += f" ({listing.get('year_built')})"
            notable_properties.append(notable)

        examples_text = "\n\n".join(f"Example {i+1}:\n{ex}" for i, ex in enumerate(voice_examples))

        prompt = f"""Write a newsletter intro paragraph for this week's Houston Housing Dispatch.

THIS EDITION FEATURES:
- {len(listings)} properties
- Neighborhoods: {', '.join(neighborhoods[:6])}
- Price range: ${min_price:,} - ${max_price:,}
- Notable listings: {'; '.join(notable_properties)}

REQUIREMENTS:
1. Hook readers with what's interesting THIS week (not generic "great listings")
2. Mention 2-3 specific neighborhoods or themes
3. Set insider tone from the first sentence
4. 2-3 sentences max

EXAMPLE INTROS TO MATCH:

{examples_text}

Write the intro now (just the intro paragraph):"""

        system = """You are writing the opening paragraph for the Houston Housing Dispatch newsletter.

VOICE: Knowledgeable Houston insider—like Curbed, Brownstoner, or local food critics.
Someone readers trust to know which listings are actually worth their time.

APPROACH:
- Lead with what's notable or unusual about this week's mix
- Reference specific neighborhoods with insider familiarity
- Set expectations without being promotional
- Conversational, not salesy—like a friend summarizing what's worth looking at

NEVER START WITH:
- "This week we have..."
- "Check out these..."
- "Welcome to..."
- Any generic real estate opener"""

        return self.complete(prompt, system=system, max_tokens=300, temperature=0.8)

    def edit_newsletter(
        self,
        content: str,
        listings: list[dict],
        avoid_phrases: list[str],
    ) -> str:
        """
        Editorial pass to polish and unify newsletter content.

        Full editorial control to rewrite descriptions, add transitions,
        and ensure consistent insider voice throughout.

        Args:
            content: The raw newsletter content in markdown
            listings: List of listing dicts (for factual validation reference)
            avoid_phrases: List of generic phrases to eliminate

        Returns:
            Polished newsletter content
        """
        # Build immutable facts reference for the editor
        immutable_facts = []
        for listing in listings:
            facts = {
                "address": listing.get("address"),
                "price": f"${listing.get('price', 0):,}",
                "beds": listing.get("bedrooms"),
                "baths": listing.get("bathrooms"),
                "sqft": listing.get("sqft"),
                "year_built": listing.get("year_built"),
                "neighborhood": listing.get("neighborhood"),
            }
            immutable_facts.append(facts)

        avoid_str = ", ".join(f'"{p}"' for p in avoid_phrases[:20])

        prompt = f"""Edit this Houston Housing Dispatch newsletter draft.

You have FULL EDITORIAL CONTROL to:
- Rewrite listing descriptions to be more distinctive and insider-voiced
- Add connecting sentences between neighborhood sections
- Strengthen the intro paragraph
- Improve flow and variety in sentence structure
- Remove any generic real estate language

IMMUTABLE FACTS (must preserve exactly):
{immutable_facts}

PHRASES TO ELIMINATE:
{avoid_str}

CURRENT DRAFT:
{content}

OUTPUT:
Return the complete polished newsletter in markdown format.
Every listing must still include its price, address, and key details.
Add connecting sentences between neighborhood sections to create narrative flow."""

        system = """You are the editor of Houston Housing Dispatch, a real estate newsletter
with the voice of a knowledgeable Houston insider—think Curbed, Brownstoner, or
local food critics like Alison Cook and Erica Chen.

Your job is to polish this newsletter draft into a cohesive, engaging read.

VOICE GUIDELINES:
- Conversational insider tone—like a friend who knows Houston neighborhoods deeply
- Observational and specific—notice details others miss
- Practical focus—parking, layout, condition, what matters to buyers
- Light editorial wit—occasional commentary without snark

YOUR #1 PRIORITY: ELIMINATE REPETITIVE STRUCTURE.
Read through the entire draft and identify repeated patterns:
- Sentence openers that appear more than once (e.g., "The lot is...", "You're close to...")
- Structural templates used across listings (e.g., "[Feature], which means [benefit]")
- Repeated transitional phrases or rhythms
- Same types of observations in the same order (building → neighborhood → practical note)

Fix these by:
- Varying how descriptions start: some with the building, some with the neighborhood,
  some with a practical observation, some with an honest editorial take
- Mixing sentence lengths: a short punchy sentence, then a longer flowing one
- Using different connective tissue: em dashes, parenthetical asides, direct address
- Occasionally breaking the pattern entirely with a one-sentence description or a
  slightly longer treatment for a standout property

WHAT YOU CAN CHANGE:
- Rewrite listing descriptions to be more distinctive
- Add brief connecting sentences between neighborhood sections
- Strengthen the intro to hook readers
- Remove any generic real estate language that slipped through
- Restructure descriptions that feel samey

WHAT YOU CANNOT CHANGE (these are factual and must appear exactly):
- Prices (dollar amounts)
- Addresses
- Bedroom/bathroom counts
- Square footage
- Year built
- HAR links
- Neighborhood names

The newsletter should read like a magazine column, not a list of property descriptions
that were generated from the same template."""

        logger.info("Running editorial pass on newsletter")
        return self.complete(prompt, system=system, max_tokens=8000, temperature=0.7)
