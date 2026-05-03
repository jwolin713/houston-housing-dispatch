import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadConfig } from "../src/config/index.js";
import { applyInitialMigration, openDatabase } from "../src/db/index.js";
import { EnrichmentRepository } from "../src/db/enrichmentRepository.js";
import { IssueRunRepository } from "../src/db/issueRunRepository.js";
import { ListingRepository } from "../src/db/listingRepository.js";
import { createEnrichmentSnapshot } from "../src/enrichment/enrichmentAdapter.js";
import { runDryDispatch } from "../src/workflows/dryRun.js";
import type { ListingRecord } from "../src/types/domain.js";

describe("runDryDispatch", () => {
  it("creates calibration and draft artifacts without touching Substack", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-dry-run-"));
    const db = openDatabase(join(dir, "dispatch.sqlite"));
    try {
      applyInitialMigration(db);
      const listing: ListingRecord = {
        id: "lst_1",
        source: "har-email",
        sourceUrl: "https://www.har.com/1",
        address: "1234 Harvard St",
        neighborhood: "Heights",
        status: "enriched",
        createdAt: "2026-05-03T00:00:00.000Z",
        updatedAt: "2026-05-03T00:00:00.000Z"
      };
      new ListingRepository(db).upsert(listing);
      new EnrichmentRepository(db).create(
        createEnrichmentSnapshot(listing, {
          payload: {},
          mappedFields: { price: 650000, squareFeet: 2400, lotSquareFeet: 7000, yearBuilt: 1920 }
        })
      );

      const result = await runDryDispatch(loadConfig({ DISPATCH_NEIGHBORHOODS: "Heights" }), db, dir);
      const issueRun = new IssueRunRepository(db).latest();

      expect(result.selected).toBe(1);
      expect(result.calibrationReportPath).toContain("calibration");
      expect(result.draftPath).toContain("draft");
      expect(issueRun?.status).toBe("ready_for_review");
      expect(issueRun?.draftArtifactPath).toBe(result.draftPath);
    } finally {
      db.close();
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
