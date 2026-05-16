import { describe, expect, it } from "vitest";
import { selectCandidates } from "../src/editorial/candidateSelector.js";
import type { ListingRecord } from "../src/types/domain.js";

function listing(id: string, neighborhood = "Heights"): ListingRecord {
  return {
    id,
    source: "har-email",
    sourceUrl: `https://www.har.com/homedetail/example/${id}`,
    neighborhood,
    address: `${id} Harvard St`,
    status: "enriched",
    createdAt: "2026-05-03T00:00:00.000Z",
    updatedAt: "2026-05-03T00:00:00.000Z"
  };
}

describe("selectCandidates", () => {
  it("returns selected and rejected candidate rationale", () => {
    const result = selectCandidates(
      [
        {
          listing: listing("lst_1"),
          enrichment: {
            price: 650000,
            squareFeet: 2400,
            lotSquareFeet: 7000,
            beds: 3,
            baths: 2,
            yearBuilt: 1920
          }
        },
        {
          listing: listing("lst_2", "Unknown"),
          enrichment: {
            price: 650000,
            squareFeet: 1500,
            lotSquareFeet: 1600,
            beds: 3,
            baths: 2,
            yearBuilt: 2024
          }
        }
      ],
      { minimumScore: 3, maxSelected: 10, now: new Date("2026-05-03T00:00:00.000Z") }
    );

    expect(result.selected).toHaveLength(1);
    expect(result.selected[0].listingId).toBe("lst_1");
    expect(result.selected[0].rationale).toContain("worth a smart buyer's pause");
    expect(result.rejected).toHaveLength(1);
    expect(result.rejected[0].rejectionReason).toContain("does not show a clear");
  });

  it("marks above-threshold listings outside the selection cap as rejected", () => {
    const result = selectCandidates(
      [
        {
          listing: listing("lst_1"),
          enrichment: { price: 650000, squareFeet: 2400, lotSquareFeet: 7000, beds: 3, baths: 2 }
        },
        {
          listing: listing("lst_2"),
          enrichment: { price: 650000, squareFeet: 2400, lotSquareFeet: 7000, beds: 3, baths: 2 }
        }
      ],
      { minimumScore: 3, maxSelected: 1, now: new Date("2026-05-03T00:00:00.000Z") }
    );

    expect(result.selected).toHaveLength(1);
    expect(result.rejected).toHaveLength(1);
    expect(result.rejected[0].selected).toBe(false);
    expect(result.rejected[0].rejectionReason).toContain("not enough to beat the issue threshold");
  });

  it("does not select value-only listings without a stronger editorial hook", () => {
    const result = selectCandidates(
      [
        {
          listing: listing("lst_1", "Unknown"),
          enrichment: {
            price: 470000,
            squareFeet: 2400,
            beds: 3,
            baths: 2,
            yearBuilt: 2024,
            description: "New construction with modern finishes."
          }
        }
      ],
      { minimumScore: 3, maxSelected: 10, now: new Date("2026-05-03T00:00:00.000Z") }
    );

    expect(result.selected).toHaveLength(0);
    expect(result.rejected[0].score).toBeGreaterThanOrEqual(3);
    expect(result.rejected[0].selected).toBe(false);
  });

  it("selects strong value when it also has a location hook", () => {
    const result = selectCandidates(
      [
        {
          listing: listing("lst_1", "Studemont Heights"),
          enrichment: {
            price: 470000,
            squareFeet: 2400,
            beds: 3,
            baths: 2,
            yearBuilt: 2024
          }
        }
      ],
      { minimumScore: 3, maxSelected: 10, now: new Date("2026-05-03T00:00:00.000Z") }
    );

    expect(result.selected).toHaveLength(1);
  });

  it("fills to the minimum selected count with the strongest backup candidates", () => {
    const result = selectCandidates(
      [
        {
          listing: listing("lst_1", "Unknown"),
          enrichment: { price: 470000, squareFeet: 2400, beds: 3, baths: 2, yearBuilt: 2024 }
        },
        {
          listing: listing("lst_2", "Unknown"),
          enrichment: { price: 800000, squareFeet: 2400, beds: 3, baths: 2, yearBuilt: 2024 }
        },
        {
          listing: listing("lst_3", "Unknown"),
          enrichment: { price: 1200000, squareFeet: 2400, beds: 1, baths: 1, yearBuilt: 2024 }
        }
      ],
      { minimumScore: 3, minSelected: 2, maxSelected: 10, now: new Date("2026-05-03T00:00:00.000Z") }
    );

    expect(result.selected.map((score) => score.listingId)).toEqual(["lst_1", "lst_2"]);
    expect(result.rejected.map((score) => score.listingId)).toEqual(["lst_3"]);
  });

  it("never fills beyond the maximum selected count", () => {
    const result = selectCandidates(
      [
        {
          listing: listing("lst_1", "Unknown"),
          enrichment: { price: 470000, squareFeet: 2400, beds: 3, baths: 2, yearBuilt: 2024 }
        },
        {
          listing: listing("lst_2", "Unknown"),
          enrichment: { price: 800000, squareFeet: 2400, beds: 3, baths: 2, yearBuilt: 2024 }
        }
      ],
      { minimumScore: 3, minSelected: 5, maxSelected: 1, now: new Date("2026-05-03T00:00:00.000Z") }
    );

    expect(result.selected).toHaveLength(1);
  });
});
