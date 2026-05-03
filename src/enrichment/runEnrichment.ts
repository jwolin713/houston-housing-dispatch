import type { DispatchDb } from "../db/index.js";
import { EnrichmentRepository } from "../db/enrichmentRepository.js";
import { ListingRepository } from "../db/listingRepository.js";
import type { EnrichmentAdapter } from "./enrichmentAdapter.js";
import { createEnrichmentSnapshot } from "./enrichmentAdapter.js";

export interface EnrichmentRunResult {
  attempted: number;
  enriched: number;
  failed: Array<{ listingId: string; error: string }>;
}

export async function runEnrichment(db: DispatchDb, adapter: EnrichmentAdapter): Promise<EnrichmentRunResult> {
  const listings = new ListingRepository(db);
  const enrichments = new EnrichmentRepository(db);
  const candidates = listings.candidatesForEnrichment();
  const result: EnrichmentRunResult = { attempted: candidates.length, enriched: 0, failed: [] };

  for (const listing of candidates) {
    try {
      const enrichment = await adapter.enrich(listing);
      enrichments.create(createEnrichmentSnapshot(listing, enrichment));
      listings.updateStatus(listing.id, "enriched");
      result.enriched += 1;
    } catch (error) {
      listings.updateStatus(listing.id, "enrichment_failed");
      result.failed.push({
        listingId: listing.id,
        error: error instanceof Error ? error.message : String(error)
      });
    }
  }

  return result;
}
