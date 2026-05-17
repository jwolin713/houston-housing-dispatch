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

By default, `SPIRAL_DRAFT_MODE=manual`, so the draft artifact tells you where to find the prompt to paste into Spiral. After pairing the Spiral CLI, set this in `.env` to have the dry run call Spiral directly:

```bash
SPIRAL_DRAFT_MODE=cli
SPIRAL_GENERATION_MODE=instant
```

Use `instant` for scheduled runs because the generated prompt already includes the selected listings and editorial context. `interactive` is available for manual experiments, but the workflow will fail fast if Spiral asks for extra context.

Live Spiral draft generation can take several minutes for a full issue. Use a scheduler or shell timeout that allows at least 8 minutes for the dry run.

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

After filling in `APIFY_TOKEN`, set:

```bash
APIFY_ZILLOW_ACTOR_ID=kawsar/affordable-zillow-details-scraper
```

Then test enrichment with one listing first:

```bash
npm run dev -- enrich --limit 1
```

Increase the limit only after the first actor run returns useful mapped fields.

## Real Integrations

- Gmail intake uses the Gmail API with read-only OAuth credentials and scans messages matching `GMAIL_QUERY`.
- Apify enrichment is adapter-backed and should be tested with mocked responses before live credentials are enabled.
- Spiral supports either manual artifact handoff or the paired Spiral CLI. Substack still uses a manual artifact fallback until a stable draft API path is chosen.
- The workflow must stop at a ready-to-review draft or artifact. Direct publishing is out of scope.

## Full Draft Run

After Gmail, Apify, and Spiral are configured, run the unattended draft workflow:

```bash
npm run dev -- dispatch --output output --enrichment-limit 20
```

This command:

- scans Gmail for new HAR listing emails
- enriches candidate listings through Apify/Zillow
- scores and selects the newsletter batch
- drafts the issue through Spiral when `SPIRAL_DRAFT_MODE=cli`
- writes calibration, Spiral input, and draft markdown artifacts
- optionally posts a notification when `NOTIFICATION_WEBHOOK_URL` is set
- never touches Substack

## Scheduling

Start with an external scheduler such as cron, Windows Task Scheduler, or a hosted job runner invoking the CLI. Keep dry-run and full-run commands separate so scheduled jobs can be enabled gradually.

The repository includes `.github/workflows/dispatch-draft.yml` as a hosted-run template. It runs manually or on a Tuesday/Friday schedule, restores the local SQLite database from GitHub Actions cache, uploads the generated output directory as an artifact, and can call a notification webhook.

See `docs/operations/hosted-dispatch-setup.md` for the step-by-step GitHub setup checklist.

Required GitHub secrets:

- `GMAIL_QUERY`
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `APIFY_TOKEN`
- `SPIRAL_API_KEY`

Optional GitHub secrets and variables:

- `NOTIFICATION_WEBHOOK_URL`: POST endpoint for draft-ready notifications.
- `DISPATCH_NEIGHBORHOODS`: repository variable overriding the monitored neighborhood list.
- `APIFY_ZILLOW_ACTOR_ID`: repository variable overriding the Zillow actor ID.
