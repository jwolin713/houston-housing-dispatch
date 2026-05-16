import type { AppConfig } from "../config/index.js";
import type { ListingRecord } from "../types/domain.js";
import type { ApifyClient } from "../integrations/apify/client.js";
import { mapZillowDetails } from "./zillowDetailsMapper.js";
import { newId } from "../util/id.js";

export type EnrichmentMappedFields = Partial<ReturnType<typeof mapZillowDetails>>;

export interface EnrichmentAdapter {
  enrich(listing: ListingRecord): Promise<{
    payload: unknown;
    mappedFields: EnrichmentMappedFields;
  }>;
}

export class ApifyZillowEnrichmentAdapter implements EnrichmentAdapter {
  constructor(
    private readonly config: AppConfig["apify"],
    private readonly apify: ApifyClient
  ) {}

  async enrich(listing: ListingRecord) {
    const actorId = this.config.zillowActorId;
    if (!actorId) {
      throw new Error("Missing required configuration: APIFY_ZILLOW_ACTOR_ID");
    }

    const [payload] = await this.apify.runActor(actorId, buildActorInput(actorId, listing));

    if (!payload) {
      throw new Error(`No enrichment result returned for listing ${listing.id}`);
    }

    return {
      payload,
      mappedFields: mapZillowDetails(payload)
    };
  }
}

export function createEnrichmentSnapshot(listing: ListingRecord, enrichment: Awaited<ReturnType<EnrichmentAdapter["enrich"]>>) {
  return {
    id: newId("enr"),
    listingId: listing.id,
    provider: "apify-zillow" as const,
    payload: enrichment.payload,
    mappedFields: enrichment.mappedFields,
    createdAt: new Date().toISOString()
  };
}

function buildActorInput(actorId: string, listing: ListingRecord) {
  if (actorId.toLowerCase() === "kawsar/affordable-zillow-details-scraper") {
    return {
      address: [zillowLookupAddress(listing)],
      maxItems: 1
    };
  }

  return {
    propertyStatus: "FOR_SALE",
    startUrls: [{ url: listing.sourceUrl }]
  };
}

function zillowLookupAddress(listing: ListingRecord): string {
  const location = locationFromHarUrl(listing.sourceUrl);
  if (listing.address && location) {
    return `${listing.address}, ${location}`;
  }
  if (listing.address) {
    return listing.address;
  }
  return listing.sourceUrl;
}

function locationFromHarUrl(sourceUrl: string): string | undefined {
  const slug = sourceUrl.match(/\/homedetail\/([^/?#]+)/)?.[1];
  const match = slug?.match(
    /-(houston|west-university-place|bellaire|southside-place|bunker-hill-village|piney-point-village|hunters-creek-village)-tx-(\d{5})(?:-|$)/i
  );
  if (!match) {
    return undefined;
  }

  const city = match[1]
    .split("-")
    .map((part) => part[0].toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
  return `${city}, TX ${match[2]}`;
}
