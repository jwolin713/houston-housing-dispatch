import { describe, expect, it } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadConfig } from "../src/config/index.js";
import { applyInitialMigration, openDatabase } from "../src/db/index.js";
import { ListingRepository } from "../src/db/listingRepository.js";
import type { GmailClient } from "../src/integrations/gmail/client.js";
import { runIntake } from "../src/intake/runIntake.js";

describe("runIntake", () => {
  it("stores normalized listings from a mocked Gmail client", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-intake-"));
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
            text: "Address: 1234 Harvard St Price: $725,000 3 beds 2 baths https://www.har.com/homedetail/example/1"
          };
        }
      };

      const result = await runIntake(loadConfig({}), db, gmail);
      const listings = new ListingRepository(db).all();

      expect(result).toMatchObject({ messagesScanned: 1, listingsParsed: 1, listingsStored: 1 });
      expect(listings[0].sourceUrl).toBe("https://www.har.com/homedetail/example/1");
      expect(listings[0].address).toBe("1234 Harvard St");
    } finally {
      db.close();
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
