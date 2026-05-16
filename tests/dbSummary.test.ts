import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { applyInitialMigration, openDatabase } from "../src/db/index.js";
import { ListingRepository } from "../src/db/listingRepository.js";
import { summarizeDatabase } from "../src/db/summary.js";
import type { ListingRecord } from "../src/types/domain.js";

function listing(overrides: Partial<ListingRecord>): ListingRecord {
  return {
    id: overrides.id ?? "lst_default",
    source: "har-email",
    sourceUrl: overrides.sourceUrl ?? `https://www.har.com/homedetail/${overrides.id ?? "default"}`,
    sourceMessageId: overrides.sourceMessageId,
    address: overrides.address,
    neighborhood: overrides.neighborhood,
    price: overrides.price,
    beds: overrides.beds,
    baths: overrides.baths,
    squareFeet: overrides.squareFeet,
    lotSquareFeet: overrides.lotSquareFeet,
    status: overrides.status ?? "candidate",
    createdAt: overrides.createdAt ?? "2026-05-03T00:00:00.000Z",
    updatedAt: overrides.updatedAt ?? "2026-05-03T00:00:00.000Z"
  };
}

describe("summarizeDatabase", () => {
  it("returns listing totals by status and newest listings", () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-summary-"));
    const db = openDatabase(join(dir, "dispatch.sqlite"));
    try {
      applyInitialMigration(db);
      const repo = new ListingRepository(db);
      repo.upsert(
        listing({
          id: "lst_1",
          address: "1234 Harvard St",
          status: "candidate",
          updatedAt: "2026-05-03T10:00:00.000Z"
        })
      );
      repo.upsert(
        listing({
          id: "lst_2",
          address: "2200 Dunlavy St",
          status: "enriched",
          updatedAt: "2026-05-03T11:00:00.000Z"
        })
      );
      repo.upsert(
        listing({
          id: "lst_3",
          status: "candidate",
          updatedAt: "2026-05-03T12:00:00.000Z"
        })
      );

      const summary = summarizeDatabase(db, 2);

      expect(summary.listings.total).toBe(3);
      expect(summary.listings.byStatus).toEqual([
        { status: "candidate", count: 2 },
        { status: "enriched", count: 1 }
      ]);
      expect(summary.listings.latest.map((item) => item.id)).toEqual(["lst_3", "lst_2"]);
      expect(summary.listings.latest[0].address).toBeUndefined();
    } finally {
      db.close();
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
