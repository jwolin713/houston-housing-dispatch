export function assertDraftOnly(action: "create-draft" | "publish"): void {
  if (action === "publish") {
    throw new Error("Direct Substack publication is out of scope; automation may only create or prepare drafts.");
  }
}
