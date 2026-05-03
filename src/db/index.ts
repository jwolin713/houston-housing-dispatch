import Database from "better-sqlite3";
import { mkdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

export type DispatchDb = Database.Database;

export function openDatabase(dbPath: string): DispatchDb {
  const resolved = resolve(dbPath);
  mkdirSync(dirname(resolved), { recursive: true });
  const db = new Database(resolved);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  return db;
}

export function applyMigration(db: DispatchDb, migrationPath: string): void {
  const sql = readFileSync(migrationPath, "utf8");
  db.exec(sql);
}

export function applyInitialMigration(db: DispatchDb): void {
  applyMigration(db, fileURLToPath(new URL("./migrations/001_initial.sql", import.meta.url)));
}
