import { describe, expect, it } from "vitest";
import { WebhookNotificationAdapter } from "../src/notifications/notificationAdapter.js";

describe("WebhookNotificationAdapter", () => {
  it("posts dispatch-ready notifications as JSON", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const adapter = new WebhookNotificationAdapter("https://hooks.example.com/dispatch", async (url, init) => {
      calls.push({ url: String(url), init: init ?? {} });
      return new Response("ok", { status: 200 });
    });

    await adapter.notifyDispatchReady({
      issueRunId: "run_1",
      selected: 13,
      rejected: 94,
      draftPath: "output/run_1-draft.md",
      calibrationReportPath: "output/run_1-calibration.md",
      spiralInputPath: "output/run_1-spiral-input.md",
      substackTouched: false
    });

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe("https://hooks.example.com/dispatch");
    expect(JSON.parse(String(calls[0].init.body))).toMatchObject({
      event: "dispatch_draft_ready",
      issueRunId: "run_1",
      selected: 13,
      substackTouched: false
    });
  });

  it("fails loudly when the webhook rejects the notification", async () => {
    const adapter = new WebhookNotificationAdapter(
      "https://hooks.example.com/dispatch",
      async () => new Response("nope", { status: 500 })
    );

    await expect(
      adapter.notifyDispatchReady({
        issueRunId: "run_1",
        selected: 13,
        rejected: 94,
        draftPath: "output/run_1-draft.md",
        calibrationReportPath: "output/run_1-calibration.md",
        spiralInputPath: "output/run_1-spiral-input.md",
        substackTouched: false
      })
    ).rejects.toThrow("Notification webhook failed: HTTP 500");
  });
});
