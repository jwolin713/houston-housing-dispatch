import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { applyInitialMigration, openDatabase } from "../src/db/index.js";
import { EnrichmentRepository } from "../src/db/enrichmentRepository.js";
import { ListingRepository } from "../src/db/listingRepository.js";
import type { EnrichmentAdapter } from "../src/enrichment/enrichmentAdapter.js";
import { runEnrichment } from "../src/enrichment/runEnrichment.js";
import type { ListingRecord } from "../src/types/domain.js";

describe("runEnrichment", () => {
  it("stores enrichment snapshots and marks listings enriched", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-enrichment-"));
    const db = openDatabase(join(dir, "dispatch.sqlite"));
    try {
      applyInitialMigration(db);
      const listing: ListingRecord = {
        id: "lst_1",
        source: "har-email",
        sourceUrl: "https://www.har.com/homedetail/example/1",
        status: "candidate",
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      };
      new ListingRepository(db).upsert(listing);

      const adapter: EnrichmentAdapter = {
        async enrich() {
          return { payload: { price: 725000 }, mappedFields: { price: 725000 } };
        }
      };

      const result = await runEnrichment(db, adapter);
      const snapshot = new EnrichmentRepository(db).latestForListing("lst_1");
      const [stored] = new ListingRepository(db).all();

      expect(result).toMatchObject({ attempted: 1, enriched: 1, failed: [] });
      expect(snapshot?.mappedFields.price).toBe(725000);
      expect(stored.status).toBe("enriched");
    } finally {
      db.close();
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("respects enrichment run limits", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-enrichment-limit-"));
    const db = openDatabase(join(dir, "dispatch.sqlite"));
    try {
      applyInitialMigration(db);
      const repo = new ListingRepository(db);
      repo.upsert({
        id: "lst_1",
        source: "har-email",
        sourceUrl: "https://www.har.com/homedetail/example/1",
        status: "candidate",
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      });
      repo.upsert({
        id: "lst_2",
        source: "har-email",
        sourceUrl: "https://www.har.com/homedetail/example/2",
        status: "candidate",
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      });

      const adapter: EnrichmentAdapter = {
        async enrich() {
          return { payload: { price: 725000 }, mappedFields: { price: 725000 } };
        }
      };

      const result = await runEnrichment(db, adapter, { limit: 1 });
      const stored = new ListingRepository(db).all();

      expect(result).toMatchObject({ attempted: 1, enriched: 1, failed: [] });
      expect(stored.filter((listing) => listing.status === "enriched")).toHaveLength(1);
      expect(stored.filter((listing) => listing.status === "candidate")).toHaveLength(1);
    } finally {
      db.close();
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
