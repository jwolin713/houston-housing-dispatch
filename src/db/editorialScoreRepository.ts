import type { DispatchDb } from "./index.js";
import type { EditorialScore } from "../types/domain.js";

export class EditorialScoreRepository {
  constructor(private readonly db: DispatchDb) {}

  upsert(score: EditorialScore): void {
    this.db
      .prepare(
        `
        INSERT INTO editorial_scores (
          listing_id, selected, score, angles_json, rationale, rejection_reason, created_at
        ) VALUES (
          @listingId, @selectedInt, @score, @anglesJson, @rationale, @rejectionReason, @createdAt
        )
        ON CONFLICT(listing_id) DO UPDATE SET
          selected = excluded.selected,
          score = excluded.score,
          angles_json = excluded.angles_json,
          rationale = excluded.rationale,
          rejection_reason = excluded.rejection_reason,
          created_at = excluded.created_at
      `
      )
      .run({
        listingId: score.listingId,
        selectedInt: score.selected ? 1 : 0,
        score: score.score,
        anglesJson: JSON.stringify(score.angles),
        rationale: score.rationale,
        rejectionReason: score.rejectionReason ?? null,
        createdAt: score.createdAt
      });
  }

  all(): EditorialScore[] {
    return this.db
      .prepare(
        `
        SELECT listing_id as listingId, selected, score, angles_json as anglesJson,
          rationale, rejection_reason as rejectionReason, created_at as createdAt
        FROM editorial_scores
        ORDER BY score DESC
      `
      )
      .all()
      .map((row) => {
        const typed = row as {
          listingId: string;
          selected: number;
          score: number;
          anglesJson: string;
          rationale: string;
          rejectionReason: string | null;
          createdAt: string;
        };
        return {
          listingId: typed.listingId,
          selected: Boolean(typed.selected),
          score: typed.score,
          angles: JSON.parse(typed.anglesJson),
          rationale: typed.rationale,
          rejectionReason: typed.rejectionReason ?? undefined,
          createdAt: typed.createdAt
        };
      });
  }
}
