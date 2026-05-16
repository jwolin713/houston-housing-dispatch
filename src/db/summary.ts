import type { DispatchDb } from "./index.js";

export interface ListingStatusCount {
  status: string;
  count: number;
}

export interface DispatchDbSummary {
  listings: {
    total: number;
    byStatus: ListingStatusCount[];
    latest: Array<{
      id: string;
      address?: string;
      sourceUrl: string;
      status: string;
      updatedAt: string;
    }>;
  };
}

export function summarizeDatabase(db: DispatchDb, latestLimit = 10): DispatchDbSummary {
  const total = (db.prepare("SELECT COUNT(*) as count FROM listings").get() as { count: number }).count;
  const byStatus = db
    .prepare(
      `
      SELECT status, COUNT(*) as count
      FROM listings
      GROUP BY status
      ORDER BY status ASC
    `
    )
    .all() as ListingStatusCount[];
  const latest = db
    .prepare(
      `
      SELECT
        id,
        address,
        source_url as sourceUrl,
        status,
        updated_at as updatedAt
      FROM listings
      ORDER BY updated_at DESC
      LIMIT @latestLimit
    `
    )
    .all({ latestLimit }) as DispatchDbSummary["listings"]["latest"];

  return {
    listings: {
      total,
      byStatus,
      latest: latest.map((listing) => ({
        ...listing,
        address: listing.address ?? undefined
      }))
    }
  };
}
