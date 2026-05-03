import { describe, expect, it } from "vitest";
import { buildDraftPrompt } from "../src/drafting/draftPromptBuilder.js";
import type { AssembledIssue } from "../src/issues/issueAssembler.js";
import type { EditorialScore, ListingRecord } from "../src/types/domain.js";

describe("buildDraftPrompt", () => {
  it("includes voice constraints, batch read, listing rationale, and links", () => {
    const listings: ListingRecord[] = [
      {
        id: "lst_1",
        source: "har-email",
        sourceUrl: "https://www.har.com/1",
        address: "1234 Harvard St",
        neighborhood: "Heights",
        status: "selected",
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      }
    ];
    const scores: EditorialScore[] = [
      {
        listingId: "lst_1",
        selected: true,
        score: 5,
        angles: ["rarity"],
        rationale: "Rare lot.",
        createdAt: "2026-05-03T00:00:00.000Z"
      }
    ];
    const issue: AssembledIssue = {
      issueRun: {
        id: "run_1",
        status: "drafting",
        neighborhoods: ["Heights"],
        selectedListingIds: ["lst_1"],
        rejectedListingIds: [],
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      },
      marketSummary: "Strong Heights batch.",
      selectedListings: listings,
      rejectedListings: []
    };

    const prompt = buildDraftPrompt(issue, listings, scores);

    expect(prompt).toContain("no agent puffery");
    expect(prompt).toContain("Strong Heights batch");
    expect(prompt).toContain("Rare lot");
    expect(prompt).toContain("https://www.har.com/1");
  });
});
