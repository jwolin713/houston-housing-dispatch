import { describe, expect, it } from "vitest";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { SpiralCliAdapter } from "../src/integrations/spiral/adapter.js";

describe("SpiralCliAdapter", () => {
  it("calls Spiral through the CLI and maps the first draft", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-spiral-"));
    const artifactPath = join(dir, "spiral-input.md");
    try {
      const adapter = new SpiralCliAdapter(artifactPath, "instant", async (command, args, options) => {
        expect(command).toMatch(/^npx/);
        expect(options.maxBuffer).toBeGreaterThan(1024);
        expect(args).toEqual([
          "@every-env/spiral-cli@latest",
          "write",
          "Write the Houston Housing Dispatch issue using the attached prompt.",
          "--file",
          artifactPath,
          "--json",
          "--instant"
        ]);
        return {
          stdout: JSON.stringify({
            status: "complete",
            drafts: [
              {
                title: "This Week in Houston Housing",
                content: "# This Week in Houston Housing\n\nA sharp listing note: https://www.har.com/1",
                url: "https://app.writewithspiral.com/chat/session"
              }
            ]
          }),
          stderr: ""
        };
      });

      const draft = await adapter.createDraft("Write the issue");

      expect(readFileSync(artifactPath, "utf8")).toBe("Write the issue");
      expect(draft.title).toBe("This Week in Houston Housing");
      expect(draft.body).toContain("A sharp listing note");
      expect(draft.body).not.toContain("# This Week in Houston Housing");
      expect(draft.body).toContain("[View in Spiral](https://app.writewithspiral.com/chat/session)");
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  it("surfaces Spiral context requests as actionable errors", async () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-spiral-"));
    try {
      const adapter = new SpiralCliAdapter(join(dir, "spiral-input.md"), "interactive", async () => ({
        stdout: JSON.stringify({
          status: "needs_input",
          messages: ["Pull more listing details from the local database."]
        }),
        stderr: ""
      }));

      await expect(adapter.createDraft("Write the issue")).rejects.toThrow(
        "Spiral requested more context: Pull more listing details from the local database."
      );
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
