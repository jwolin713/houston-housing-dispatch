"""Editorial voice guide for the Houston Housing Dispatch newsletter.

Voice: Knowledgeable Houston insider—like Curbed, Brownstoner, or local food critics
(Alison Cook, Erica Chen). Someone who's watched neighborhoods evolve and knows
every street in the Inner Loop.

Philosophy: "Interesting houses that can become long-lasting homes"
"""

from dataclasses import dataclass, field


@dataclass
class VoiceGuide:
    """
    Editorial voice guide with examples for AI-powered content generation.

    Based on:
    - Curbed, The Infatuation, Brownstoner style
    - Local Houston critics (Alison Cook, Erica Chen)
    - Core philosophy: character, quality, fit—not investment returns
    """

    # Listing description examples (Curbed/Brownstoner style)
    listing_examples: list[str] = field(default_factory=lambda: [
        # Heights / Historic
        "The kind of Heights bungalow that used to go for under $400K—back when that "
        "was a lot for the neighborhood. This one's been updated without erasing its "
        "history: original pine floors sanded back to life, period-appropriate trim "
        "work, and a kitchen that acknowledges microwaves exist. The lot's tight but "
        "the mature pecan in back provides actual shade, not just landscaping.",

        "One of the oldest houses in the Heights still standing, and it shows in the "
        "best ways—12-foot ceilings, transom windows, the kind of woodwork that would "
        "cost six figures to reproduce today. Previous owner ran it as an Airbnb, so "
        "everything's been permitted and updated behind the walls.",

        # Montrose / Museum District
        "Three-story Montrose townhome on the quiet side of Westheimer, which means "
        "you can walk to Hugo's for Sunday brunch without crossing six lanes of traffic. "
        "The rooftop deck actually gets used here—downtown views, room for a grill, and "
        "enough space that your guests aren't standing in single file.",

        "Former fourplex converted to a single-family in the '90s, which means you're "
        "getting 3,400 square feet for what one-story ranches cost nearby. The bones "
        "are solid—poured concrete foundation, real plaster walls—and the layout's "
        "weird in a good way. Two blocks from the Menil.",

        # EaDo / Midtown
        "One of the first loft conversions in EaDo before the neighborhood got loud "
        "about being a neighborhood. The 16-foot ceilings and original brick aren't "
        "affected—that's the whole point. Walking distance to 8th Wonder and not "
        "hearing your neighbor's Peloton through the walls.",

        "A legitimate 1930s cottage in Midtown that somehow survived the townhome rush. "
        "It's tiny—950 square feet, two bedrooms, one bath—but the lot is the story. "
        "Oversized for the block, mature oaks, and enough room for an ADU if the city "
        "ever makes permitting reasonable.",

        # West U / Bellaire / Meyerland
        "West U finally has something under $1.5M, and here's the catch: it needs "
        "everything. Roof, HVAC, kitchen, baths—the full gut job. But the bones are "
        "there: 8,000 square foot lot on a quiet street, original hardwoods that could "
        "come back to life, and room for a pool without sacrificing the entire backyard.",

        "One of those Bellaire ranches that real estate Twitter argues about—is it "
        "worth saving, or is the lot the value? We'd argue this one's worth saving. "
        "Original brick fireplace, clerestory windows in the living room, the kind of "
        "open plan that mid-century architects actually designed instead of HGTV'd "
        "into existence.",

        # Meyerland post-Harvey
        "Meyerland house that flooded in Harvey and was rebuilt properly—not just "
        "dried out and flipped. We checked: new foundation, new electrical, new HVAC, "
        "elevated two feet above the old slab. The neighborhood's still recovering, "
        "but the house itself is functionally new construction at half the price.",

        # River Oaks / Southampton
        "Southampton technically, but the kind of Southampton lot that backs up to "
        "actual River Oaks. The house is a 1950s ranch that someone's already gutted "
        "to the studs—you're buying a shell on a great lot. Bring your architect.",

        # Garden Oaks / Oak Forest
        "Double lot in Garden Oaks—actual double lot, two tax IDs, not just a big "
        "yard that could maybe be subdivided. The house is fine: three bed, two bath, "
        "updated enough to live in while you plan what's next. But the lot is the play.",

        "The A-frame that Oak Forest lifers have been watching for years. It hits the "
        "market every decade or so, and each time someone says they're going to restore "
        "it properly—and then doesn't. Vaulted ceilings, original stone fireplace, a "
        "floor plan that doesn't make sense until you live in it.",
    ])

    # Intro paragraph examples
    intro_examples: list[str] = field(default_factory=lambda: [
        "From a Heights Victorian that predates most of the neighborhood to new EaDo "
        "lofts with downtown views, this week's mix actually feels like Houston—diverse, "
        "spread out, and hard to categorize. Montrose delivers the walkability, West U "
        "delivers the schools, and Garden Oaks delivers a double lot that's been "
        "waiting for the right buyer.",

        "The spread this week runs from a $300K Meyerland fixer to a River Oaks-adjacent "
        "lot with an asking price that assumes you'll tear down what's there. Most of "
        "the action is in the $500K-$800K range, where updated bungalows and honest "
        "mid-centuries compete for buyers who missed the market five years ago.",

        "Three weeks of rain meant fewer open houses and more price reductions. If "
        "you've been waiting for negotiating room, this is the week to look. The Heights "
        "has options at every price point, and Montrose finally has something that's "
        "not a skinny lot townhome.",

        "If you've been doom-scrolling through gray paint and LVP flooring, this week's "
        "a palate cleanser. Original hardwoods in Bellaire, transom windows in the "
        "Heights, and a Garden Oaks A-frame that's been teasing the neighborhood for "
        "years. Not everything needs updating—sometimes it just needs someone who gets it.",

        "Three houses this week that are priced like projects but move-in ready if your "
        "standards are flexible. The Meyerland post-Harvey rebuild is functionally new; "
        "the West U ranch needs everything but rewards the work; and the Midtown cottage "
        "is just small, not broken.",

        "The house that Oak Forest neighbors have been watching since the '90s finally "
        "hit the market. We've got that, plus a Museum District fourplex conversion "
        "with more square footage than you'd guess, and a Heights bungalow that's proof "
        "you don't need to gut everything to make it work.",
    ])

    # Things to avoid in descriptions
    avoid_phrases: list[str] = field(default_factory=lambda: [
        # Original
        "won't last long",
        "move-in ready",
        "must see",
        "stunning",
        "gorgeous",
        "beautiful home",
        "perfect for entertaining",
        "great location",
        "close to everything",
        "pride of ownership",
        "motivated seller",
        "priced to sell",
        "turnkey",
        "chef's delight",
        "spa-like bathroom",
        "resort-style",
        "highly sought after",
        # New additions
        "dream home",
        "amazing opportunity",
        "rare find",
        "don't miss out",
        "entertainer's paradise",
        "open concept living",
        "shows like a model",
        "lovingly maintained",
        "charming",
        "exquisite",
        "impeccable",
        "breathtaking",
        "spectacular",
        "one-of-a-kind",
        "luxury living",
    ])

    # Phrases that work (insider vocabulary)
    phrases_that_work: dict[str, list[str]] = field(default_factory=lambda: {
        "architecture": [
            "the kind of [feature] that would cost six figures to reproduce",
            "bones are solid",
            "original [material] that could come back to life",
            "properly permitted",
            "functionally new construction",
            "converted without erasing its history",
            "the weird houses are the ones worth keeping",
        ],
        "neighborhood_context": [
            "the quiet side of [street]",
            "before the neighborhood got loud about being a neighborhood",
            "backs up to actual [upscale area]",
            "walking distance to [specific restaurant/landmark]",
            "[Neighborhood] lifers have been watching this one",
            "survived the townhome rush",
        ],
        "practical": [
            "the lot is the play here",
            "bring your architect",
            "priced for the lot, not the finishes",
            "needs everything, but the bones are there",
            "acknowledges [modern thing] exists",
            "two parking spots included, which is rare",
        ],
        "value_commentary": [
            "what [property type] used to cost before [neighborhood] got expensive",
            "half the price per square foot",
            "rewards the work",
            "the catch is...",
        ],
        "honest_assessments": [
            "it's tiny, but...",
            "the house is fine; the lot is the story",
            "layout's weird in a good way",
            "not broken, just small",
        ],
    })

    # Tone guidelines
    tone_guidelines: str = """
VOICE: Knowledgeable Houston insider
Think Curbed, Brownstoner, or local food critics like Alison Cook and Erica Chen.
Someone who's watched neighborhoods evolve and knows every street in the Inner Loop.

PHILOSOPHY:
"Interesting houses that can become long-lasting homes"
Not about investment returns or flipping potential. About character, quality, and fit.

TONE:
- Conversational insider: Like getting listings texted from a friend who knows Houston
- Observational: Notice details others miss (original materials, practical quirks)
- Practical: Focus on what matters (parking, layout, condition, neighborhood reality)
- Light editorial wit: Occasional commentary without being snarky

STRUCTURE PER LISTING:
**$XXX,XXX — [Address]**
X bed / X bath / X,XXX sqft / [Type] / [Year]

[2-4 sentences highlighting what makes this property interesting. Focus on unique
features, neighborhood context, or honest value assessment. Lead with what's notable.]

[HAR Link]

WHAT TO HIGHLIGHT:
- Neighborhood context (what it's like to live there, nearby landmarks)
- Unique architectural features or history
- Practical considerations (parking, layout, systems, flood history)
- Honest assessment with specific details
- Why this house stands out from the generic listings

WHAT TO AVOID:
- Generic real estate speak (see avoid_phrases list)
- Excessive adjectives without substance
- Claims about how fast it will sell
- Anything that sounds like an agent wrote it
- Investor-focused language (ROI, flip potential, rental income)
"""

    def get_listing_prompt_context(self) -> str:
        """Get context for listing description prompts."""
        examples = "\n\n".join(
            f"Example {i+1}:\n{ex}" for i, ex in enumerate(self.listing_examples[:6])
        )
        avoid = ", ".join(f'"{p}"' for p in self.avoid_phrases[:15])
        return f"""
{self.tone_guidelines}

PHRASES TO AVOID:
{avoid}

EXAMPLE DESCRIPTIONS TO MATCH:

{examples}
"""

    def get_intro_prompt_context(self) -> str:
        """Get context for intro paragraph prompts."""
        examples = "\n\n".join(
            f"Example {i+1}:\n{ex}" for i, ex in enumerate(self.intro_examples)
        )
        return f"""
INTRO STYLE:
- Contextualizes the week's offerings with insider perspective
- Mentions 2-3 neighborhood themes or notable properties
- Sets expectations for what makes this week interesting
- 2-3 sentences max
- Conversational, not promotional—like a friend summarizing what's worth looking at

EXAMPLE INTROS TO MATCH:

{examples}
"""

    def get_avoid_phrases(self) -> list[str]:
        """Get list of phrases to avoid in generated content."""
        return self.avoid_phrases

    def get_phrases_that_work(self) -> dict[str, list[str]]:
        """Get categorized phrases that work well in insider voice."""
        return self.phrases_that_work
