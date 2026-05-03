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

## Real Integrations

- Gmail intake and Apify enrichment are adapter-backed and should be tested with mocked responses before live credentials are enabled.
- Spiral and Substack support manual artifact fallbacks when direct automation is unavailable.
- The workflow must stop at a ready-to-review draft or artifact. Direct publishing is out of scope.

## Scheduling

Start with an external scheduler such as cron, Windows Task Scheduler, or a hosted job runner invoking the CLI. Keep dry-run and full-run commands separate so scheduled jobs can be enabled gradually.
