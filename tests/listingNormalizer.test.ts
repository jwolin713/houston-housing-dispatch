import { describe, expect, it } from "vitest";
import { normalizeListing } from "../src/intake/listingNormalizer.js";

describe("normalizeListing", () => {
  it("creates stable listing records from parsed HAR listings", () => {
    const listing = normalizeListing(
      {
        sourceUrl: "https://www.har.com/homedetail/example/1",
        address: "1234 Harvard St",
        price: 725000
      },
      { id: "msg-1", text: "body" },
      new Date("2026-05-03T12:00:00.000Z")
    );

    expect(listing.id).toMatch(/^lst_/);
    expect(listing.source).toBe("har-email");
    expect(listing.sourceMessageId).toBe("msg-1");
    expect(listing.status).toBe("candidate");
    expect(listing.createdAt).toBe("2026-05-03T12:00:00.000Z");
  });
});
