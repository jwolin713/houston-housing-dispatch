import { describe, expect, it } from "vitest";
import { ApifyApiClient } from "../src/integrations/apify/client.js";

describe("ApifyApiClient", () => {
  it("runs an actor synchronously and returns dataset items", async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    const fetchImpl = async (url: string | URL | Request, init?: RequestInit) => {
      requests.push({ url: String(url), init });
      return new Response(JSON.stringify([{ price: 725000 }]), { status: 200 });
    };

    const client = new ApifyApiClient({ token: "token-123", zillowActorId: "owner/zillow-details" }, fetchImpl);
    const result = await client.runActor("owner/zillow-details", {
      startUrls: [{ url: "https://www.har.com/homedetail/example/1" }]
    });

    expect(result).toEqual([{ price: 725000 }]);
    expect(requests[0].url).toBe(
      "https://api.apify.com/v2/acts/owner~zillow-details/run-sync-get-dataset-items?token=token-123"
    );
    expect(requests[0].init).toMatchObject({
      method: "POST",
      headers: { "content-type": "application/json" }
    });
    expect(JSON.parse(String(requests[0].init?.body))).toEqual({
      startUrls: [{ url: "https://www.har.com/homedetail/example/1" }]
    });
  });

  it("throws a useful error for failed actor runs", async () => {
    const fetchImpl = async () => new Response("invalid input", { status: 400 });
    const client = new ApifyApiClient({ token: "token-123", zillowActorId: "actor" }, fetchImpl);

    await expect(client.runActor("actor", { startUrls: [] })).rejects.toThrow(
      "Apify actor run failed with 400: invalid input"
    );
  });
});
