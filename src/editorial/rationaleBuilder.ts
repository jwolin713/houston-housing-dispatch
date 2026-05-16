import type { ScoringResult } from "./scoringRules.js";
import type { ListingRecord } from "../types/domain.js";

export function buildSelectedRationale(listing: ListingRecord, scoring: ScoringResult): string {
  const address = listing.address ?? "This listing";
  const strongest = strongestDistinctHits(scoring).map((hit) => hit.note);
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

function strongestDistinctHits(scoring: ScoringResult) {
  const seen = new Set<string>();
  const hits = [];

  for (const hit of scoring.hits) {
    if (!seen.has(hit.angle)) {
      hits.push(hit);
      seen.add(hit.angle);
    }
    if (hits.length === 3) {
      break;
    }
  }

  return hits;
}
