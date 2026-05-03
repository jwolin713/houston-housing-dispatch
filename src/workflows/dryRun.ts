import { join } from "node:path";
import type { AppConfig } from "../config/index.js";
import type { DispatchDb } from "../db/index.js";
import { EditorialScoreRepository } from "../db/editorialScoreRepository.js";
import { EnrichmentRepository } from "../db/enrichmentRepository.js";
import { IssueRunRepository } from "../db/issueRunRepository.js";
import { ListingRepository } from "../db/listingRepository.js";
import { selectCandidates } from "../editorial/candidateSelector.js";
import { runIssueAssembly } from "../issues/runIssue.js";
import { buildDraftPrompt } from "../drafting/draftPromptBuilder.js";
import { ManualSpiralAdapter } from "../integrations/spiral/adapter.js";
import { writeDraftArtifact } from "../drafting/newsletterDraft.js";

export async function runDryDispatch(config: AppConfig, db: DispatchDb, outputDir = "output") {
  const listings = new ListingRepository(db).all();
  const enrichments = new EnrichmentRepository(db);
  const selection = selectCandidates(
    listings.map((listing) => ({
      listing,
      enrichment: enrichments.latestForListing(listing.id)?.mappedFields
    })),
    { minimumScore: 3, maxSelected: 15 }
  );
  const scores = new EditorialScoreRepository(db);
  [...selection.selected, ...selection.rejected].forEach((score) => scores.upsert(score));

  const issue = runIssueAssembly(config, db, outputDir);
  const allScores = scores.all();
  const prompt = buildDraftPrompt(issue, listings, allScores);
  const spiral = new ManualSpiralAdapter(join(outputDir, `${issue.issueRun.id}-spiral-input.md`));
  const draft = await spiral.createDraft(prompt);
  const draftPath = join(outputDir, `${issue.issueRun.id}-draft.md`);
  writeDraftArtifact(draftPath, draft);
  const updatedIssueRun = {
    ...issue.issueRun,
    spiralArtifactPath: join(outputDir, `${issue.issueRun.id}-spiral-input.md`),
    draftArtifactPath: draftPath,
    status: "ready_for_review" as const,
    updatedAt: new Date().toISOString()
  };
  new IssueRunRepository(db).update(updatedIssueRun);

  return {
    issueRunId: issue.issueRun.id,
    selected: selection.selected.length,
    rejected: selection.rejected.length,
    calibrationReportPath: issue.reportPath,
    spiralInputPath: join(outputDir, `${issue.issueRun.id}-spiral-input.md`),
    draftPath
  };
}
