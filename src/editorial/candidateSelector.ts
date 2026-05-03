import type { EditorialScore, ListingRecord } from "../types/domain.js";
import type { EnrichmentMappedFields } from "../enrichment/enrichmentAdapter.js";
import { scoreListing } from "./scoringRules.js";
import { buildRejectionReason, buildSelectedRationale } from "./rationaleBuilder.js";

export interface CandidateSelection {
  selected: EditorialScore[];
  rejected: EditorialScore[];
}

export interface CandidateSelectionOptions {
  minimumScore: number;
  maxSelected: number;
  now?: Date;
}

export function selectCandidates(
  candidates: Array<{ listing: ListingRecord; enrichment?: EnrichmentMappedFields }>,
  options: CandidateSelectionOptions
): CandidateSelection {
  const createdAt = (options.now ?? new Date()).toISOString();
  const scored = candidates.map(({ listing, enrichment }) => {
    const scoring = scoreListing({ listing, enrichment });
    const selected = scoring.score >= options.minimumScore;

    return {
      listingId: listing.id,
      selected,
      score: scoring.score,
      angles: scoring.hits.map((hit) => hit.angle),
      rationale: selected ? buildSelectedRationale(listing, scoring) : "",
      rejectionReason: selected ? undefined : buildRejectionReason(listing, scoring),
      createdAt
    } satisfies EditorialScore;
  });

  const selected = scored
    .filter((score) => score.selected)
    .sort((a, b) => b.score - a.score)
    .slice(0, options.maxSelected);
  const selectedIds = new Set(selected.map((score) => score.listingId));

  return {
    selected,
    rejected: scored.filter((score) => !selectedIds.has(score.listingId))
  };
}
