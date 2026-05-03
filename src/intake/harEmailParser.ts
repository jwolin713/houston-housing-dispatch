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

export function parseHarEmail(message: GmailMessage): ParsedHarListing[] {
  const body = normalizeWhitespace(`${message.subject ?? ""}\n${message.text}\n${message.html ?? ""}`);
  const urls = unique((body.match(HAR_URL_PATTERN) ?? []).map(cleanUrl));

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
  return value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function cleanUrl(url: string): string {
  return url.replace(/[).,]+$/, "");
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
