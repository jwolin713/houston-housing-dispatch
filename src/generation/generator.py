"""Newsletter content generator using Claude AI."""

from collections import defaultdict
from datetime import datetime
from typing import Optional

import structlog

from src.ai.claude_client import ClaudeClient
from src.generation.voice_guide import VoiceGuide
from src.models import Listing

logger = structlog.get_logger()


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
    ) -> dict:
        """
        Generate a complete newsletter from listings.

        Args:
            listings: List of selected Listing objects
            title: Optional custom title (generates one if None)

        Returns:
            Dict with 'title', 'intro', 'sections', 'markdown', 'html'
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
            section = {
                "neighborhood": neighborhood,
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

        # Assemble final content
        markdown = self._assemble_markdown(title, intro, sections)
        html = self._markdown_to_html(markdown)

        logger.info("Newsletter generated", sections=len(sections))

        return {
            "title": title,
            "intro": intro,
            "sections": sections,
            "markdown": markdown,
            "html": html,
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
            voice_examples=self.voice.listing_examples[:4],
        )

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
        premium = ["Heights", "Montrose", "River Oaks", "West University", "West U", "Memorial"]

        sorted_neighborhoods = sorted(
            by_neighborhood.keys(),
            key=lambda n: (n not in premium, n),
        )

        return {n: by_neighborhood[n] for n in sorted_neighborhoods}

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

        for section in sections:
            neighborhood = section["neighborhood"]
            lines.append(f"## {neighborhood}")
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
