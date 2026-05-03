import { describe, expect, it } from "vitest";
import { assertDraftOnly } from "../src/publishing/publicationGuard.js";

describe("assertDraftOnly", () => {
  it("blocks publish actions", () => {
    expect(() => assertDraftOnly("publish")).toThrow("Direct Substack publication is out of scope");
  });
});
