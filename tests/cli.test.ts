import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createProgram } from "../src/cli.js";
import { loadConfig } from "../src/config/index.js";
import { applyInitialMigration, openDatabase } from "../src/db/index.js";
import { ListingRepository } from "../src/db/listingRepository.js";
import { summarizeDatabase } from "../src/db/summary.js";
import type { GmailClient } from "../src/integrations/gmail/client.js";
import type { NotificationAdapter } from "../src/notifications/notificationAdapter.js";
import type { ListingRecord } from "../src/types/domain.js";

function tempDbPath(prefix: string): { dir: string; dbPath: string } {
  const dir = mkdtempSync(join(tmpdir(), prefix));
  return { dir, dbPath: join(dir, "dispatch.sqlite") };
}

function listing(overrides: Partial<ListingRecord>): ListingRecord {
  return {
    id: overrides.id ?? "lst_default",
    source: "har-email",
    sourceUrl: overrides.sourceUrl ?? `https://www.har.com/homedetail/${overrides.id ?? "default"}`,
    status: overrides.status ?? "candidate",
    createdAt: overrides.createdAt ?? "2026-05-03T00:00:00.000Z",
    updatedAt: overrides.updatedAt ?? "2026-05-03T00:00:00.000Z",
    address: overrides.address
  };
}

describe("createProgram", () => {
  it("runs Gmail intake through the concrete command path", async () => {
    const { dir, dbPath } = tempDbPath("dispatch-cli-intake-");
    const output: string[] = [];
    let gmailClientCreated = false;
    try {
      const program = createProgram({
        loadConfig: () => loadConfig({ DISPATCH_DB_PATH: dbPath, GMAIL_QUERY: "from:(har.com)" }),
        openDatabase,
        applyInitialMigration,
        createGmailClient: () => {
          gmailClientCreated = true;
          return {} as GmailClient;
        },
        runIntake: async () => ({
          messagesScanned: 2,
          listingsParsed: 1,
          listingsStored: 1,
          parseFailures: []
        }),
        runEnrichment: async () => ({ attempted: 0, enriched: 0, failed: [] }),
        sampleGmailMessages: async () => [],
        writeLine: (message) => output.push(message)
      });

      await program.parseAsync(["intake"], { from: "user" });

      expect(gmailClientCreated).toBe(true);
      expect(JSON.parse(output[0])).toEqual({
        messagesScanned: 2,
        listingsParsed: 1,
        listingsStored: 1,
        parseFailures: []
      });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("prints database summary output", async () => {
    const { dir, dbPath } = tempDbPath("dispatch-cli-summary-");
    const db = openDatabase(dbPath);
    const output: string[] = [];
    try {
      applyInitialMigration(db);
      new ListingRepository(db).upsert(
        listing({
          id: "lst_1",
          address: "1234 Harvard St",
          updatedAt: "2026-05-03T10:00:00.000Z"
        })
      );
      db.close();

      const program = createProgram({
        loadConfig: () => loadConfig({ DISPATCH_DB_PATH: dbPath }),
        openDatabase,
        applyInitialMigration,
        summarizeDatabase,
        runEnrichment: async () => ({ attempted: 0, enriched: 0, failed: [] }),
        sampleGmailMessages: async () => [],
        writeLine: (message) => output.push(message)
      });

      await program.parseAsync(["db-summary", "--limit", "1"], { from: "user" });

      const summary = JSON.parse(output[0]);
      expect(summary.listings.total).toBe(1);
      expect(summary.listings.latest[0].address).toBe("1234 Harvard St");
    } finally {
      if (db.open) {
        db.close();
      }
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("prints redacted Gmail samples", async () => {
    const output: string[] = [];
    const program = createProgram({
      loadConfig: () => loadConfig({ GMAIL_QUERY: "from:(har.com)" }),
      createGmailClient: () => ({} as GmailClient),
      runEnrichment: async () => ({ attempted: 0, enriched: 0, failed: [] }),
      sampleGmailMessages: async () => [
        {
          id: "msg-1",
          subject: "HAR alert",
          harUrls: ["https://www.har.com/homedetail/example/1"],
          excerpt: "See https://www.har.com/homedetail/example/1"
        }
      ],
      writeLine: (message) => output.push(message)
    });

    await program.parseAsync(["gmail-sample", "--limit", "1"], { from: "user" });

    expect(JSON.parse(output[0])).toEqual([
        {
          id: "msg-1",
          subject: "HAR alert",
          harUrls: ["https://www.har.com/homedetail/example/1"],
          excerpt: "See https://www.har.com/homedetail/example/1"
        }
    ]);
  });

  it("runs limited enrichment through the command path", async () => {
    const { dir, dbPath } = tempDbPath("dispatch-cli-enrich-");
    const output: string[] = [];
    let observedLimit: number | undefined;
    try {
      const program = createProgram({
        loadConfig: () =>
          loadConfig({
            DISPATCH_DB_PATH: dbPath,
            APIFY_TOKEN: "token",
            APIFY_ZILLOW_ACTOR_ID: "actor"
          }),
        openDatabase,
        applyInitialMigration,
        createApifyClient: () => ({ async runActor() { return []; } }),
        runEnrichment: async (_db, _adapter, options) => {
          observedLimit = options?.limit;
          return { attempted: 1, enriched: 1, failed: [] };
        },
        sampleGmailMessages: async () => [],
        writeLine: (message) => output.push(message)
      });

      await program.parseAsync(["enrich", "--limit", "2"], { from: "user" });

      expect(observedLimit).toBe(2);
      expect(JSON.parse(output[0])).toEqual({ attempted: 1, enriched: 1, failed: [] });
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("runs the full dispatch command path without touching Substack", async () => {
    const { dir, dbPath } = tempDbPath("dispatch-cli-run-");
    const output: string[] = [];
    let notificationCreated = false;
    let observedEnrichmentLimit: number | undefined;
    try {
      const program = createProgram({
        loadConfig: () =>
          loadConfig({
            DISPATCH_DB_PATH: dbPath,
            APIFY_TOKEN: "token",
            APIFY_ZILLOW_ACTOR_ID: "actor"
          }),
        openDatabase,
        applyInitialMigration,
        createGmailClient: () => ({} as GmailClient),
        createApifyClient: () => ({ async runActor() { return []; } }),
        createNotificationAdapter: () => {
          notificationCreated = true;
          return {} as NotificationAdapter;
        },
        runDispatch: async (_config, _db, _gmail, _enrichment, outputDir, _notifier, options) => {
          observedEnrichmentLimit = options?.enrichmentLimit;
          return {
            intake: { messagesScanned: 2, listingsParsed: 1, listingsStored: 1, parseFailures: [] },
            enrichment: { attempted: 1, enriched: 1, failed: [] },
            dryRun: {
              issueRunId: "run_1",
              selected: 1,
              rejected: 0,
              calibrationReportPath: `${outputDir}\\dispatch\\run_1-calibration.md`,
              spiralInputPath: `${outputDir}\\dispatch\\run_1-spiral-input.md`,
              draftPath: `${outputDir}\\dispatch\\run_1-draft.md`
            },
            substackTouched: false
          };
        },
        sampleGmailMessages: async () => [],
        writeLine: (message) => output.push(message)
      });

      await program.parseAsync(["dispatch", "--output", "output", "--enrichment-limit", "20"], { from: "user" });

      expect(notificationCreated).toBe(true);
      expect(observedEnrichmentLimit).toBe(20);
      expect(JSON.parse(output[0]).substackTouched).toBe(false);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
