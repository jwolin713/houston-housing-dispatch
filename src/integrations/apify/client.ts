import { requireConfigValue, type AppConfig } from "../../config/index.js";

export interface ApifyActorInput {
  startUrls: Array<{ url: string }>;
}

export interface ApifyClient {
  runActor(actorId: string, input: ApifyActorInput): Promise<unknown[]>;
}

export class ApifyApiClient implements ApifyClient {
  constructor(private readonly config: AppConfig["apify"]) {}

  async runActor(_actorId: string, _input: ApifyActorInput): Promise<unknown[]> {
    requireConfigValue(this.config.token, "APIFY_TOKEN");
    throw new Error("Apify API transport is not implemented yet; use a concrete adapter during integration.");
  }
}
