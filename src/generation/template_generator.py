"""Template-based newsletter generator that doesn't require AI API credits."""

from collections import defaultdict
from datetime import datetime
from typing import Optional

import structlog

from src.models import Listing

logger = structlog.get_logger()


class TemplateNewsletterGenerator:
    """Generates newsletter content using templates instead of AI."""

    # Price tier descriptions
    PRICE_TIER_INTROS = {
        "under_300k": "Affordable options in this price range often represent the best value for first-time buyers or investors looking at the Houston market.",
        "300k_400k": "This sweet spot offers solid square footage and often includes newer construction or well-renovated older homes.",
        "400k_500k": "Properties in this range typically offer more space or more desirable locations than lower tiers.",
        "500k_750k": "This tier opens up access to larger homes in established neighborhoods with mature landscaping.",
        "over_750k": "Higher-end properties that often feature premium locations, architectural details, or significant lot sizes.",
    }

    # Neighborhood highlights (insider context for 35+ Houston neighborhoods)
    NEIGHBORHOOD_CONTEXT = {
        # Inner Loop - Premium
        "Heights": "Houston's most walkable neighborhood—Victorian bungalows, 19th Street shops, and the kind of tree cover that makes August survivable.",
        "Montrose": "Houston's cultural heart. Museum District access, eclectic architecture, and more restaurants per block than anywhere else in the city.",
        "River Oaks": "Old Houston money and mature oaks. The lots are bigger, the hedges are taller, and the property taxes are legendary.",
        "West University": "West U exists for the schools. Tree-lined streets, village feel, and home prices that reflect what parents will pay for HISD's top feeders.",
        "West U": "West U exists for the schools. Tree-lined streets, village feel, and home prices that reflect what parents will pay for HISD's top feeders.",
        "Southampton": "River Oaks adjacent without the River Oaks price tag—barely. Established streets with Rice University practically next door.",

        # Inner Loop - Emerging/Value
        "EaDo": "East Downtown's warehouse district turned brewery corridor. Walking distance to downtown, MLS stadium, and 8th Wonder.",
        "East Downtown": "East Downtown's warehouse district turned brewery corridor. Walking distance to downtown, MLS stadium, and 8th Wonder.",
        "Third Ward": "Historic Black neighborhood undergoing rapid change. TSU nearby, Emancipation Park restored, and development pressure everywhere.",
        "Midtown": "Light rail access to everywhere—downtown, Medical Center, Museum District. Urban density Houston-style.",
        "Rice Military": "Memorial Park on one side, Washington Avenue on the other. Townhome territory with actual walkability.",
        "Museum District": "The Menil, MFAH, and Hermann Park within walking distance. What Houston looks like when it tries.",

        # Inner Loop - Established
        "Memorial": "Memorial's sprawling lots and country club lifestyle. The kind of Houston wealth that doesn't need River Oaks zip codes.",
        "Tanglewood": "Galleria-adjacent but quieter. Mid-century ranches and traditional builds on generous lots.",
        "Meyerland": "Post-Harvey rebuilds and longtime residents who remember when this was considered far from everything.",
        "Bellaire": "Small-town city inside Houston. Asian grocery stores, good schools, and mid-century ranches holding their ground.",
        "Braeswood": "The bayou runs through it—literally. Jewish community roots, mature trees, and prices that reflect flood history.",

        # Inner Loop - Character Neighborhoods
        "Garden Oaks": "Oak Forest's quieter neighbor. Bungalows, double lots, and the occasional A-frame that's been there since the '60s.",
        "Oak Forest": "The '50s subdivision that aged well. Mid-century ranches, mature trees, and the kind of neighbors who wave.",
        "Eastwood": "First suburb in Houston, now feeling the eastside revival. Craftsman bungalows and proximity to EaDo.",
        "Woodland Heights": "Heights-adjacent with the prices to match. Historic bungalows and the White Oak Bayou trail.",

        # Medical Center / Museum Area
        "Medical Center": "Hospital scrubs and short commutes. Townhomes and condos for the 24/7 healthcare workforce.",
        "Hermann Park": "The park, the zoo, the golf course. What passes for Central Park in Houston.",

        # Outer Loop - Northwest
        "Spring Branch": "Spring Branch is having a moment—Korean restaurants, reasonable prices, and Memorial City access.",
        "Galleria": "Urban convenience, high-rise living, and walking-distance shopping. Houston's version of a city center.",

        # Outer Loop - West
        "Katy": "Master-planned communities, top-rated schools, and the energy corridor commute.",
        "Sugar Land": "Fort Bend schools and Town Square. Suburban Houston at its most polished.",

        # Outer Loop - North
        "The Woodlands": "The master-planned community that became its own city. Forests, trails, and Exxon campus.",
        "Humble": "Lake Houston access and IAH proximity. Old Humble oil town turned suburb.",
        "Kingwood": "The Livable Forest—trees, trails, and that Houston humidity keeping everything green.",
        "Cypress": "Northwest growth corridor. New construction, good schools, and the 290 commute.",

        # Outer Loop - South
        "Pearland": "South Houston suburb that grew up. Medical Center access and master-planned neighborhoods.",
        "Clear Lake": "NASA's backyard. Mid-century space-age architecture and Kemah boardwalk weekends.",
        "League City": "Where Clear Lake meets the Bay. Boating access and Galveston day trips.",

        # Catch-all
        "Other Areas": "Houston's sprawl means opportunity in unexpected places.",
    }

    def generate_newsletter(
        self,
        listings: list[Listing],
        title: Optional[str] = None,
    ) -> dict:
        """Generate a complete newsletter from listings using templates."""
        logger.info("Generating newsletter with templates", listing_count=len(listings))

        if not title:
            title = self._generate_title(listings)

        intro = self._generate_intro(listings)

        # Group by price tier
        by_price_tier = self._group_by_price_tier(listings)

        sections = []
        for tier_name, tier_listings in by_price_tier.items():
            section = {
                "tier": tier_name,
                "listings": [],
            }

            for listing in tier_listings:
                description = self._generate_listing_description(listing)
                listing.generated_description = description

                section["listings"].append({
                    "listing": listing,
                    "description": description,
                })

            sections.append(section)

        html = self._generate_html(title, intro, sections)
        markdown = self._generate_markdown(title, intro, sections)

        logger.info("Template newsletter generated", sections=len(sections))

        return {
            "title": title,
            "intro": intro,
            "sections": sections,
            "markdown": markdown,
            "html": html,
        }

    def _generate_title(self, listings: list[Listing]) -> str:
        """Generate a newsletter title."""
        date_str = datetime.now().strftime("%B %d, %Y")
        return f"Houston Housing Dispatch - {date_str}"

    def _generate_intro(self, listings: list[Listing]) -> str:
        """Generate the intro paragraph."""
        prices = [l.price for l in listings if l.price]
        neighborhoods = list(set(l.neighborhood for l in listings if l.neighborhood))[:3]

        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0

        neighborhood_str = ", ".join(neighborhoods) if neighborhoods else "various Houston neighborhoods"

        intro = f"This week's edition features {len(listings)} properties "
        intro += f"ranging from ${min_price:,} to ${max_price:,}. "

        if neighborhoods:
            intro += f"We're seeing interesting options in {neighborhood_str}. "

        # Add context based on price distribution
        mid_price = (min_price + max_price) / 2
        if mid_price < 350000:
            intro += "There are several accessible options for first-time buyers this week."
        elif mid_price < 500000:
            intro += "The inventory shows a healthy mix of starter homes and upgrade options."
        else:
            intro += "This week skews toward higher-end properties in established neighborhoods."

        return intro

    def _generate_listing_description(self, listing: Listing) -> str:
        """Generate a description for a single listing."""
        parts = []

        # Property type context
        prop_type = listing.property_type or "home"
        if "condo" in prop_type.lower():
            parts.append(f"This condo in {listing.neighborhood or 'Houston'}")
        elif "townhome" in prop_type.lower() or "townhouse" in prop_type.lower():
            parts.append(f"This townhome in {listing.neighborhood or 'Houston'}")
        else:
            parts.append(f"Located in {listing.neighborhood or 'Houston'}")

        # Size and bedroom context
        if listing.sqft:
            if listing.sqft > 2500:
                parts.append(f"offers generous space at {listing.sqft:,} square feet")
            elif listing.sqft > 1500:
                parts.append(f"provides solid living space with {listing.sqft:,} square feet")
            else:
                parts.append(f"delivers {listing.sqft:,} square feet")

        # Bedroom/bath context
        beds = listing.bedrooms or 0
        baths = listing.bathrooms or 0
        if beds >= 4:
            parts.append(f"with {beds} bedrooms for a growing family")
        elif beds == 3:
            parts.append(f"with {beds} bedrooms and {baths} baths")
        elif beds <= 2 and listing.price and listing.price < 300000:
            parts.append("representing good value for the area")

        # Year built context
        if listing.year_built:
            if listing.year_built >= 2020:
                parts.append("— newer construction with modern finishes")
            elif listing.year_built >= 2000:
                parts.append("in a building from the early 2000s")
            elif listing.year_built < 1960:
                parts.append("with the character of older Houston architecture")

        # Neighborhood-specific context
        neighborhood = listing.neighborhood or ""
        if neighborhood in self.NEIGHBORHOOD_CONTEXT:
            # Add shortened neighborhood context
            if "Heights" in neighborhood:
                parts.append("where walkability to local shops and restaurants adds value")
            elif "Montrose" in neighborhood:
                parts.append("in one of Houston's most culturally vibrant areas")
            elif "River Oaks" in neighborhood:
                parts.append("in Houston's most prestigious address")
            elif "EaDo" in neighborhood:
                parts.append("near the growing restaurant scene and stadium district")

        # Combine into a flowing description
        if len(parts) >= 3:
            desc = f"{parts[0]} {parts[1]}, {', '.join(parts[2:])}."
        elif len(parts) == 2:
            desc = f"{parts[0]} {parts[1]}."
        elif parts:
            desc = f"{parts[0]}."
        else:
            desc = f"A property worth considering at ${listing.price:,}."

        return desc

    def _group_by_price_tier(
        self,
        listings: list[Listing],
    ) -> dict[str, list[Listing]]:
        """Group listings by price tier."""
        tiers = defaultdict(list)

        for listing in sorted(listings, key=lambda l: l.price or 0):
            price = listing.price or 0

            if price < 300000:
                tiers["UNDER $300K"].append(listing)
            elif price < 400000:
                tiers["$300K - $400K"].append(listing)
            elif price < 500000:
                tiers["$400K - $500K"].append(listing)
            elif price < 750000:
                tiers["$500K - $750K"].append(listing)
            else:
                tiers["OVER $750K"].append(listing)

        return dict(tiers)

    def _generate_html(
        self,
        title: str,
        intro: str,
        sections: list[dict],
    ) -> str:
        """Generate HTML newsletter."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ font-size: 28px; margin-bottom: 10px; }}
        h2 {{ font-size: 20px; color: #333; margin-top: 30px; margin-bottom: 10px; }}
        .listing {{ margin-bottom: 25px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
        .listing:last-child {{ border-bottom: none; }}
        .price {{ font-size: 18px; font-weight: bold; color: #2a5934; }}
        .details {{ color: #666; font-size: 14px; margin: 5px 0; }}
        .description {{ margin-top: 10px; }}
        a {{ color: #1a73e8; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .intro {{ font-style: italic; color: #555; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #333; }}
        .section-header {{ background: #f5f5f5; padding: 10px 15px; margin: 30px 0 20px 0; font-size: 16px; font-weight: bold; }}
    </style>
</head>
<body>

<h1>Houston Housing Dispatch</h1>
<p class="intro">{intro}</p>
"""

        for section in sections:
            tier = section["tier"]
            html += f'\n<div class="section-header">{tier}</div>\n'

            for item in section["listings"]:
                listing = item["listing"]
                description = item["description"]

                beds_baths = f"{listing.bedrooms or '?'} bed / {listing.bathrooms or '?'} bath"
                sqft_str = f"{listing.sqft:,} sqft" if listing.sqft else ""
                neighborhood = listing.neighborhood or ""

                details_parts = [beds_baths]
                if sqft_str:
                    details_parts.append(sqft_str)
                if neighborhood:
                    details_parts.append(neighborhood)

                details = " | ".join(details_parts)

                html += f"""
<div class="listing">
    <div class="price">${listing.price:,}</div>
    <h2><a href="{listing.har_link}">{listing.address}</a></h2>
    <div class="details">{details}</div>
    <p class="description">{description}</p>
</div>
"""

        html += """
<hr style="margin: 40px 0; border: none; border-top: 2px solid #333;">

<p style="font-size: 14px; color: #666;">
That's it for this week. If you found something interesting, let me know—I always like hearing what catches readers' eyes.<br><br>
Until next time,<br>
<strong>Houston Housing Dispatch</strong>
</p>

</body>
</html>
"""
        return html

    def _generate_markdown(
        self,
        title: str,
        intro: str,
        sections: list[dict],
    ) -> str:
        """Generate markdown newsletter."""
        lines = [
            f"# {title}",
            "",
            f"*{intro}*",
            "",
            "---",
            "",
        ]

        for section in sections:
            tier = section["tier"]
            lines.append(f"## {tier}")
            lines.append("")

            for item in section["listings"]:
                listing = item["listing"]
                description = item["description"]

                beds_baths = f"{listing.bedrooms or '?'} bed / {listing.bathrooms or '?'} bath"
                sqft_str = f"{listing.sqft:,} sqft" if listing.sqft else ""

                lines.append(f"**${listing.price:,} — {listing.address}**")
                lines.append(f"*{beds_baths} | {sqft_str}*")
                lines.append("")
                lines.append(description)
                lines.append("")
                lines.append(f"[View on HAR]({listing.har_link})")
                lines.append("")
                lines.append("---")
                lines.append("")

        lines.append("")
        lines.append("*Houston Housing Dispatch*")

        return "\n".join(lines)
