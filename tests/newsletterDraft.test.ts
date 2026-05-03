import { describe, expect, it } from "vitest";
import { validateNewsletterDraft } from "../src/drafting/newsletterDraft.js";

describe("validateNewsletterDraft", () => {
  it("accepts drafts with title and source links", () => {
    expect(() =>
      validateNewsletterDraft({ title: "This Week", body: "A listing: https://www.har.com/1" })
    ).not.toThrow();
  });

  it("rejects drafts without links", () => {
    expect(() => validateNewsletterDraft({ title: "This Week", body: "No sources." })).toThrow("source links");
  });
});
