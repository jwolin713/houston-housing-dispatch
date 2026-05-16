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

  it("treats ordinary value plus utility as supporting signal, not enough by itself", () => {
    const score = scoreListing({
      listing: baseListing,
      enrichment: {
        price: 700000,
        squareFeet: 2600,
        lotSquareFeet: 1800,
        beds: 3,
        baths: 2,
        yearBuilt: 2024,
        description: "New construction with modern finishes."
      }
    });

    expect(score.score).toBeLessThan(3);
    expect(score.hits.map((hit) => hit.angle)).toEqual(
      expect.arrayContaining(["value_mismatch", "location_hook", "buyer_usefulness"])
    );
  });

  it("elevates unusually strong value even without old-house character", () => {
    const score = scoreListing({
      listing: baseListing,
      enrichment: {
        price: 470000,
        squareFeet: 2400,
        lotSquareFeet: 1800,
        beds: 3,
        baths: 2,
        yearBuilt: 2020
      }
    });

    expect(score.score).toBeGreaterThanOrEqual(3);
    expect(score.hits.find((hit) => hit.angle === "value_mismatch")?.note).toContain("Unusual value");
  });

  it("recognizes property-specific hooks from enriched descriptions", () => {
    const score = scoreListing({
      listing: baseListing,
      enrichment: {
        price: 750000,
        squareFeet: 2905,
        beds: 3,
        baths: 3.5,
        yearBuilt: 2005,
        description: "Featured in Texas Architect with a rare first floor layout and custom design."
      }
    });

    expect(score.hits.map((hit) => hit.angle)).toEqual(
      expect.arrayContaining(["character", "buyer_usefulness"])
    );
    expect(score.score).toBeGreaterThanOrEqual(3);
  });

  it("recognizes explicit location tradeoffs from descriptions", () => {
    const score = scoreListing({
      listing: baseListing,
      enrichment: {
        price: 435000,
        squareFeet: 2052,
        beds: 3,
        baths: 2.5,
        description: "Life in the Heights often comes with tradeoffs, narrow streets, limited parking, and congestion."
      }
    });

    expect(score.hits.map((hit) => hit.angle)).toContain("tradeoff");
  });
});
