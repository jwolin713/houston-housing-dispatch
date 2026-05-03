import { afterEach, describe, expect, it } from "vitest";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { applyInitialMigration, openDatabase } from "../src/db/index.js";

const tempDirs: string[] = [];

afterEach(() => {
  for (const dir of tempDirs.splice(0)) {
    rmSync(dir, { recursive: true, force: true });
  }
});

describe("database setup", () => {
  it("creates parent directories and applies the initial schema", () => {
    const dir = mkdtempSync(join(tmpdir(), "dispatch-db-"));
    tempDirs.push(dir);
    const dbPath = join(dir, "nested", "dispatch.sqlite");

    const db = openDatabase(dbPath);
    try {
      applyInitialMigration(db);

      const tables = db
        .prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
        .all() as Array<{ name: string }>;

      expect(existsSync(dbPath)).toBe(true);
      expect(tables.map((table) => table.name)).toContain("listings");
      expect(tables.map((table) => table.name)).toContain("issue_runs");
    } finally {
      db.close();
    }
  });
});
