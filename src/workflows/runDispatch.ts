import { join } from "node:path";
import type { AppConfig } from "../config/index.js";
import type { DispatchDb } from "../db/index.js";
import type { GmailClient } from "../integrations/gmail/client.js";
import type { EnrichmentAdapter } from "../enrichment/enrichmentAdapter.js";
import { runIntake } from "../intake/runIntake.js";
import { runEnrichment } from "../enrichment/runEnrichment.js";
import { runDryDispatch } from "./dryRun.js";

export async function runDispatch(
  config: AppConfig,
  db: DispatchDb,
  gmail: GmailClient,
  enrichment: EnrichmentAdapter,
  outputDir = "output"
) {
  const intake = await runIntake(config, db, gmail);
  const enrichmentResult = await runEnrichment(db, enrichment);
  const dryRun = await runDryDispatch(config, db, join(outputDir, "dispatch"));

  return {
    intake,
    enrichment: enrichmentResult,
    dryRun,
    substackTouched: false
  };
}
