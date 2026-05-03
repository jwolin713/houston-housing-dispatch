import { createHash, randomUUID } from "node:crypto";

export function stableId(prefix: string, value: string): string {
  const hash = createHash("sha256").update(value).digest("hex").slice(0, 16);
  return `${prefix}_${hash}`;
}

export function newId(prefix: string): string {
  return `${prefix}_${randomUUID()}`;
}
