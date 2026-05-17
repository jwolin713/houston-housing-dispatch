import { describe, expect, it } from "vitest";
import { loadConfig, requireConfigValue } from "../src/config/index.js";

describe("loadConfig", () => {
  it("loads typed config from environment values", () => {
    const config = loadConfig({
      DISPATCH_DB_PATH: "./tmp/test.sqlite",
      DISPATCH_NEIGHBORHOODS: "Heights, Montrose, Rice Military",
      DISPATCH_RUN_CADENCE: "twice-weekly",
      GMAIL_QUERY: "from:(har.com)",
      SUBSTACK_BASE_URL: "https://example.substack.com",
      NOTIFICATION_WEBHOOK_URL: "https://hooks.example.com/dispatch"
    });

    expect(config.dbPath).toBe("./tmp/test.sqlite");
    expect(config.neighborhoods).toEqual(["Heights", "Montrose", "Rice Military"]);
    expect(config.runCadence).toBe("twice-weekly");
    expect(config.gmail.query).toBe("from:(har.com)");
    expect(config.spiral.draftMode).toBe("manual");
    expect(config.spiral.generationMode).toBe("instant");
    expect(config.substack.baseUrl).toBe("https://example.substack.com");
    expect(config.notifications.webhookUrl).toBe("https://hooks.example.com/dispatch");
  });

  it("allows optional integration credentials to be absent", () => {
    const config = loadConfig({});

    expect(config.gmail.clientId).toBeUndefined();
    expect(config.apify.token).toBeUndefined();
    expect(config.spiral.apiKey).toBeUndefined();
    expect(config.substack.sessionToken).toBeUndefined();
  });
});

describe("requireConfigValue", () => {
  it("throws for missing required values", () => {
    expect(() => requireConfigValue(undefined, "APIFY_TOKEN")).toThrow(
      "Missing required configuration: APIFY_TOKEN"
    );
  });
});
