import { requireConfigValue, type AppConfig } from "../../config/index.js";

export interface ApifyActorInput {
  startUrls?: Array<{ url: string }>;
  propertyStatus?: string;
  property_url?: string[];
  zpid?: string[];
  address?: string[];
  maxItems?: number;
  timeoutSecs?: number;
  requestTimeoutSecs?: number;
}

export interface ApifyClient {
  runActor(actorId: string, input: ApifyActorInput): Promise<unknown[]>;
}

type FetchLike = typeof fetch;

export class ApifyApiClient implements ApifyClient {
  constructor(
    private readonly config: AppConfig["apify"],
    private readonly fetchImpl: FetchLike = fetch
  ) {}

  async runActor(actorId: string, input: ApifyActorInput): Promise<unknown[]> {
    const token = requireConfigValue(this.config.token, "APIFY_TOKEN");
    const url = new URL(`https://api.apify.com/v2/acts/${normalizeActorId(actorId)}/run-sync-get-dataset-items`);
    url.searchParams.set("token", token);

    const response = await this.fetchImpl(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input)
    });

    if (!response.ok) {
      throw new Error(`Apify actor run failed with ${response.status}: ${await response.text()}`);
    }

    const payload = await response.json();
    if (!Array.isArray(payload)) {
      throw new Error("Apify actor run did not return dataset items.");
    }

    return payload;
  }
}

function normalizeActorId(actorId: string): string {
  return encodeURIComponent(actorId.replace("/", "~"));
}
