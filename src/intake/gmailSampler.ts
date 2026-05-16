import type { GmailClient } from "../integrations/gmail/client.js";
import { redact } from "../security/redaction.js";

export interface GmailSample {
  id: string;
  subject?: string;
  from?: string;
  date?: string;
  harUrls: string[];
  excerpt: string;
}

const HAR_URL_PATTERN = /https?:\/\/(?:www\.)?har\.com\/[^\s"'<>]+/gi;

export async function sampleGmailMessages(
  gmail: GmailClient,
  query: string,
  options: { limit: number; excerptLength: number }
): Promise<GmailSample[]> {
  const summaries = await gmail.listMessages(query);
  const samples: GmailSample[] = [];

  for (const summary of summaries.slice(0, options.limit)) {
    const message = await gmail.getMessage(summary.id);
    samples.push({
      id: message.id,
      subject: message.subject,
      from: message.from,
      date: message.date,
      harUrls: unique(`${message.text}\n${message.html ?? ""}`.match(HAR_URL_PATTERN) ?? []).slice(0, 20),
      excerpt: buildExcerpt(message.text || message.html || "", options.excerptLength)
    });
  }

  return samples;
}

function buildExcerpt(value: string, excerptLength: number): string {
  const compact = value.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
  return redact(compact.slice(0, excerptLength));
}

function unique(values: string[]): string[] {
  return [...new Set(values.map((value) => value.replace(/[).,]+$/, "")))];
}
