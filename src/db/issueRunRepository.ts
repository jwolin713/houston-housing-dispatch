import type { DispatchDb } from "./index.js";
import type { IssueRun } from "../types/domain.js";

export class IssueRunRepository {
  constructor(private readonly db: DispatchDb) {}

  create(issueRun: IssueRun): void {
    this.db
      .prepare(
        `
        INSERT INTO issue_runs (
          id, status, neighborhoods_json, selected_listing_ids_json, rejected_listing_ids_json,
          calibration_report_path, spiral_artifact_path, draft_artifact_path, substack_draft_url,
          created_at, updated_at
        ) VALUES (
          @id, @status, @neighborhoodsJson, @selectedListingIdsJson, @rejectedListingIdsJson,
          @calibrationReportPath, @spiralArtifactPath, @draftArtifactPath, @substackDraftUrl,
          @createdAt, @updatedAt
        )
      `
      )
      .run(toRow(issueRun));
  }

  update(issueRun: IssueRun): void {
    this.db
      .prepare(
        `
        UPDATE issue_runs SET
          status = @status,
          neighborhoods_json = @neighborhoodsJson,
          selected_listing_ids_json = @selectedListingIdsJson,
          rejected_listing_ids_json = @rejectedListingIdsJson,
          calibration_report_path = @calibrationReportPath,
          spiral_artifact_path = @spiralArtifactPath,
          draft_artifact_path = @draftArtifactPath,
          substack_draft_url = @substackDraftUrl,
          updated_at = @updatedAt
        WHERE id = @id
      `
      )
      .run(toRow(issueRun));
  }

  latest(): IssueRun | undefined {
    const row = this.db
      .prepare("SELECT * FROM issue_runs ORDER BY created_at DESC LIMIT 1")
      .get() as Record<string, unknown> | undefined;
    return row ? fromRow(row) : undefined;
  }
}

function toRow(issueRun: IssueRun) {
  return {
    id: issueRun.id,
    status: issueRun.status,
    neighborhoodsJson: JSON.stringify(issueRun.neighborhoods),
    selectedListingIdsJson: JSON.stringify(issueRun.selectedListingIds),
    rejectedListingIdsJson: JSON.stringify(issueRun.rejectedListingIds),
    calibrationReportPath: issueRun.calibrationReportPath ?? null,
    spiralArtifactPath: issueRun.spiralArtifactPath ?? null,
    draftArtifactPath: issueRun.draftArtifactPath ?? null,
    substackDraftUrl: issueRun.substackDraftUrl ?? null,
    createdAt: issueRun.createdAt,
    updatedAt: issueRun.updatedAt
  };
}

function fromRow(row: Record<string, unknown>): IssueRun {
  return {
    id: String(row.id),
    status: row.status as IssueRun["status"],
    neighborhoods: JSON.parse(String(row.neighborhoods_json)),
    selectedListingIds: JSON.parse(String(row.selected_listing_ids_json)),
    rejectedListingIds: JSON.parse(String(row.rejected_listing_ids_json)),
    calibrationReportPath: row.calibration_report_path ? String(row.calibration_report_path) : undefined,
    spiralArtifactPath: row.spiral_artifact_path ? String(row.spiral_artifact_path) : undefined,
    draftArtifactPath: row.draft_artifact_path ? String(row.draft_artifact_path) : undefined,
    substackDraftUrl: row.substack_draft_url ? String(row.substack_draft_url) : undefined,
    createdAt: String(row.created_at),
    updatedAt: String(row.updated_at)
  };
}
