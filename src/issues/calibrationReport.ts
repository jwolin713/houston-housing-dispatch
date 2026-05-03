import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { EditorialScore, ListingRecord } from "../types/domain.js";
import type { AssembledIssue } from "./issueAssembler.js";

export function renderCalibrationReport(
  issue: AssembledIssue,
  scores: EditorialScore[],
  listings: ListingRecord[]
): string {
  const scoreByListing = new Map(scores.map((score) => [score.listingId, score]));
  const listingById = new Map(listings.map((listing) => [listing.id, listing]));

  return [
    `# Houston Housing Dispatch Calibration`,
    ``,
    `Issue run: ${issue.issueRun.id}`,
    `Neighborhoods: ${issue.issueRun.neighborhoods.join(", ")}`,
    ``,
    `## Batch Read`,
    ``,
    issue.marketSummary,
    ``,
    `## Selected Listings`,
    ``,
    ...issue.issueRun.selectedListingIds.map((id) => renderListing(id, listingById, scoreByListing, "selected")),
    ``,
    `## Rejected Listings`,
    ``,
    ...issue.issueRun.rejectedListingIds.map((id) => renderListing(id, listingById, scoreByListing, "rejected"))
  ].join("\n");
}

export function writeCalibrationReport(path: string, content: string): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content, "utf8");
}

function renderListing(
  id: string,
  listingById: Map<string, ListingRecord>,
  scoreByListing: Map<string, EditorialScore>,
  mode: "selected" | "rejected"
): string {
  const listing = listingById.get(id);
  const score = scoreByListing.get(id);
  const title = listing?.address ?? listing?.sourceUrl ?? id;
  const rationale = mode === "selected" ? score?.rationale : score?.rejectionReason;

  return [
    `- **${title}**`,
    `  - Source: ${listing?.sourceUrl ?? "unknown"}`,
    `  - Score: ${score?.score ?? "n/a"}`,
    `  - Angles: ${score?.angles.join(", ") || "none"}`,
    `  - Rationale: ${rationale ?? "No rationale recorded."}`,
    ``
  ].join("\n");
}
