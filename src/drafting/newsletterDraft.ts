import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

export interface NewsletterDraft {
  title: string;
  body: string;
}

export function validateNewsletterDraft(draft: NewsletterDraft): void {
  if (!draft.title.trim()) {
    throw new Error("Draft title is required before Substack handoff.");
  }
  if (!draft.body.includes("http")) {
    throw new Error("Draft body must include source links before Substack handoff.");
  }
}

export function writeDraftArtifact(path: string, draft: NewsletterDraft): void {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `# ${draft.title}\n\n${draft.body}`, "utf8");
}
