import { describe, expect, it } from "vitest";
import { handoffToSubstackDraft } from "../src/publishing/substackDraft.js";
import type { IssueRun } from "../src/types/domain.js";

const issueRun: IssueRun = {
  id: "run_1",
  status: "drafting",
  neighborhoods: ["Heights"],
  selectedListingIds: ["lst_1"],
  rejectedListingIds: [],
  createdAt: "2026-05-03T00:00:00.000Z",
  updatedAt: "2026-05-03T00:00:00.000Z"
};

describe("handoffToSubstackDraft", () => {
  it("stores a draft URL when the adapter creates one", async () => {
    const updated = await handoffToSubstackDraft(
      issueRun,
      { title: "This Week", body: "Source: https://www.har.com/1" },
      { async createDraft() { return { draftUrl: "https://substack.com/draft/1" }; } }
    );

    expect(updated.status).toBe("ready_for_review");
    expect(updated.substackDraftUrl).toBe("https://substack.com/draft/1");
  });
});
