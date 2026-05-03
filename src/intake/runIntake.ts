import type { AppConfig } from "../config/index.js";
import type { DispatchDb } from "../db/index.js";
import { ListingRepository } from "../db/listingRepository.js";
import type { GmailClient } from "../integrations/gmail/client.js";
import { parseHarEmail } from "./harEmailParser.js";
import { normalizeListing } from "./listingNormalizer.js";

export interface IntakeResult {
  messagesScanned: number;
  listingsParsed: number;
  listingsStored: number;
  parseFailures: Array<{ messageId: string; error: string }>;
}

export async function runIntake(config: AppConfig, db: DispatchDb, gmail: GmailClient): Promise<IntakeResult> {
  const repo = new ListingRepository(db);
  const messages = await gmail.listMessages(config.gmail.query);
  const result: IntakeResult = {
    messagesScanned: messages.length,
    listingsParsed: 0,
    listingsStored: 0,
    parseFailures: []
  };

  for (const summary of messages) {
    try {
      const message = await gmail.getMessage(summary.id);
      const parsedListings = parseHarEmail(message);
      result.listingsParsed += parsedListings.length;

      for (const parsed of parsedListings) {
        repo.upsert(normalizeListing(parsed, message));
        result.listingsStored += 1;
      }
    } catch (error) {
      result.parseFailures.push({
        messageId: summary.id,
        error: error instanceof Error ? error.message : String(error)
      });
    }
  }

  return result;
}
