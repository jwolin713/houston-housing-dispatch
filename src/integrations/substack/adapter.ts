import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { NewsletterDraft } from "../../drafting/newsletterDraft.js";
import { assertDraftOnly } from "../../publishing/publicationGuard.js";

export interface SubstackDraftResult {
  draftUrl?: string;
  artifactPath?: string;
}

export interface SubstackDraftAdapter {
  createDraft(draft: NewsletterDraft): Promise<SubstackDraftResult>;
}

export class ManualSubstackAdapter implements SubstackDraftAdapter {
  constructor(private readonly artifactPath: string) {}

  async createDraft(draft: NewsletterDraft): Promise<SubstackDraftResult> {
    assertDraftOnly("create-draft");
    mkdirSync(dirname(this.artifactPath), { recursive: true });
    writeFileSync(this.artifactPath, `# ${draft.title}\n\n${draft.body}`, "utf8");
    return { artifactPath: this.artifactPath };
  }
}
