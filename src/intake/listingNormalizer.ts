import type { GmailMessage } from "../integrations/gmail/client.js";
import type { ListingRecord } from "../types/domain.js";
import type { ParsedHarListing } from "./harEmailParser.js";
import { stableId } from "../util/id.js";

export function normalizeListing(parsed: ParsedHarListing, message: GmailMessage, now = new Date()): ListingRecord {
  const timestamp = now.toISOString();

  return {
    id: stableId("lst", parsed.sourceUrl),
    source: "har-email",
    sourceUrl: parsed.sourceUrl,
    sourceMessageId: message.id,
    address: parsed.address,
    neighborhood: parsed.neighborhood,
    price: parsed.price,
    beds: parsed.beds,
    baths: parsed.baths,
    squareFeet: parsed.squareFeet,
    status: "candidate",
    createdAt: timestamp,
    updatedAt: timestamp
  };
}
