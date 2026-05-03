# Credentials and Access

Houston Housing Dispatch uses connected accounts for mailbox intake, enrichment, drafting, and Substack draft handoff. Real account access should not be enabled until each credential has an owner, minimum scope, storage location, and rotation plan.

## Credential Inventory

- Gmail OAuth credentials: read HAR notification emails from the dedicated dispatch mailbox. Use read-only mailbox access where possible.
- Apify token: run the Zillow Details Scraper actor and read its dataset output.
- Spiral access: generate or assist with newsletter draft prose. If no stable API is available, use the manual artifact workflow.
- Substack session or API credential: create or prepare drafts only. Disable publish permission technically if Substack supports it; otherwise rely on a dedicated low-privilege account and the publication guard.
- Operator access token: optional local guard for running workflow commands.

## Logging Rules

- Do not log OAuth tokens, refresh tokens, session cookies, or API keys.
- Do not log full mailbox message bodies by default.
- Do not commit `.env` files or local SQLite databases.
- Keep real listing fixtures sanitized if they include private mailbox metadata.

## Environment Separation

- Use separate credentials for development and production runs when possible.
- Default tests and dry runs must use mocks or local artifacts.
- Real integration checks should be opt-in and documented separately from the default test suite.
