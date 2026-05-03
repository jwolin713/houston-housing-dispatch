import { Command } from "commander";
import { loadConfig } from "./config/index.js";
import { applyInitialMigration, openDatabase } from "./db/index.js";
import { runDryDispatch } from "./workflows/dryRun.js";

const program = new Command();

program.name("houston-housing-dispatch").description("Houston Housing Dispatch automation CLI");

program
  .command("init-db")
  .description("Initialize the local Dispatch database")
  .action(() => {
    const config = loadConfig();
    const db = openDatabase(config.dbPath);
    try {
      applyInitialMigration(db);
      console.log(`Initialized database at ${config.dbPath}`);
    } finally {
      db.close();
    }
  });

program
  .command("dry-run")
  .description("Build calibration and draft artifacts from local data without touching Substack")
  .option("-o, --output <dir>", "Output directory", "output")
  .action(async (options: { output: string }) => {
    const config = loadConfig();
    const db = openDatabase(config.dbPath);
    try {
      applyInitialMigration(db);
      const result = await runDryDispatch(config, db, options.output);
      console.log(JSON.stringify(result, null, 2));
    } finally {
      db.close();
    }
  });

program.parseAsync();
