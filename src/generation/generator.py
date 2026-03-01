"""Newsletter content generator using Claude AI."""

import re
from collections import defaultdict
from datetime import datetime
from typing import Optional

import structlog

from src.ai.claude_client import ClaudeClient
from src.generation.voice_guide import VoiceGuide
from src.models import Listing

logger = structlog.get_logger()


class EditorialValidationError(Exception):
    """Raised when editorial pass changes factual details."""

    pass


class NewsletterGenerator:
    """Generates newsletter content from curated listings."""

    def __init__(
        self,
        claude_client: Optional[ClaudeClient] = None,
        voice_guide: Optional[VoiceGuide] = None,
    ):
        """
        Initialize the generator.

        Args:
            claude_client: ClaudeClient instance (creates default if None)
            voice_guide: VoiceGuide instance (creates default if None)
        """
        self.claude = claude_client or ClaudeClient()
        self.voice = voice_guide or VoiceGuide()

    def generate_newsletter(
        self,
        listings: list[Listing],
        title: Optional[str] = None,
        skip_editorial: bool = False,
    ) -> dict:
        """
        Generate a complete newsletter from listings.

        Args:
            listings: List of selected Listing objects
            title: Optional custom title (generates one if None)
            skip_editorial: If True, skip the editorial pass (for testing/debugging)

        Returns:
            Dict with 'title', 'intro', 'sections', 'markdown', 'html', 'phrase_warnings'
        """
        logger.info("Generating newsletter", listing_count=len(listings))

        # Generate title if not provided
        if not title:
            title = self._generate_title(listings)

        # Generate intro paragraph
        intro = self._generate_intro(listings)

        # Group listings by neighborhood
        by_neighborhood = self._group_by_neighborhood(listings)

        # Generate descriptions for each listing
        sections = []
        for neighborhood, neighborhood_listings in by_neighborhood.items():
            # Generate neighborhood intro sentence
            neighborhood_intro = self._generate_neighborhood_intro(
                neighborhood, neighborhood_listings
            )

            section = {
                "neighborhood": neighborhood,
                "neighborhood_intro": neighborhood_intro,
                "listings": [],
            }

            for listing in neighborhood_listings:
                description = self._generate_listing_description(listing)
                listing.generated_description = description

                section["listings"].append({
                    "listing": listing,
                    "description": description,
                })

            sections.append(section)

        # Assemble pre-edit content
        pre_edit_markdown = self._assemble_markdown(title, intro, sections)

        # Run editorial pass (with fallback)
        if not skip_editorial:
            markdown, editorial_applied = self._run_editorial_pass(
                pre_edit_markdown, listings
            )
        else:
            markdown = pre_edit_markdown
            editorial_applied = False

        # Scan for generic phrases
        phrase_warnings = self._scan_for_generic_phrases(markdown)

        # Convert to HTML
        html = self._markdown_to_html(markdown)

        logger.info(
            "Newsletter generated",
            sections=len(sections),
            editorial_applied=editorial_applied,
            phrase_warnings=len(phrase_warnings),
        )

        return {
            "title": title,
            "intro": intro,
            "sections": sections,
            "markdown": markdown,
            "html": html,
            "phrase_warnings": phrase_warnings,
            "editorial_applied": editorial_applied,
        }

    def _generate_title(self, listings: list[Listing]) -> str:
        """Generate a newsletter title."""
        # Get featured neighborhoods
        neighborhoods = list(set(
            l.neighborhood for l in listings
            if l.neighborhood
        ))[:3]

        # Get date
        date_str = datetime.now().strftime("%B %d, %Y")

        if neighborhoods:
            return f"Houston Housing Dispatch: {', '.join(neighborhoods)} & More — {date_str}"
        return f"Houston Housing Dispatch — {date_str}"

    def _generate_intro(self, listings: list[Listing]) -> str:
        """Generate the intro paragraph using Claude."""
        listing_dicts = [
            {
                "address": l.address,
                "price": l.price,
                "neighborhood": l.neighborhood,
                "bedrooms": l.bedrooms,
                "bathrooms": l.bathrooms,
                "year_built": l.year_built,
                "property_type": l.property_type,
            }
            for l in listings
        ]

        return self.claude.generate_newsletter_intro(
            listings=listing_dicts,
            voice_examples=self.voice.intro_examples,
        )

    def _generate_listing_description(self, listing: Listing) -> str:
        """Generate a description for a single listing."""
        listing_dict = {
            "address": listing.address,
            "price": listing.price,
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "sqft": listing.sqft,
            "year_built": listing.year_built,
            "neighborhood": listing.neighborhood,
            "property_type": listing.property_type,
            "description_raw": listing.description_raw,
        }

        return self.claude.generate_listing_description(
            listing=listing_dict,
            voice_examples=self.voice.listing_examples[:6],
            avoid_phrases=self.voice.avoid_phrases,
        )

    def _generate_neighborhood_intro(
        self,
        neighborhood: str,
        listings: list[Listing],
    ) -> str:
        """Generate a brief intro sentence for a neighborhood section."""
        # For now, generate simple contextual intros
        # Could be expanded to use Claude for more dynamic intros
        count = len(listings)
        price_range = ""
        if listings:
            prices = [l.price for l in listings]
            min_p = min(prices)
            max_p = max(prices)
            if min_p == max_p:
                price_range = f"at ${min_p:,}"
            else:
                price_range = f"from ${min_p:,} to ${max_p:,}"

        if count == 1:
            return f"One listing {price_range} in {neighborhood}."
        return f"{count} listings {price_range} across {neighborhood}."

    def _group_by_neighborhood(
        self,
        listings: list[Listing],
    ) -> dict[str, list[Listing]]:
        """Group listings by neighborhood, maintaining order."""
        by_neighborhood = defaultdict(list)

        for listing in listings:
            neighborhood = listing.neighborhood or "Other Areas"
            by_neighborhood[neighborhood].append(listing)

        # Sort neighborhoods with premium ones first
        premium = [
            "Heights", "Montrose", "River Oaks", "West University", "West U",
            "Memorial", "Museum District", "Bellaire", "Meyerland", "Garden Oaks",
            "Oak Forest", "EaDo", "Midtown", "Southampton", "Tanglewood",
        ]

        sorted_neighborhoods = sorted(
            by_neighborhood.keys(),
            key=lambda n: (n not in premium, n),
        )

        return {n: by_neighborhood[n] for n in sorted_neighborhoods}

    def _run_editorial_pass(
        self,
        content: str,
        listings: list[Listing],
    ) -> tuple[str, bool]:
        """
        Run editorial pass with fallback on failure.

        Args:
            content: Pre-edit markdown content
            listings: List of listings for validation

        Returns:
            Tuple of (edited_content, editorial_applied)
        """
        listing_dicts = [
            {
                "address": l.address,
                "price": l.price,
                "bedrooms": l.bedrooms,
                "bathrooms": l.bathrooms,
                "sqft": l.sqft,
                "year_built": l.year_built,
                "neighborhood": l.neighborhood,
            }
            for l in listings
        ]

        try:
            logger.info("Running editorial pass")
            edited = self.claude.edit_newsletter(
                content=content,
                listings=listing_dicts,
                avoid_phrases=self.voice.avoid_phrases,
            )

            # Validate factual accuracy
            if self._validate_editorial_output(listings, edited):
                logger.info("Editorial pass completed successfully")
                return edited, True
            else:
                logger.warning("Editorial validation failed, retrying once")
                # Retry once
                edited = self.claude.edit_newsletter(
                    content=content,
                    listings=listing_dicts,
                    avoid_phrases=self.voice.avoid_phrases,
                )
                if self._validate_editorial_output(listings, edited):
                    return edited, True
                else:
                    logger.error("Editorial validation failed twice, using pre-edit content")
                    return content, False

        except Exception as e:
            logger.error("Editorial pass failed", error=str(e))
            return content, False

    def _validate_editorial_output(
        self,
        listings: list[Listing],
        edited_content: str,
    ) -> bool:
        """
        Validate that editorial pass preserved factual details.

        Args:
            listings: Original listings with facts
            edited_content: Edited newsletter content

        Returns:
            True if all facts are preserved, False otherwise
        """
        for listing in listings:
            # Check price appears (with some flexibility for formatting)
            price_str = f"${listing.price:,}"
            if price_str not in edited_content:
                logger.warning(
                    "Price missing from edited content",
                    address=listing.address,
                    expected_price=price_str,
                )
                return False

            # Check address appears
            if listing.address not in edited_content:
                logger.warning(
                    "Address missing from edited content",
                    address=listing.address,
                )
                return False

            # Check bedroom count appears somewhere
            beds_pattern = f"{listing.bedrooms} bed"
            if beds_pattern not in edited_content.lower():
                logger.warning(
                    "Bedroom count missing from edited content",
                    address=listing.address,
                    expected_beds=listing.bedrooms,
                )
                return False

        return True

    def _scan_for_generic_phrases(self, content: str) -> list[dict]:
        """
        Scan content for generic phrases that slipped through.

        Args:
            content: Newsletter content to scan

        Returns:
            List of warnings with phrase and context
        """
        warnings = []
        content_lower = content.lower()

        for phrase in self.voice.avoid_phrases:
            if phrase.lower() in content_lower:
                # Find context around the phrase
                idx = content_lower.find(phrase.lower())
                start = max(0, idx - 30)
                end = min(len(content), idx + len(phrase) + 30)
                context = content[start:end]

                warnings.append({
                    "phrase": phrase,
                    "context": f"...{context}...",
                })
                logger.warning(
                    "Generic phrase detected",
                    phrase=phrase,
                    context=context,
                )

        return warnings

    def _assemble_markdown(
        self,
        title: str,
        intro: str,
        sections: list[dict],
    ) -> str:
        """Assemble the full newsletter markdown."""
        lines = [
            f"# {title}",
            "",
            intro,
            "",
            "---",
            "",
        ]

        for i, section in enumerate(sections):
            neighborhood = section["neighborhood"]
            neighborhood_intro = section.get("neighborhood_intro", "")

            lines.append(f"## {neighborhood}")
            lines.append("")

            # Add neighborhood intro if present
            if neighborhood_intro:
                lines.append(f"*{neighborhood_intro}*")
                lines.append("")

            for item in section["listings"]:
                listing = item["listing"]
                description = item["description"]

                # Format listing header
                price_str = f"${listing.price:,}"
                beds_baths = f"{listing.bedrooms} bed / {listing.bathrooms} bath"
                sqft_str = f"{listing.sqft:,} sqft" if listing.sqft else ""
                type_str = listing.property_type or ""
                year_str = str(listing.year_built) if listing.year_built else ""

                details = " / ".join(filter(None, [beds_baths, sqft_str, type_str, year_str]))

                lines.append(f"**{price_str} — {listing.address}**")
                lines.append(f"*{details}*")
                lines.append("")
                lines.append(description)
                lines.append("")
                lines.append(f"[View on HAR]({listing.har_link})")
                lines.append("")
                lines.append("---")
                lines.append("")

        # Footer
        lines.append("")
        lines.append("That's it for this week. If you found something interesting, let me know.")
        lines.append("")
        lines.append("*Houston Housing Dispatch is a curated guide to interesting homes on the market. ")
        lines.append("Not affiliated with HAR or any real estate agency.*")

        return "\n".join(lines)

    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML for Substack."""
        # Simple markdown to HTML conversion
        # For production, consider using a proper markdown library

        html_lines = []
        in_paragraph = False

        for line in markdown.split("\n"):
            line = line.strip()

            if not line:
                if in_paragraph:
                    html_lines.append("</p>")
                    in_paragraph = False
                continue

            # Headers
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")

            # Horizontal rule
            elif line == "---":
                html_lines.append("<hr>")

            # Bold
            elif line.startswith("**") and line.endswith("**"):
                html_lines.append(f"<p><strong>{line[2:-2]}</strong></p>")

            # Italic
            elif line.startswith("*") and line.endswith("*") and not line.startswith("**"):
                html_lines.append(f"<p><em>{line[1:-1]}</em></p>")

            # Links
            elif line.startswith("[") and "](" in line and line.endswith(")"):
                import re
                match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", line)
                if match:
                    text, url = match.groups()
                    html_lines.append(f'<p><a href="{url}">{text}</a></p>')

            # Regular paragraph
            else:
                if not in_paragraph:
                    html_lines.append("<p>")
                    in_paragraph = True
                html_lines.append(line)

        if in_paragraph:
            html_lines.append("</p>")

        return "\n".join(html_lines)

    def regenerate_listing(
        self,
        listing: Listing,
        feedback: Optional[str] = None,
    ) -> str:
        """
        Regenerate a listing description, optionally incorporating feedback.

        Args:
            listing: The listing to regenerate
            feedback: Optional feedback about what to change

        Returns:
            New description text
        """
        listing_dict = {
            "address": listing.address,
            "price": listing.price,
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "sqft": listing.sqft,
            "year_built": listing.year_built,
            "neighborhood": listing.neighborhood,
            "property_type": listing.property_type,
            "description_raw": listing.description_raw,
            "previous_description": listing.generated_description,
            "feedback": feedback,
        }

        prompt_addition = ""
        if feedback:
            prompt_addition = f"\n\nPrevious description:\n{listing.generated_description}\n\nFeedback to incorporate:\n{feedback}"

        return self.claude.generate_listing_description(
            listing=listing_dict,
            voice_examples=self.voice.listing_examples[:4],
        )
