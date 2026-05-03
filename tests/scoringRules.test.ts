import { describe, expect, it } from "vitest";
import { scoreListing } from "../src/editorial/scoringRules.js";
import type { ListingRecord } from "../src/types/domain.js";

const baseListing: ListingRecord = {
  id: "lst_1",
  source: "har-email",
  sourceUrl: "https://www.har.com/homedetail/example/1",
  neighborhood: "Heights",
  status: "enriched",
  createdAt: "2026-05-03T00:00:00.000Z",
  updatedAt: "2026-05-03T00:00:00.000Z"
};

describe("scoreListing", () => {
  it("elevates a rare older home with buyer-relevant tradeoffs", () => {
    const score = scoreListing({
      listing: baseListing,
      enrichment: {
        price: 725000,
        squareFeet: 2300,
        lotSquareFeet: 6600,
        beds: 3,
        baths: 2,
        yearBuilt: 1920,
        description: "Historic bungalow sold as-is with renovation potential."
      }
    });

    expect(score.score).toBeGreaterThanOrEqual(6);
    expect(score.hits.map((hit) => hit.angle)).toEqual(
      expect.arrayContaining(["rarity", "character", "tradeoff", "buyer_usefulness"])
    );
  });

  it("keeps generic new listings below a meaningful threshold", () => {
    const score = scoreListing({
      listing: { ...baseListing, neighborhood: "Unknown" },
      enrichment: {
        price: 650000,
        squareFeet: 1600,
        lotSquareFeet: 1800,
        beds: 3,
        baths: 2,
        yearBuilt: 2024,
        description: "New construction with modern finishes."
      }
    });

    expect(score.score).toBeLessThan(3);
  });
});
