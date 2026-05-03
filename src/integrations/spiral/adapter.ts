import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { NewsletterDraft } from "../../drafting/newsletterDraft.js";

export interface SpiralDraftAdapter {
  createDraft(prompt: string): Promise<NewsletterDraft>;
}

export class ManualSpiralAdapter implements SpiralDraftAdapter {
  constructor(private readonly artifactPath: string) {}

  async createDraft(prompt: string): Promise<NewsletterDraft> {
    mkdirSync(dirname(this.artifactPath), { recursive: true });
    writeFileSync(this.artifactPath, prompt, "utf8");
    return {
      title: "Manual Spiral Draft Needed",
      body: `Use the Spiral input artifact to generate the issue draft:\n\n${this.artifactPath}`
    };
  }
}
