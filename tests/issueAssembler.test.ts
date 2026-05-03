import { describe, expect, it } from "vitest";
import { loadConfig } from "../src/config/index.js";
import { assembleIssueRun } from "../src/issues/issueAssembler.js";
import type { EditorialScore, ListingRecord } from "../src/types/domain.js";

const listings: ListingRecord[] = [
  {
    id: "lst_1",
    source: "har-email",
    sourceUrl: "https://www.har.com/1",
    address: "1234 Harvard St",
    neighborhood: "Heights",
    status: "scored",
    createdAt: "2026-05-03T00:00:00.000Z",
    updatedAt: "2026-05-03T00:00:00.000Z"
  },
  {
    id: "lst_2",
    source: "har-email",
    sourceUrl: "https://www.har.com/2",
    address: "999 Suburb Ln",
    neighborhood: "Katy",
    status: "scored",
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
  },
  {
    listingId: "lst_2",
    selected: true,
    score: 5,
    angles: ["buyer_usefulness"],
    rationale: "Practical.",
    createdAt: "2026-05-03T00:00:00.000Z"
  }
];

describe("assembleIssueRun", () => {
  it("includes only configured neighborhoods", () => {
    const issue = assembleIssueRun(loadConfig({ DISPATCH_NEIGHBORHOODS: "Heights" }), listings, scores);

    expect(issue.selectedListings.map((listing) => listing.id)).toEqual(["lst_1"]);
    expect(issue.issueRun.neighborhoods).toEqual(["Heights"]);
    expect(issue.marketSummary).toContain("Heights");
  });
});
