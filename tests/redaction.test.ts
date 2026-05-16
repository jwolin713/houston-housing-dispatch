import { describe, expect, it } from "vitest";
import { redact, redactObject } from "../src/security/redaction.js";

describe("redact", () => {
  it("redacts token and secret-like values", () => {
    expect(redact("APIFY_TOKEN=abc123 SUBSTACK_SESSION_TOKEN=secret")).toContain("APIFY_TOKEN=[REDACTED]");
    expect(redact("APIFY_TOKEN=abc123 SUBSTACK_SESSION_TOKEN=secret")).toContain(
      "SUBSTACK_SESSION_TOKEN=[REDACTED]"
    );
  });

  it("redacts contact details", () => {
    expect(redact("Email person@example.com or call 713-555-1212")).toBe(
      "Email [REDACTED] or call [REDACTED]"
    );
  });

  it("redacts object JSON", () => {
    expect(redactObject({ session_token: "secret", ok: true })).toEqual({
      session_token: "[REDACTED]",
      ok: true
    });
  });
});
