import { requireConfigValue, type AppConfig } from "../../config/index.js";

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

export class GmailApiClient implements GmailClient {
  constructor(private readonly config: AppConfig["gmail"]) {}

  async listMessages(_query: string): Promise<GmailMessageSummary[]> {
    this.assertConfigured();
    throw new Error("Gmail API transport is not implemented yet; use a concrete adapter during integration.");
  }

  async getMessage(_id: string): Promise<GmailMessage> {
    this.assertConfigured();
    throw new Error("Gmail API transport is not implemented yet; use a concrete adapter during integration.");
  }

  private assertConfigured(): void {
    requireConfigValue(this.config.clientId, "GMAIL_CLIENT_ID");
    requireConfigValue(this.config.clientSecret, "GMAIL_CLIENT_SECRET");
    requireConfigValue(this.config.refreshToken, "GMAIL_REFRESH_TOKEN");
  }
}
