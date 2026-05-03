import { join } from "node:path";
import type { IssueRun } from "../types/domain.js";
import type { NewsletterDraft } from "../drafting/newsletterDraft.js";
import { validateNewsletterDraft, writeDraftArtifact } from "../drafting/newsletterDraft.js";
import type { SubstackDraftAdapter } from "../integrations/substack/adapter.js";

export async function handoffToSubstackDraft(
  issueRun: IssueRun,
  draft: NewsletterDraft,
  adapter: SubstackDraftAdapter,
  outputDir = "output"
): Promise<IssueRun> {
  validateNewsletterDraft(draft);
  const result = await adapter.createDraft(draft);
  const updated = { ...issueRun, status: "ready_for_review" as const, updatedAt: new Date().toISOString() };

  if (result.draftUrl) {
    updated.substackDraftUrl = result.draftUrl;
  } else {
    const artifactPath = result.artifactPath ?? join(outputDir, `${issueRun.id}-substack-handoff.md`);
    writeDraftArtifact(artifactPath, draft);
    updated.draftArtifactPath = artifactPath;
  }

  return updated;
}
