# Hosted Dispatch Setup

Use this checklist to move Houston Housing Dispatch from local runs to an unattended hosted draft run. This does not create Substack drafts yet; it creates the final markdown draft and notifies you when it is ready.

## 1. Commit And Push

The repository needs a GitHub remote before the included Actions workflow can run.

```bash
git remote add origin <github-repo-url>
git push -u origin codex/houston-housing-dispatch
```

## 2. Add Repository Secrets

In GitHub, open Settings -> Secrets and variables -> Actions -> New repository secret.

Required secrets:

- `GMAIL_QUERY`
- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`
- `APIFY_TOKEN`
- `SPIRAL_API_KEY`

Optional secret:

- `NOTIFICATION_WEBHOOK_URL`

The local Spiral CLI pairing is not enough for GitHub Actions. Create a Personal Access Token at `https://app.writewithspiral.com/settings/api-keys` and store it as `SPIRAL_API_KEY`.

## 3. Add Repository Variables

In GitHub, open Settings -> Secrets and variables -> Actions -> Variables.

Optional variables:

- `DISPATCH_NEIGHBORHOODS`
- `APIFY_ZILLOW_ACTOR_ID`

Recommended values:

```text
DISPATCH_NEIGHBORHOODS=Heights,Montrose,EaDo,Midtown,Rice Military,West University,River Oaks
APIFY_ZILLOW_ACTOR_ID=kawsar/affordable-zillow-details-scraper
```

## 4. Run Manually First

Open Actions -> Dispatch Draft -> Run workflow.

Check:

- the job finishes successfully
- the uploaded `dispatch-output` artifact contains a draft markdown file
- the notification fires if `NOTIFICATION_WEBHOOK_URL` is configured
- the draft still stops before Substack/publication

## 5. Enable Schedule

The workflow currently runs at `14:00 UTC` on Tuesdays and Fridays. Adjust `.github/workflows/dispatch-draft.yml` if you want a different cadence.

## 6. Production Caveats

- GitHub Actions cache is a practical first pass for SQLite state, not a long-term database strategy.
- A missed cache write can cause older listings to be reconsidered.
- Notification is webhook-only for now. Use Slack, Discord, Zapier, Make, Pipedream, or another webhook receiver.
- Substack remains manual until a stable draft creation route is chosen.
