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
  minSelected?: number;
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

    return {
      listing,
      scoring,
      score: scoring.score
    };
  });

  const selectedCandidates = scored
    .filter((candidate) => isSelectable(candidate.scoring, options.minimumScore))
    .sort((a, b) => b.score - a.score)
    .slice(0, options.maxSelected);

  const minSelected = Math.min(options.minSelected ?? 0, options.maxSelected);
  if (selectedCandidates.length < minSelected) {
    const selectedIds = new Set(selectedCandidates.map((candidate) => candidate.listing.id));
    const backups = scored
      .filter((candidate) => !selectedIds.has(candidate.listing.id) && candidate.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, minSelected - selectedCandidates.length);
    selectedCandidates.push(...backups);
  }

  const selectedIds = new Set(selectedCandidates.map((candidate) => candidate.listing.id));

  const selected = selectedCandidates.map(({ listing, scoring }) => ({
      listingId: listing.id,
      selected: true,
      score: scoring.score,
      angles: uniqueAngles(scoring),
      rationale: buildSelectedRationale(listing, scoring),
      createdAt
    } satisfies EditorialScore));

  const rejected = scored
    .filter((candidate) => !selectedIds.has(candidate.listing.id))
    .map(({ listing, scoring }) => ({
      listingId: listing.id,
      selected: false,
      score: scoring.score,
      angles: uniqueAngles(scoring),
      rationale: "",
      rejectionReason: buildRejectionReason(listing, scoring),
      createdAt
    } satisfies EditorialScore));

  return {
    selected,
    rejected
  };
}

function isSelectable(scoring: ReturnType<typeof scoreListing>, minimumScore: number): boolean {
  if (scoring.score < minimumScore) {
    return false;
  }

  const angles = new Set(scoring.hits.map((hit) => hit.angle));
  if (angles.has("rarity") || angles.has("character") || angles.has("tradeoff")) {
    return true;
  }

  return scoring.score >= minimumScore + 0.5 && angles.has("location_hook");
}

function uniqueAngles(scoring: ReturnType<typeof scoreListing>) {
  return [...new Set(scoring.hits.map((hit) => hit.angle))];
}
