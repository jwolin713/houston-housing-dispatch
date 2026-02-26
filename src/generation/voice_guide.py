"""Editorial voice guide for the Houston Housing Dispatch newsletter."""

from dataclasses import dataclass, field


@dataclass
class VoiceGuide:
    """
    Editorial voice guide with examples for AI-powered content generation.

    Based on analysis of existing Houston Housing Dispatch newsletters:
    - Conversational insider tone
    - Observational and specific
    - Practical focus (parking, layout, condition)
    - Light editorial wit
    """

    # Listing description examples (good style to match)
    listing_examples: list[str] = field(default_factory=lambda: [
        "A 1920 bungalow that's been fully gutted and rebuilt—keeping the character but "
        "adding the systems a century-old house needs. The private driveway for two cars "
        "is genuinely rare on these tight Heights streets.",

        "Clean mid-century lines on a corner lot in Oak Forest. The original terrazzo "
        "floors are intact, and whoever designed this carport actually thought about "
        "Houston summers. Three beds plus a converted garage that could go either way.",

        "West U traditional that skipped the gray-paint-and-subway-tile refresh. The "
        "layout flows better than most from this era—kitchen open to the family room "
        "without feeling like an afterthought. Backyard has room for a pool if that's "
        "your move.",

        "Montrose townhome with more garage space than most single-family homes in the "
        "neighborhood. Built in 2019, so you're getting proper insulation and hurricane "
        "windows without the new-construction premium. Walking distance to Underbelly.",

        "A 1950s ranch in Meyerland with the bones for a proper renovation. Original "
        "hardwoods throughout, mature oaks in the back, and enough square footage to "
        "add a primary suite without eating the whole yard. Priced for the lot, not "
        "the finishes.",

        "River Oaks adjacent, technically Afton Oaks, but you'd never know it driving "
        "by. French-Mediterranean hybrid that looks like it was transported from another "
        "era. The pool house alone is bigger than most starter homes.",

        "Garden Oaks bungalow with the double lot that old-timers talk about. Previous "
        "owner added a detached studio that's properly permitted—could be an office, "
        "guest quarters, or rental income. Main house needs updating but nothing structural.",

        "New construction in EaDo that actually looks like Houston, not a transplant "
        "from Austin or Nashville. Rooftop deck with downtown views, and the builder "
        "included the garage door motor this time.",
    ])

    # Intro paragraph examples
    intro_examples: list[str] = field(default_factory=lambda: [
        "Clean lines from Montrose to Meyerland, plus a few homes that skipped the "
        "gray-box memo. The Heights delivers two traditional builds worth a look, and "
        "River Oaks has a French-Mediterranean hybrid that feels lifted from another era.",

        "This week's mix runs from a $300K fixer in Garden Oaks to a River Oaks estate "
        "that'll make your tax bill hurt. Most of the action is in the middle though—"
        "updated Heights bungalows and Montrose townhomes priced where they might "
        "actually move.",

        "New construction from EaDo to Katy, plus some mid-century finds for the buyers "
        "who'd rather renovate than pay the builder premium. The Heights has a rare "
        "double lot, and West U finally has something under a million.",

        "Rain-delayed open houses meant more listings sitting longer than usual. Good "
        "news for buyers—there's actual negotiating room this week. Montrose, Heights, "
        "and a few suburban finds that punch above their price point.",
    ])

    # Things to avoid in descriptions
    avoid_phrases: list[str] = field(default_factory=lambda: [
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
    ])

    # Tone guidelines
    tone_guidelines: str = """
    TONE:
    - Conversational insider: Write like a knowledgeable friend, not a salesperson
    - Observational: Notice interesting details others might miss
    - Practical: Focus on what matters to buyers (parking, layout, condition)
    - Light editorial: Occasional wit without being snarky

    STRUCTURE PER LISTING:
    **$XXX,XXX — [Address]**
    X bed / X bath / X,XXX sqft / [Type] / [Year]

    [2-3 sentences highlighting what makes this property interesting. Focus on unique
    features, neighborhood context, or value proposition. Avoid generic descriptions.]

    [HAR Link]

    WHAT TO HIGHLIGHT:
    - Unique architectural features or history
    - Practical considerations (parking, layout, systems)
    - Neighborhood context and value proposition
    - Honest assessment without being negative
    - Specific details that show you've actually looked at the listing

    WHAT TO AVOID:
    - Generic real estate speak
    - Excessive adjectives
    - Claims about how fast it will sell
    - Phrases like "stunning," "gorgeous," "must see"
    - Anything that sounds like an agent wrote it
    """

    def get_listing_prompt_context(self) -> str:
        """Get context for listing description prompts."""
        examples = "\n\n".join(
            f"Example {i+1}:\n{ex}" for i, ex in enumerate(self.listing_examples[:4])
        )
        return f"""
{self.tone_guidelines}

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
- Contextualizes the week's offerings
- Mentions 2-3 neighborhood themes
- Sets expectations for what's included
- 2-3 sentences max
- Conversational, not promotional

EXAMPLE INTROS TO MATCH:

{examples}
"""
