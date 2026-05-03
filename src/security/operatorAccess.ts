import type { AppConfig } from "../config/index.js";

export function assertOperatorAccess(config: AppConfig, providedToken: string | undefined): void {
  if (!config.operatorAccessToken) {
    return;
  }

  if (providedToken !== config.operatorAccessToken) {
    throw new Error("Operator access denied.");
  }
}
