export interface CredentialPolicyEntry {
  name: string;
  owner: string;
  purpose: string;
  minimumScope: string;
  rotation: string;
  loggingRule: string;
}

export const credentialPolicy: CredentialPolicyEntry[] = [
  {
    name: "Gmail OAuth credentials",
    owner: "Editorial operator",
    purpose: "Read HAR notification emails from the dedicated mailbox.",
    minimumScope: "Read-only mailbox access for the dispatch mailbox.",
    rotation: "Rotate if operator changes or token exposure is suspected.",
    loggingRule: "Never log message bodies, OAuth tokens, or refresh tokens."
  },
  {
    name: "Apify token",
    owner: "Editorial operator",
    purpose: "Run the Zillow Details Scraper actor for candidate listings.",
    minimumScope: "Actor execution and dataset read access.",
    rotation: "Rotate if shared outside the runtime environment.",
    loggingRule: "Never log token values or raw paid dataset payloads by default."
  },
  {
    name: "Spiral access",
    owner: "Editorial operator",
    purpose: "Draft newsletter prose from selected listing rationale.",
    minimumScope: "Draft generation only.",
    rotation: "Rotate with vendor account policy.",
    loggingRule: "Log artifact paths, not secret values."
  },
  {
    name: "Substack session or API credential",
    owner: "Editorial operator",
    purpose: "Create or prepare drafts for human review.",
    minimumScope: "Draft creation without publish permission when technically possible.",
    rotation: "Rotate after any local machine or session compromise.",
    loggingRule: "Never log session cookies, tokens, or draft editor payloads."
  }
];
