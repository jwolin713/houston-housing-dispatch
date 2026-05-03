import type { EditorialScore, ListingRecord } from "../types/domain.js";

export function buildMarketBatchSummary(listings: ListingRecord[], selectedScores: EditorialScore[]): string {
  if (selectedScores.length === 0) {
    return "This batch did not produce enough buyer-relevant listings to support a strong read.";
  }

  const neighborhoods = unique(
    selectedScores
      .map((score) => listings.find((listing) => listing.id === score.listingId)?.neighborhood)
      .filter(isString)
  );
  const angles = unique(selectedScores.flatMap((score) => score.angles));

  return [
    `This batch is strongest in ${neighborhoods.length ? neighborhoods.join(", ") : "the monitored neighborhoods"}.`,
    `The recurring signals are ${angles.join(", ") || "buyer-specific tradeoffs"}.`,
    "The issue should explain why these homes are worth attention, not just recap their specs."
  ].join(" ");
}

function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}

function isString(value: string | undefined): value is string {
  return typeof value === "string" && value.length > 0;
}
