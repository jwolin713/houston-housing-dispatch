import type { DispatchDb } from "./index.js";
import type { ListingRecord } from "../types/domain.js";

export class ListingRepository {
  constructor(private readonly db: DispatchDb) {}

  upsert(listing: ListingRecord): void {
    const row = {
      ...listing,
      sourceMessageId: listing.sourceMessageId ?? null,
      address: listing.address ?? null,
      neighborhood: listing.neighborhood ?? null,
      price: listing.price ?? null,
      beds: listing.beds ?? null,
      baths: listing.baths ?? null,
      squareFeet: listing.squareFeet ?? null,
      lotSquareFeet: listing.lotSquareFeet ?? null
    };

    this.db
      .prepare(
        `
        INSERT INTO listings (
          id, source, source_url, source_message_id, address, neighborhood,
          price, beds, baths, square_feet, lot_square_feet, status, created_at, updated_at
        ) VALUES (
          @id, @source, @sourceUrl, @sourceMessageId, @address, @neighborhood,
          @price, @beds, @baths, @squareFeet, @lotSquareFeet, @status, @createdAt, @updatedAt
        )
        ON CONFLICT(source_url) DO UPDATE SET
          source_message_id = excluded.source_message_id,
          address = COALESCE(excluded.address, listings.address),
          neighborhood = COALESCE(excluded.neighborhood, listings.neighborhood),
          price = COALESCE(excluded.price, listings.price),
          beds = COALESCE(excluded.beds, listings.beds),
          baths = COALESCE(excluded.baths, listings.baths),
          square_feet = COALESCE(excluded.square_feet, listings.square_feet),
          lot_square_feet = COALESCE(excluded.lot_square_feet, listings.lot_square_feet),
          status = excluded.status,
          updated_at = excluded.updated_at
      `
      )
      .run(row);
  }

  all(): ListingRecord[] {
    return this.db
      .prepare(
        `
        SELECT
          id,
          source,
          source_url as sourceUrl,
          source_message_id as sourceMessageId,
          address,
          neighborhood,
          price,
          beds,
          baths,
          square_feet as squareFeet,
          lot_square_feet as lotSquareFeet,
          status,
          created_at as createdAt,
          updated_at as updatedAt
        FROM listings
        ORDER BY created_at ASC
      `
      )
      .all() as ListingRecord[];
  }

  candidatesForEnrichment(): ListingRecord[] {
    return this.db
      .prepare(
        `
        SELECT
          id,
          source,
          source_url as sourceUrl,
          source_message_id as sourceMessageId,
          address,
          neighborhood,
          price,
          beds,
          baths,
          square_feet as squareFeet,
          lot_square_feet as lotSquareFeet,
          status,
          created_at as createdAt,
          updated_at as updatedAt
        FROM listings
        WHERE status IN ('candidate', 'enrichment_failed')
        ORDER BY created_at ASC
      `
      )
      .all() as ListingRecord[];
  }

  updateStatus(id: string, status: ListingRecord["status"]): void {
    this.db
      .prepare("UPDATE listings SET status = @status, updated_at = @updatedAt WHERE id = @id")
      .run({ id, status, updatedAt: new Date().toISOString() });
  }
}
