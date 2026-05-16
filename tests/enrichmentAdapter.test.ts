import { describe, expect, it } from "vitest";
import { ApifyZillowEnrichmentAdapter } from "../src/enrichment/enrichmentAdapter.js";
import type { ApifyClient } from "../src/integrations/apify/client.js";
import type { ListingRecord } from "../src/types/domain.js";

const listing: ListingRecord = {
  id: "lst_1",
  source: "har-email",
  sourceUrl: "https://www.har.com/homedetail/2314-huldy-st-b-houston-tx-77019/8096007?lid=10887164",
  address: "2314 Huldy St B",
  status: "candidate",
  createdAt: "2026-05-03T00:00:00.000Z",
  updatedAt: "2026-05-03T00:00:00.000Z"
};

describe("ApifyZillowEnrichmentAdapter", () => {
  it("runs the configured actor and maps the first result", async () => {
    const apify: ApifyClient = {
      async runActor(actorId, input) {
        expect(actorId).toBe("actor-1");
        expect(input.startUrls?.[0].url).toBe(listing.sourceUrl);
        expect(input.propertyStatus).toBe("FOR_SALE");
        return [{ price: "725000", bedrooms: 3 }];
      }
    };

    const adapter = new ApifyZillowEnrichmentAdapter({ token: "token", zillowActorId: "actor-1" }, apify);
    const result = await adapter.enrich(listing);

    expect(result.mappedFields.price).toBe(725000);
    expect(result.mappedFields.beds).toBe(3);
  });

  it("uses address lookup input for the address-based Zillow details actor", async () => {
    const apify: ApifyClient = {
      async runActor(actorId, input) {
        expect(actorId).toBe("kawsar/affordable-zillow-details-scraper");
        expect(input).toEqual({
          address: ["2314 Huldy St B, Houston, TX 77019"],
          maxItems: 1
        });
        return [{ price: "725000", bedrooms: 3 }];
      }
    };

    const adapter = new ApifyZillowEnrichmentAdapter(
      { token: "token", zillowActorId: "kawsar/affordable-zillow-details-scraper" },
      apify
    );
    const result = await adapter.enrich(listing);

    expect(result.mappedFields.price).toBe(725000);
  });

  it("fails clearly when no actor is configured", async () => {
    const adapter = new ApifyZillowEnrichmentAdapter(
      { token: undefined, zillowActorId: undefined },
      { async runActor() { return []; } }
    );

    await expect(adapter.enrich(listing)).rejects.toThrow("APIFY_ZILLOW_ACTOR_ID");
  });
});
