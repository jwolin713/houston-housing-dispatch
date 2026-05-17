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
    price: 725000,
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
    price: 400000,
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
  it("includes scored listings without requiring exact broad neighborhood labels", () => {
    const issue = assembleIssueRun(loadConfig({ DISPATCH_NEIGHBORHOODS: "Heights" }), listings, scores);

    expect(issue.selectedListings.map((listing) => listing.id)).toEqual(["lst_1", "lst_2"]);
    expect(issue.issueRun.neighborhoods).toEqual(["Heights"]);
    expect(issue.marketSummary).toContain("Heights, Katy");
  });

  it("orders selected listings by local neighborhood and price within neighborhood", () => {
    const unorderedListings: ListingRecord[] = [
      { ...listings[0], id: "lst_heights_high", neighborhood: "Heights", price: 900000 },
      { ...listings[0], id: "lst_eado_high", neighborhood: "Eado Point", price: 470000 },
      { ...listings[0], id: "lst_heights_low", neighborhood: "Twenty 03 Street Manors Rep 01", price: 435000 },
      { ...listings[0], id: "lst_eado_low", neighborhood: "Eado Place", price: 375900 }
    ];
    const unorderedScores: EditorialScore[] = unorderedListings.map((listing) => ({
      listingId: listing.id,
      selected: true,
      score: 5,
      angles: ["value_mismatch"],
      rationale: "Interesting.",
      createdAt: "2026-05-03T00:00:00.000Z"
    }));

    const issue = assembleIssueRun(loadConfig({ DISPATCH_NEIGHBORHOODS: "Heights,EaDo" }), unorderedListings, unorderedScores);

    expect(issue.issueRun.selectedListingIds).toEqual([
      "lst_eado_low",
      "lst_eado_high",
      "lst_heights_high",
      "lst_heights_low"
    ]);
  });
});
