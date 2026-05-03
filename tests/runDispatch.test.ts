import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadConfig } from "../src/config/index.js";
import { applyInitialMigration, openDatabase } from "../src/db/index.js";
import type { EnrichmentAdapter } from "../src/enrichment/enrichmentAdapter.js";
import type { GmailClient } from "../src/integrations/gmail/client.js";
import { runDispatch } from "../src/workflows/runDispatch.js";

describe("runDispatch", () => {
  it("runs mocked intake, enrichment, scoring, calibration, and draft artifact handoff", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-full-run-"));
    const db = openDatabase(join(dir, "dispatch.sqlite"));
    try {
      applyInitialMigration(db);
      const gmail: GmailClient = {
        async listMessages() {
          return [{ id: "msg-1" }];
        },
        async getMessage() {
          return {
            id: "msg-1",
            text: "Address: 1234 Harvard St Neighborhood: Heights Price: $650,000 3 beds 2 baths https://www.har.com/homedetail/example/1"
          };
        }
      };
      const enrichment: EnrichmentAdapter = {
        async enrich() {
          return {
            payload: {},
            mappedFields: {
              price: 650000,
              squareFeet: 2400,
              lotSquareFeet: 7000,
              beds: 3,
              baths: 2,
              yearBuilt: 1920
            }
          };
        }
      };

      const result = await runDispatch(loadConfig({ DISPATCH_NEIGHBORHOODS: "Heights" }), db, gmail, enrichment, dir);

      expect(result.intake.listingsStored).toBe(1);
      expect(result.enrichment.enriched).toBe(1);
      expect(result.dryRun.selected).toBe(1);
      expect(result.substackTouched).toBe(false);
    } finally {
      db.close();
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
