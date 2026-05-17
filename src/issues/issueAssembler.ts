import type { AppConfig } from "../config/index.js";
import type { EditorialScore, IssueRun, ListingRecord } from "../types/domain.js";
import { localNeighborhoodLabel } from "../editorial/localNeighborhood.js";
import { buildMarketBatchSummary } from "../editorial/marketBatchSummary.js";
import { newId } from "../util/id.js";

export interface AssembledIssue {
  issueRun: IssueRun;
  marketSummary: string;
  selectedListings: ListingRecord[];
  rejectedListings: ListingRecord[];
}

export function assembleIssueRun(
  config: AppConfig,
  listings: ListingRecord[],
  scores: EditorialScore[],
  now = new Date()
): AssembledIssue {
  const scoredIds = new Set(scores.map((score) => score.listingId));
  const scopedListings = listings.filter((listing) => scoredIds.has(listing.id));
  const scopedIds = new Set(scopedListings.map((listing) => listing.id));
  const selectedScores = scores.filter((score) => score.selected && scopedIds.has(score.listingId));
  const rejectedScores = scores.filter((score) => !score.selected && scopedIds.has(score.listingId));
  const selectedListings = selectedScores
    .map((score) => scopedListings.find((listing) => listing.id === score.listingId))
    .filter(isListing)
    .sort(compareListingsForNewsletter);
  const rejectedListings = rejectedScores
    .map((score) => scopedListings.find((listing) => listing.id === score.listingId))
    .filter(isListing);

  if (scopedListings.length === 0) {
    throw new Error("No scored candidates exist for issue assembly.");
  }

  const timestamp = now.toISOString();
  const issueRun: IssueRun = {
    id: newId("run"),
    status: "drafting",
    neighborhoods: config.neighborhoods,
    selectedListingIds: selectedListings.map((listing) => listing.id),
    rejectedListingIds: rejectedListings.map((listing) => listing.id),
    createdAt: timestamp,
    updatedAt: timestamp
  };

  return {
    issueRun,
    marketSummary: buildMarketBatchSummary(scopedListings, selectedScores),
    selectedListings,
    rejectedListings
  };
}

function isListing(value: ListingRecord | undefined): value is ListingRecord {
  return Boolean(value);
}

function compareListingsForNewsletter(a: ListingRecord, b: ListingRecord): number {
  const neighborhoodCompare = (localNeighborhoodLabel(a.neighborhood) ?? "").localeCompare(
    localNeighborhoodLabel(b.neighborhood) ?? "",
    "en",
    { sensitivity: "base" }
  );
  if (neighborhoodCompare !== 0) {
    return neighborhoodCompare;
  }

  const priceCompare = priceSortValue(a) - priceSortValue(b);
  if (priceCompare !== 0) {
    return priceCompare;
  }

  return (a.address ?? a.sourceUrl).localeCompare(b.address ?? b.sourceUrl, "en", { sensitivity: "base" });
}

function priceSortValue(listing: ListingRecord): number {
  return listing.price ?? Number.POSITIVE_INFINITY;
}
