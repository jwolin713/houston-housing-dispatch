# Running the Dispatch

## Setup

1. Install dependencies with `npm install`.
2. Copy `.env.example` to `.env` and fill in only the credentials needed for the command being run.
3. Initialize the local database with `npm run dev -- init-db`.

## Dry Run

Use dry runs before connecting Substack:

```bash
npm run dev -- dry-run --output output
```

The dry run reads local database state, scores candidates, writes a calibration report, creates a Spiral input artifact, and writes a draft artifact. It does not touch Substack.

## Gmail Intake

After filling in Gmail credentials in `.env`, run:

```bash
npm run dev -- intake
```

The command scans messages matching `GMAIL_QUERY`, parses HAR listings, and stores normalized listing records in the local database.

To inspect what landed:

```bash
npm run dev -- db-summary
```

## Zillow Enrichment

After filling in `APIFY_TOKEN` and `APIFY_ZILLOW_ACTOR_ID`, test enrichment with one listing first:

```bash
npm run dev -- enrich --limit 1
```

Increase the limit only after the first actor run returns useful mapped fields.

## Real Integrations

- Gmail intake uses the Gmail API with read-only OAuth credentials and scans messages matching `GMAIL_QUERY`.
- Apify enrichment is adapter-backed and should be tested with mocked responses before live credentials are enabled.
- Spiral and Substack support manual artifact fallbacks when direct automation is unavailable.
- The workflow must stop at a ready-to-review draft or artifact. Direct publishing is out of scope.

## Scheduling

Start with an external scheduler such as cron, Windows Task Scheduler, or a hosted job runner invoking the CLI. Keep dry-run and full-run commands separate so scheduled jobs can be enabled gradually.
