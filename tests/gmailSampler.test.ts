import { describe, expect, it } from "vitest";
import { sampleGmailMessages } from "../src/intake/gmailSampler.js";
import type { GmailClient } from "../src/integrations/gmail/client.js";

describe("sampleGmailMessages", () => {
  it("returns redacted excerpts for a limited set of Gmail messages", async () => {
    const gmail: GmailClient = {
      async listMessages() {
        return [{ id: "msg-1" }, { id: "msg-2" }];
      },
      async getMessage(id) {
        return {
          id,
          subject: "HAR alert",
          from: "alerts@har.com",
          date: "Sat, 16 May 2026 10:00:00 -0500",
          text: "Contact person@example.com at 713-555-1212 about https://www.har.com/homedetail/example/1"
        };
      }
    };

    const samples = await sampleGmailMessages(gmail, "from:(har.com)", { limit: 1, excerptLength: 200 });

    expect(samples).toEqual([
      {
        id: "msg-1",
        subject: "HAR alert",
        from: "alerts@har.com",
        date: "Sat, 16 May 2026 10:00:00 -0500",
        harUrls: ["https://www.har.com/homedetail/example/1"],
        excerpt: "Contact [REDACTED] at [REDACTED] about https://www.har.com/homedetail/example/1"
      }
    ]);
  });
});
