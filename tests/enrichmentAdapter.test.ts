import { describe, expect, it } from "vitest";
import { ApifyZillowEnrichmentAdapter } from "../src/enrichment/enrichmentAdapter.js";
import type { ApifyClient } from "../src/integrations/apify/client.js";
import type { ListingRecord } from "../src/types/domain.js";

const listing: ListingRecord = {
  id: "lst_1",
  source: "har-email",
  sourceUrl: "https://www.har.com/homedetail/example/1",
  status: "candidate",
  createdAt: "2026-05-03T00:00:00.000Z",
  updatedAt: "2026-05-03T00:00:00.000Z"
};

describe("ApifyZillowEnrichmentAdapter", () => {
  it("runs the configured actor and maps the first result", async () => {
    const apify: ApifyClient = {
      async runActor(actorId, input) {
        expect(actorId).toBe("actor-1");
        expect(input.startUrls[0].url).toBe(listing.sourceUrl);
        return [{ price: "725000", bedrooms: 3 }];
      }
    };

    const adapter = new ApifyZillowEnrichmentAdapter({ token: "token", zillowActorId: "actor-1" }, apify);
    const result = await adapter.enrich(listing);

    expect(result.mappedFields.price).toBe(725000);
    expect(result.mappedFields.beds).toBe(3);
  });

  it("fails clearly when no actor is configured", async () => {
    const adapter = new ApifyZillowEnrichmentAdapter(
      { token: undefined, zillowActorId: undefined },
      { async runActor() { return []; } }
    );

    await expect(adapter.enrich(listing)).rejects.toThrow("APIFY_ZILLOW_ACTOR_ID");
  });
});
