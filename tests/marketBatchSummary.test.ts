import { describe, expect, it } from "vitest";
import { buildMarketBatchSummary } from "../src/editorial/marketBatchSummary.js";
import type { EditorialScore, ListingRecord } from "../src/types/domain.js";

describe("buildMarketBatchSummary", () => {
  it("summarizes batches with local-facing neighborhood labels", () => {
    const listings: ListingRecord[] = [
      {
        id: "lst_1",
        source: "har-email",
        sourceUrl: "https://www.har.com/1",
        neighborhood: "Eado Point",
        status: "selected",
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      },
      {
        id: "lst_2",
        source: "har-email",
        sourceUrl: "https://www.har.com/2",
        neighborhood: "Stuart Terrace / Midtown",
        status: "selected",
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      }
    ];
    const scores: EditorialScore[] = [
      { listingId: "lst_1", selected: true, score: 4, angles: ["value_mismatch"], rationale: "", createdAt: "2026-05-03T00:00:00.000Z" },
      { listingId: "lst_2", selected: true, score: 4, angles: ["character"], rationale: "", createdAt: "2026-05-03T00:00:00.000Z" }
    ];

    const summary = buildMarketBatchSummary(listings, scores);

    expect(summary).toContain("EaDo, Midtown");
    expect(summary).not.toContain("Eado Point");
    expect(summary).not.toContain("Stuart Terrace");
  });
});
