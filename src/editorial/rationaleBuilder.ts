import type { ScoringResult } from "./scoringRules.js";
import type { ListingRecord } from "../types/domain.js";

export function buildSelectedRationale(listing: ListingRecord, scoring: ScoringResult): string {
  const address = listing.address ?? "This listing";
  const strongest = scoring.hits.slice(0, 3).map((hit) => hit.note);
  return `${address} is worth a smart buyer's pause because ${strongest.join(" ")}`;
}

export function buildRejectionReason(listing: ListingRecord, scoring: ScoringResult): string {
  const address = listing.address ?? "This listing";
  if (scoring.hits.length === 0) {
    return `${address} does not show a clear rarity, value, character, tradeoff, location, or buyer-usefulness angle.`;
  }

  return `${address} has some signal, but not enough to beat the issue threshold: ${scoring.hits
    .map((hit) => hit.note)
    .join(" ")}`;
}
