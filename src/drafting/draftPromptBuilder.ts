import type { EditorialScore, ListingRecord } from "../types/domain.js";
import type { AssembledIssue } from "../issues/issueAssembler.js";
import { localNeighborhoodLabel } from "../editorial/localNeighborhood.js";

export function buildDraftPrompt(issue: AssembledIssue, listings: ListingRecord[], scores: EditorialScore[]): string {
  const scoreByListing = new Map(scores.map((score) => [score.listingId, score]));
  const listingById = new Map(listings.map((listing) => [listing.id, listing]));
  const issueDate = issue.issueRun.createdAt.slice(0, 10);

  const selected = issue.issueRun.selectedListingIds
    .map((id) => {
      const listing = listingById.get(id);
      const score = scoreByListing.get(id);
      const displayNeighborhood = localNeighborhoodLabel(listing?.neighborhood) ?? "unknown";
      return [
        `- ${listing?.address ?? listing?.sourceUrl ?? id}`,
        `  Source: ${listing?.sourceUrl ?? "unknown"}`,
        `  Display neighborhood: ${displayNeighborhood}`,
        `  Raw HAR neighborhood/subdivision: ${listing?.neighborhood ?? "unknown"}`,
        `  Angle: ${score?.angles.join(", ") || "buyer-relevant tradeoff"}`,
        `  Rationale: ${score?.rationale ?? "No rationale recorded."}`
      ].join("\n");
    })
    .join("\n\n");

  return [
    `Write a Houston Housing Dispatch issue for smart Houston homebuyers and real-estate-curious locals.`,
    `Voice: sharp local filter, taste plus practicality, no agent puffery, no generic listing syndication.`,
    ``,
    `Batch read: ${issue.marketSummary}`,
    `Issue date: ${issueDate}`,
    ``,
    `Selected listings:`,
    selected,
    ``,
    `Draft constraints:`,
    `- Make the reader smarter about Houston housing.`,
    `- Explain the buyer-relevant judgment for each listing.`,
    `- Preserve the listing order provided below. It is already grouped by local neighborhood and sorted low-to-high by price within each neighborhood.`,
    `- Use the Display neighborhood exactly in each listing heading. Do not use HAR subdivision names, development names, or hyper-specific labels as public neighborhood titles.`,
    `- Price per square foot may appear in listing headings only. Do not mention price per square foot in the intro, body paragraphs, comparisons, or closing summary. Talk about value in normal buyer language instead.`,
    `- Write about homes the way thoughtful buyers talk about homes they might love: layout, block, lot, light, renovation quality, daily-life tradeoffs, schools, outdoor space, commute, and resale logic.`,
    `- Do not mention builder names. Builder names rarely mean anything to this reader; translate any builder-related detail into observable build quality, layout, materials, or finish choices instead.`,
    `- Do not include open-house, showing-window, or tour-window information at all. These details age too quickly for the newsletter.`,
    `- Include source links.`,
    `- Stop short of legal, financing, or inspection advice.`
  ].join("\n");
}
