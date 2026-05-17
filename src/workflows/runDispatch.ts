import { join } from "node:path";
import type { AppConfig } from "../config/index.js";
import type { DispatchDb } from "../db/index.js";
import type { GmailClient } from "../integrations/gmail/client.js";
import type { EnrichmentAdapter } from "../enrichment/enrichmentAdapter.js";
import type { NotificationAdapter } from "../notifications/notificationAdapter.js";
import { NoopNotificationAdapter } from "../notifications/notificationAdapter.js";
import { runIntake } from "../intake/runIntake.js";
import { runEnrichment } from "../enrichment/runEnrichment.js";
import { runDryDispatch } from "./dryRun.js";

export async function runDispatch(
  config: AppConfig,
  db: DispatchDb,
  gmail: GmailClient,
  enrichment: EnrichmentAdapter,
  outputDir = "output",
  notifier: NotificationAdapter = new NoopNotificationAdapter(),
  options: { enrichmentLimit?: number } = {}
) {
  const intake = await runIntake(config, db, gmail);
  const enrichmentResult = await runEnrichment(db, enrichment, { limit: options.enrichmentLimit });
  const dryRun = await runDryDispatch(config, db, join(outputDir, "dispatch"));
  const result = {
    intake,
    enrichment: enrichmentResult,
    dryRun,
    substackTouched: false
  };

  await notifier.notifyDispatchReady({
    issueRunId: dryRun.issueRunId,
    selected: dryRun.selected,
    rejected: dryRun.rejected,
    draftPath: dryRun.draftPath,
    calibrationReportPath: dryRun.calibrationReportPath,
    spiralInputPath: dryRun.spiralInputPath,
    substackTouched: result.substackTouched
  });

  return result;
}
