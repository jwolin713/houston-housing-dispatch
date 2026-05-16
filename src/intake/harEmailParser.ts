import type { GmailMessage } from "../integrations/gmail/client.js";

export interface ParsedHarListing {
  sourceUrl: string;
  address?: string;
  neighborhood?: string;
  price?: number;
  beds?: number;
  baths?: number;
  squareFeet?: number;
}

const HAR_URL_PATTERN = /https?:\/\/(?:www\.)?har\.com\/[^\s"'<>]+/gi;
const HAR_HOMEDETAIL_PATTERN = /https?:\/\/(?:www\.)?har\.com\/homedetail\/[^\s"'<>]+/gi;

export function parseHarEmail(message: GmailMessage): ParsedHarListing[] {
  const raw = `${message.subject ?? ""}\n${message.text}\n${message.html ?? ""}`;
  const body = normalizeWhitespace(raw);
  const savedSearchListings = parseSavedSearchDigest(
    normalizeWhitespace(`${message.subject ?? ""}\n${message.text}`),
    unique(((message.html ?? "").match(HAR_HOMEDETAIL_PATTERN) ?? []).map(cleanUrl))
  );
  if (savedSearchListings.length > 0) {
    return savedSearchListings;
  }

  const urls = unique((raw.match(HAR_URL_PATTERN) ?? []).map(cleanUrl));

  return urls.map((sourceUrl) => ({
    sourceUrl,
    address: parseAddressNearUrl(body, sourceUrl),
    neighborhood: parseLabeledText(body, "Neighborhood"),
    price: parseMoney(body),
    beds: parseCountField(body, "Beds?", "bed"),
    baths: parseCountField(body, "Baths?", "bath"),
    squareFeet: parseAreaField(body)
  }));
}

function normalizeWhitespace(value: string): string {
  return value
    .replace(/&zwnj;/gi, "")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function cleanUrl(url: string): string {
  return url.replace(/[).,]+$/, "").replace(/&amp;/g, "&");
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

function parseMoney(body: string): number | undefined {
  const match = body.match(/\$([\d,]+)/);
  return match ? Number(match[1].replace(/,/g, "")) : undefined;
}

function parseCountField(body: string, labelBefore: string, labelAfter: string): number | undefined {
  const labeled = body.match(new RegExp(`${labelBefore}:\\s*(\\d+(?:\\.\\d+)?)`, "i"));
  if (labeled) return Number(labeled[1]);

  const inline = body.match(new RegExp(`\\b(\\d+(?:\\.\\d+)?)\\s*${labelAfter}s?\\b`, "i"));
  return inline ? Number(inline[1]) : undefined;
}

function parseAreaField(body: string): number | undefined {
  const labeled = body.match(/(?:Square Feet|Sqft):\s*([\d,]+)/i);
  if (labeled) return Number(labeled[1].replace(/,/g, ""));

  const inline = body.match(/\b([\d,]+)\s*sqft\b/i);
  return inline ? Number(inline[1].replace(/,/g, "")) : undefined;
}

function parseLabeledText(body: string, label: string): string | undefined {
  const match = body.match(new RegExp(`${label}:\\s*([^|]+?)(?:\\s{2,}|\\sPrice:|\\sBeds?:|\\sBaths?:|$)`, "i"));
  return match?.[1]?.trim();
}

function parseAddressNearUrl(body: string, sourceUrl: string): string | undefined {
  const urlIndex = body.indexOf(sourceUrl);
  const nearby = urlIndex >= 0 ? body.slice(Math.max(0, urlIndex - 160), urlIndex + 160) : body;
  const labeled = nearby.match(/Address:\s*([^|]+?)(?:\sNeighborhood:|\sPrice:|\sBeds?:|\sBaths?:|$)/i);
  if (labeled) return labeled[1].trim();

  const addressLike = nearby.match(/\b\d{2,6}\s+[A-Za-z0-9 .'-]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Rd|Road|Ln|Lane|Ct|Court|Way)\b/i);
  return addressLike?.[0]?.trim();
}

function parseSavedSearchDigest(body: string, listingUrls: string[]): ParsedHarListing[] {
  if (!body.includes("Saved Search Notification") || listingUrls.length === 0) {
    return [];
  }

  const blocks = body
    .split(/\bNew Listing\b/i)
    .slice(1)
    .map((block) => block.split(/\bView Listing\b/i)[0]?.trim())
    .filter(Boolean);

  return blocks.slice(0, listingUrls.length).map((block, index) => ({
    sourceUrl: listingUrls[index],
    address: parseSavedSearchAddress(block),
    neighborhood: parseSavedSearchNeighborhood(block),
    price: parseMoney(block),
    beds: parseCountField(block, "Beds?", "bedroom"),
    baths: parseSavedSearchBaths(block),
    squareFeet: parseAreaField(block)
  }));
}

function parseSavedSearchAddress(block: string): string | undefined {
  const match = block.match(/^(.+?),\s*(?:Houston|West University Place|Bellaire|Southside Place|Bunker Hill Village|Piney Point Village|Hunters Creek Village)\s+TX\s+\d{5}\b/i);
  return match?.[1]?.trim();
}

function parseSavedSearchNeighborhood(block: string): string | undefined {
  return block.match(/\bLocated in\s+(.+?)\s+\d+(?:\.\d+)?\s+bedrooms?\b/i)?.[1]?.trim();
}

function parseSavedSearchBaths(block: string): number | undefined {
  const full = block.match(/\b(\d+)\s+full\b/i);
  const half = block.match(/\b(\d+)\s+half\b/i);
  if (!full && !half) {
    return parseCountField(block, "Baths?", "bath");
  }

  return Number(full?.[1] ?? 0) + Number(half?.[1] ?? 0) * 0.5;
}
