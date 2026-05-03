import { describe, expect, it } from "vitest";
import { loadConfig } from "../src/config/index.js";
import { assertOperatorAccess } from "../src/security/operatorAccess.js";

describe("assertOperatorAccess", () => {
  it("allows access when no operator token is configured", () => {
    expect(() => assertOperatorAccess(loadConfig({}), undefined)).not.toThrow();
  });

  it("rejects mismatched operator tokens", () => {
    const config = loadConfig({ OPERATOR_ACCESS_TOKEN: "expected" });

    expect(() => assertOperatorAccess(config, "wrong")).toThrow("Operator access denied");
  });
});
