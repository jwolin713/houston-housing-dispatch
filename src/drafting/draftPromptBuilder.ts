import type { EditorialScore, ListingRecord } from "../types/domain.js";
import type { AssembledIssue } from "../issues/issueAssembler.js";

export function buildDraftPrompt(issue: AssembledIssue, listings: ListingRecord[], scores: EditorialScore[]): string {
  const scoreByListing = new Map(scores.map((score) => [score.listingId, score]));
  const listingById = new Map(listings.map((listing) => [listing.id, listing]));

  const selected = issue.issueRun.selectedListingIds
    .map((id) => {
      const listing = listingById.get(id);
      const score = scoreByListing.get(id);
      return [
        `- ${listing?.address ?? listing?.sourceUrl ?? id}`,
        `  Source: ${listing?.sourceUrl ?? "unknown"}`,
        `  Neighborhood: ${listing?.neighborhood ?? "unknown"}`,
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
    ``,
    `Selected listings:`,
    selected,
    ``,
    `Draft constraints:`,
    `- Make the reader smarter about Houston housing.`,
    `- Explain the buyer-relevant judgment for each listing.`,
    `- Include source links.`,
    `- Stop short of legal, financing, or inspection advice.`
  ].join("\n");
}
