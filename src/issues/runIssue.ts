import { join } from "node:path";
import type { AppConfig } from "../config/index.js";
import type { DispatchDb } from "../db/index.js";
import { EditorialScoreRepository } from "../db/editorialScoreRepository.js";
import { IssueRunRepository } from "../db/issueRunRepository.js";
import { ListingRepository } from "../db/listingRepository.js";
import { assembleIssueRun } from "./issueAssembler.js";
import { renderCalibrationReport, writeCalibrationReport } from "./calibrationReport.js";

export function runIssueAssembly(config: AppConfig, db: DispatchDb, outputDir = "output") {
  const listings = new ListingRepository(db).all();
  const scores = new EditorialScoreRepository(db).all();
  const issue = assembleIssueRun(config, listings, scores);
  const reportPath = join(outputDir, `${issue.issueRun.id}-calibration.md`);
  const report = renderCalibrationReport(issue, scores, listings);

  issue.issueRun.calibrationReportPath = reportPath;
  issue.issueRun.updatedAt = new Date().toISOString();
  writeCalibrationReport(reportPath, report);
  new IssueRunRepository(db).create(issue.issueRun);

  return { ...issue, reportPath };
}
