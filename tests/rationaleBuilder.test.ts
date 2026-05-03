import { describe, expect, it } from "vitest";
import { buildRejectionReason, buildSelectedRationale } from "../src/editorial/rationaleBuilder.js";
import type { ListingRecord } from "../src/types/domain.js";

const listing: ListingRecord = {
  id: "lst_1",
  source: "har-email",
  sourceUrl: "https://www.har.com/homedetail/example/1",
  address: "1234 Harvard St",
  status: "enriched",
  createdAt: "2026-05-03T00:00:00.000Z",
  updatedAt: "2026-05-03T00:00:00.000Z"
};

describe("rationale builders", () => {
  it("explains selected listings in buyer-relevant terms", () => {
    const rationale = buildSelectedRationale(listing, {
      score: 3,
      hits: [{ angle: "rarity", points: 2, note: "Rare lot signal." }]
    });

    expect(rationale).toContain("1234 Harvard St");
    expect(rationale).toContain("Rare lot signal");
  });

  it("explains rejected listings without generic phrasing", () => {
    const reason = buildRejectionReason(listing, { score: 0, hits: [] });

    expect(reason).toContain("does not show a clear");
  });
});
