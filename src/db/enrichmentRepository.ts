import type { DispatchDb } from "./index.js";
import type { EnrichmentSnapshot } from "../types/domain.js";

export class EnrichmentRepository {
  constructor(private readonly db: DispatchDb) {}

  create(snapshot: EnrichmentSnapshot): void {
    this.db
      .prepare(
        `
        INSERT INTO enrichment_snapshots (
          id, listing_id, provider, payload_json, mapped_fields_json, created_at
        ) VALUES (
          @id, @listingId, @provider, @payloadJson, @mappedFieldsJson, @createdAt
        )
      `
      )
      .run({
        id: snapshot.id,
        listingId: snapshot.listingId,
        provider: snapshot.provider,
        payloadJson: JSON.stringify(snapshot.payload),
        mappedFieldsJson: JSON.stringify(snapshot.mappedFields),
        createdAt: snapshot.createdAt
      });
  }

  latestForListing(listingId: string): EnrichmentSnapshot | undefined {
    const row = this.db
      .prepare(
        `
        SELECT id, listing_id as listingId, provider, payload_json as payloadJson,
          mapped_fields_json as mappedFieldsJson, created_at as createdAt
        FROM enrichment_snapshots
        WHERE listing_id = ?
        ORDER BY created_at DESC
        LIMIT 1
      `
      )
      .get(listingId) as
      | {
          id: string;
          listingId: string;
          provider: EnrichmentSnapshot["provider"];
          payloadJson: string;
          mappedFieldsJson: string;
          createdAt: string;
        }
      | undefined;

    return row
      ? {
          id: row.id,
          listingId: row.listingId,
          provider: row.provider,
          payload: JSON.parse(row.payloadJson),
          mappedFields: JSON.parse(row.mappedFieldsJson),
          createdAt: row.createdAt
        }
      : undefined;
  }
}
