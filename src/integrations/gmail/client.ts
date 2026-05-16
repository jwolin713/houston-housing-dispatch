import { requireConfigValue, type AppConfig } from "../../config/index.js";
import { google } from "googleapis";

export interface GmailMessageSummary {
  id: string;
  threadId?: string;
}

export interface GmailMessage {
  id: string;
  subject?: string;
  from?: string;
  date?: string;
  text: string;
  html?: string;
}

export interface GmailClient {
  listMessages(query: string): Promise<GmailMessageSummary[]>;
  getMessage(id: string): Promise<GmailMessage>;
}

export interface GmailApiMessagePart {
  mimeType?: string | null;
  body?: {
    data?: string | null;
  } | null;
  parts?: GmailApiMessagePart[] | null;
}

export interface GmailApiMessageData {
  id?: string | null;
  payload?: (GmailApiMessagePart & {
    headers?: Array<{ name?: string | null; value?: string | null }> | null;
  }) | null;
}

export interface GmailMessagesResource {
  list(params: {
    userId: "me";
    q: string;
    maxResults: number;
    pageToken?: string;
  }): Promise<{
    data: {
      messages?: Array<{ id?: string | null; threadId?: string | null }>;
      nextPageToken?: string | null;
    };
  }>;
  get(params: {
    userId: "me";
    id: string;
    format: "full";
  }): Promise<{
    data: GmailApiMessageData;
  }>;
}

export class GmailApiClient implements GmailClient {
  private resource?: GmailMessagesResource;

  constructor(
    private readonly config: AppConfig["gmail"],
    resource?: GmailMessagesResource
  ) {
    this.resource = resource;
  }

  async listMessages(query: string): Promise<GmailMessageSummary[]> {
    const resource = this.getResource();
    const messages: GmailMessageSummary[] = [];
    let pageToken: string | undefined;

    do {
      const response = await resource.list({
        userId: "me",
        q: query,
        maxResults: 100,
        pageToken
      });

      for (const message of response.data.messages ?? []) {
        if (message.id) {
          messages.push({
            id: message.id,
            threadId: message.threadId ?? undefined
          });
        }
      }

      pageToken = response.data.nextPageToken ?? undefined;
    } while (pageToken);

    return messages;
  }

  async getMessage(id: string): Promise<GmailMessage> {
    const response = await this.getResource().get({
      userId: "me",
      id,
      format: "full"
    });

    const payload = response.data.payload;
    const headers = payload?.headers ?? [];
    const bodies = collectBodies(payload);
    const html = bodies.html.join("\n\n") || undefined;
    const text = bodies.text.join("\n\n") || (html ? htmlToText(html) : "");

    return {
      id: response.data.id ?? id,
      subject: headerValue(headers, "subject"),
      from: headerValue(headers, "from"),
      date: headerValue(headers, "date"),
      text,
      html
    };
  }

  private getResource(): GmailMessagesResource {
    if (this.resource) {
      return this.resource;
    }

    const clientId = requireConfigValue(this.config.clientId, "GMAIL_CLIENT_ID");
    const clientSecret = requireConfigValue(this.config.clientSecret, "GMAIL_CLIENT_SECRET");
    const refreshToken = requireConfigValue(this.config.refreshToken, "GMAIL_REFRESH_TOKEN");

    const auth = new google.auth.OAuth2(clientId, clientSecret);
    auth.setCredentials({ refresh_token: refreshToken });
    this.resource = google.gmail({ version: "v1", auth }).users.messages as GmailMessagesResource;

    return this.resource;
  }
}

function headerValue(headers: Array<{ name?: string | null; value?: string | null }>, name: string): string | undefined {
  return headers.find((header) => header.name?.toLowerCase() === name)?.value ?? undefined;
}

function collectBodies(part: GmailApiMessagePart | null | undefined): { text: string[]; html: string[] } {
  const bodies = { text: [] as string[], html: [] as string[] };
  collectBodiesInto(part, bodies);
  return bodies;
}

function collectBodiesInto(
  part: GmailApiMessagePart | null | undefined,
  bodies: { text: string[]; html: string[] }
): void {
  if (!part) {
    return;
  }

  const decoded = part.body?.data ? decodeBase64Url(part.body.data) : undefined;
  if (decoded && part.mimeType === "text/plain") {
    bodies.text.push(decoded);
  }
  if (decoded && part.mimeType === "text/html") {
    bodies.html.push(decoded);
  }

  for (const child of part.parts ?? []) {
    collectBodiesInto(child, bodies);
  }
}

function decodeBase64Url(value: string): string {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), "=");
  return Buffer.from(padded, "base64").toString("utf8");
}

function htmlToText(html: string): string {
  return html
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}
