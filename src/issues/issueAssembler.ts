import type { AppConfig } from "../config/index.js";
import type { EditorialScore, IssueRun, ListingRecord } from "../types/domain.js";
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
    .filter(isListing);
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
