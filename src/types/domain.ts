export type ListingSource = "har-email" | "manual";

export type ListingStatus =
  | "candidate"
  | "enrichment_failed"
  | "enriched"
  | "scored"
  | "selected"
  | "rejected";

export type EditorialAngle =
  | "rarity"
  | "value_mismatch"
  | "character"
  | "tradeoff"
  | "location_hook"
  | "buyer_usefulness";

export interface ListingRecord {
  id: string;
  source: ListingSource;
  sourceUrl: string;
  sourceMessageId?: string;
  address?: string;
  neighborhood?: string;
  price?: number;
  beds?: number;
  baths?: number;
  squareFeet?: number;
  lotSquareFeet?: number;
  status: ListingStatus;
  createdAt: string;
  updatedAt: string;
}

export interface EnrichmentSnapshot {
  id: string;
  listingId: string;
  provider: "apify-zillow" | "manual";
  payload: unknown;
  mappedFields: Partial<ListingRecord> & {
    yearBuilt?: number;
    propertyType?: string;
    description?: string;
    photoUrls?: string[];
  };
  createdAt: string;
}

export interface EditorialScore {
  listingId: string;
  selected: boolean;
  score: number;
  angles: EditorialAngle[];
  rationale: string;
  rejectionReason?: string;
  createdAt: string;
}

export interface IssueRun {
  id: string;
  status: "drafting" | "ready_for_review" | "handoff_failed";
  neighborhoods: string[];
  selectedListingIds: string[];
  rejectedListingIds: string[];
  calibrationReportPath?: string;
  spiralArtifactPath?: string;
  draftArtifactPath?: string;
  substackDraftUrl?: string;
  createdAt: string;
  updatedAt: string;
}
