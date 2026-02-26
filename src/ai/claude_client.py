"""Claude API client wrapper for AI-powered operations."""

from typing import Any, Optional

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
        system: Optional[str] = None,
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
        system: Optional[str] = None,
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
        json_system = (system or "") + "\n\nYou must respond with valid JSON only. No markdown, no explanation, just JSON."

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
        Use Claude to score listings for interest/uniqueness.

        Args:
            listings: List of listing dicts with address, price, details, etc.

        Returns:
            List of listings with added 'ai_score' and 'ai_reasoning' fields
        """
        if not listings:
            return []

        prompt = f"""Analyze these Houston real estate listings and score each one for newsletter interest.

Consider these factors:
- Unique architectural features or history
- Value proposition (underpriced for area/size)
- Desirable neighborhoods (Heights, Montrose, River Oaks, West U, etc.)
- Interesting details that would engage readers
- New construction or well-renovated older homes

For each listing, provide:
- score: 0-100 (higher = more interesting for newsletter)
- reasoning: 1-2 sentences explaining why

Listings to analyze:
{listings}

Respond with JSON array matching the input order:
[
  {{"address": "...", "score": 85, "reasoning": "Historic Heights home with rare garage apartment..."}},
  ...
]
"""

        system = """You are an expert Houston real estate analyst helping curate a newsletter.
You understand what makes properties interesting to buyers and investors in the Houston market.
Focus on unique features, good value, and architectural interest."""

        result = self.complete_json(prompt, system=system)

        # Merge AI scores back into listings
        for i, listing in enumerate(listings):
            if i < len(result):
                listing["ai_score"] = result[i].get("score", 50)
                listing["ai_reasoning"] = result[i].get("reasoning", "")

        return listings

    def generate_listing_description(
        self,
        listing: dict,
        voice_examples: list[str],
    ) -> str:
        """
        Generate a newsletter description for a listing.

        Args:
            listing: Dict with listing details
            voice_examples: Example descriptions to match style

        Returns:
            Generated description text
        """
        examples_text = "\n\n".join(f"Example {i+1}:\n{ex}" for i, ex in enumerate(voice_examples))

        prompt = f"""Write a newsletter description for this Houston listing.

Listing details:
- Address: {listing.get('address')}
- Price: ${listing.get('price', 0):,}
- Beds: {listing.get('bedrooms')} / Baths: {listing.get('bathrooms')}
- Sqft: {listing.get('sqft', 'N/A')}
- Year built: {listing.get('year_built', 'N/A')}
- Neighborhood: {listing.get('neighborhood', 'N/A')}
- Type: {listing.get('property_type', 'N/A')}
- HAR description: {listing.get('description_raw', 'N/A')}

Match this writing style (2-3 sentences, observational, insider tone):

{examples_text}

Write the description now (just the description, no header):"""

        system = """You are writing for the Houston Housing Dispatch newsletter.
Your voice is conversational and knowledgeable - like a friend who really knows Houston real estate.
Focus on what makes properties interesting: unique features, neighborhood context, value.
Avoid generic real estate speak like "won't last long" or "stunning."
Be specific and observational."""

        return self.complete(prompt, system=system, max_tokens=500, temperature=0.8)

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

        examples_text = "\n\n".join(f"Example {i+1}:\n{ex}" for i, ex in enumerate(voice_examples))

        prompt = f"""Write a newsletter intro paragraph for this week's Houston Housing Dispatch.

This edition features:
- {len(listings)} properties
- Neighborhoods: {', '.join(neighborhoods[:5])}
- Price range: ${min_price:,} - ${max_price:,}

Match this intro style (2-3 sentences, sets context for the edition):

{examples_text}

Write the intro now (just the intro paragraph):"""

        system = """You are writing the opening paragraph for the Houston Housing Dispatch newsletter.
Set the tone for what's in this edition - mention 2-3 neighborhoods or themes.
Keep it brief (2-3 sentences) and conversational.
Avoid generic openers like "This week we have great listings!" """

        return self.complete(prompt, system=system, max_tokens=300, temperature=0.8)
