import { Command } from "commander";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig } from "./config/index.js";
import { applyInitialMigration, openDatabase } from "./db/index.js";
import { summarizeDatabase } from "./db/summary.js";
import { GmailApiClient, type GmailClient } from "./integrations/gmail/client.js";
import { runIntake } from "./intake/runIntake.js";
import { runDryDispatch } from "./workflows/dryRun.js";

interface CliDependencies {
  loadConfig: typeof loadConfig;
  openDatabase: typeof openDatabase;
  applyInitialMigration: typeof applyInitialMigration;
  runDryDispatch: typeof runDryDispatch;
  runIntake: typeof runIntake;
  createGmailClient(config: ReturnType<typeof loadConfig>["gmail"]): GmailClient;
  summarizeDatabase: typeof summarizeDatabase;
  writeLine(message: string): void;
}

const defaultDependencies: CliDependencies = {
  loadConfig,
  openDatabase,
  applyInitialMigration,
  runDryDispatch,
  runIntake,
  createGmailClient: (config) => new GmailApiClient(config),
  summarizeDatabase,
  writeLine: (message) => console.log(message)
};

export function createProgram(dependencies: Partial<CliDependencies> = {}): Command {
  const deps = { ...defaultDependencies, ...dependencies };
  const program = new Command();

  program.name("houston-housing-dispatch").description("Houston Housing Dispatch automation CLI");

  program
    .command("init-db")
    .description("Initialize the local Dispatch database")
    .action(() => {
      const config = deps.loadConfig();
      const db = deps.openDatabase(config.dbPath);
      try {
        deps.applyInitialMigration(db);
        deps.writeLine(`Initialized database at ${config.dbPath}`);
      } finally {
        db.close();
      }
    });

  program
    .command("dry-run")
    .description("Build calibration and draft artifacts from local data without touching Substack")
    .option("-o, --output <dir>", "Output directory", "output")
    .action(async (options: { output: string }) => {
      const config = deps.loadConfig();
      const db = deps.openDatabase(config.dbPath);
      try {
        deps.applyInitialMigration(db);
        const result = await deps.runDryDispatch(config, db, options.output);
        deps.writeLine(JSON.stringify(result, null, 2));
      } finally {
        db.close();
      }
    });

  program
    .command("intake")
    .description("Read matching HAR notification emails from Gmail and store parsed listings")
    .action(async () => {
      const config = deps.loadConfig();
      const db = deps.openDatabase(config.dbPath);
      try {
        deps.applyInitialMigration(db);
        const result = await deps.runIntake(config, db, deps.createGmailClient(config.gmail));
        deps.writeLine(JSON.stringify(result, null, 2));
      } finally {
        db.close();
      }
    });

  program
    .command("db-summary")
    .description("Print listing counts and recently updated listings from the local database")
    .option("-l, --limit <number>", "Recent listing limit", "10")
    .action((options: { limit: string }) => {
      const config = deps.loadConfig();
      const db = deps.openDatabase(config.dbPath);
      try {
        deps.applyInitialMigration(db);
        const limit = Number.parseInt(options.limit, 10);
        const summary = deps.summarizeDatabase(db, Number.isFinite(limit) && limit > 0 ? limit : 10);
        deps.writeLine(JSON.stringify(summary, null, 2));
      } finally {
        db.close();
      }
    });

  return program;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  createProgram().parseAsync();
}
