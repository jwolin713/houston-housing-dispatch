# Houston Housing Dispatch

Automated newsletter system for the [Houston Housing Dispatch](https://houstonhousingdispatch.substack.com) Substack publication.

## Overview

This system automates the end-to-end workflow for creating and publishing real estate newsletters:

1. **Ingests** listing alerts from HAR (Houston Association of Realtors) via Gmail
2. **Curates** the most interesting 15-20 properties using AI + rule-based scoring
3. **Generates** newsletter content matching the editorial voice
4. **Creates** drafts in Substack (via unofficial API)
5. **Sends** approval emails with magic links for human review
6. **Publishes** to Substack and optionally creates Instagram posts

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/houston-housing-dispatch.git
cd houston-housing-dispatch

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   # Required
   ANTHROPIC_API_KEY=sk-ant-...
   SECRET_KEY=generate-a-random-string
   NOTIFICATION_EMAIL=your@email.com
   SUBSTACK_PUBLICATION_URL=https://yourpub.substack.com

   # Optional
   RESEND_API_KEY=re_...
   INSTAGRAM_USER_ID=...
   INSTAGRAM_ACCESS_TOKEN=...
   ```

### Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download `credentials.json` to the project root
6. Run the first ingest to authorize:
   ```bash
   houston-dispatch ingest
   ```

### Substack Cookie Setup

Since Substack has no official API, we use browser cookies:

```bash
# Show capture instructions
houston-dispatch cookies capture

# After copying your session ID from browser DevTools:
houston-dispatch cookies capture --sid "your_substack_sid_cookie"
```

## Usage

### Manual Pipeline Run

```bash
# Run the full pipeline
houston-dispatch run

# Just ingest emails
houston-dispatch ingest --days 7

# Check curation readiness
houston-dispatch curate --preview
```

### Start the Scheduler

For automated daily runs:

```bash
# Start the scheduler daemon
houston-dispatch scheduler
```

The scheduler runs:
- Daily pipeline at 8 AM (configurable)
- Cleanup every 6 hours
- Approval reminders every 2 hours
- Health checks every hour

### Start the API Server

For the approval workflow endpoints:

```bash
# Development
houston-dispatch server --reload

# Production
houston-dispatch server --host 0.0.0.0 --port 8000
```

### Check System Health

```bash
houston-dispatch health
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HOUSTON HOUSING DISPATCH                      │
├─────────────────────────────────────────────────────────────────┤
│  Gmail API → Parser → SQLite → Curator → Generator → Substack  │
│                                               ↓                  │
│                                     Approval Email → Publish     │
│                                               ↓                  │
│                                     Instagram (optional)         │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Description |
|-----------|-------------|
| `src/email/` | Gmail API client and HAR email parser |
| `src/curation/` | Property scoring and diversity selection |
| `src/generation/` | Claude-powered content generation |
| `src/publishers/` | Substack and Instagram clients |
| `src/workflows/` | Approval workflow orchestration |
| `src/api/` | FastAPI endpoints for approval |
| `src/scheduler/` | APScheduler job definitions |

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `CURATION_HOUR` | 8 | Hour to run daily pipeline (24h format) |
| `MIN_LISTINGS_TO_PUBLISH` | 10 | Minimum quality listings needed |
| `MAX_LISTINGS_PER_NEWSLETTER` | 20 | Maximum listings per edition |
| `APPROVAL_TIMEOUT_HOURS` | 24 | Time before draft expires |
| `TIMEZONE` | America/Chicago | Timezone for scheduling |

## Editorial Voice

The system generates content matching the Houston Housing Dispatch style:

- **Conversational insider** tone
- **Observational** details about properties
- **Practical** focus on what matters to buyers
- **Light editorial** wit without being snarky

Example generated description:
> "A 1920 bungalow that's been fully gutted and rebuilt—keeping the character but adding the systems a century-old house needs. The private driveway for two cars is genuinely rare on these tight Heights streets."

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
ruff format src/

# Lint
ruff check src/
```

### Project Structure

```
houston-housing-dispatch/
├── src/
│   ├── ai/                 # Claude API client
│   ├── api/                # FastAPI application
│   ├── auth/               # Authentication & tokens
│   ├── curation/           # Scoring & selection
│   ├── email/              # Gmail & parsing
│   ├── generation/         # Content generation
│   ├── monitoring/         # Health checks
│   ├── notifications/      # Email sending
│   ├── publishers/         # Substack & Instagram
│   ├── scheduler/          # Job scheduling
│   ├── workflows/          # Approval workflow
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration
│   ├── database.py         # Database setup
│   └── models.py           # SQLAlchemy models
├── data/                   # SQLite database
├── docs/                   # Documentation
├── tests/                  # Test suite
├── pyproject.toml          # Project metadata
└── .env.example            # Environment template
```

## Limitations & Risks

### Substack API

⚠️ The `python-substack` library uses an **unofficial API** with cookie-based authentication:

- Cookies expire after ~30 days
- Substack can change their internal API without notice
- No official support

**Mitigations:**
- Health checks alert before cookie expiration
- Manual fallback exports content for copy/paste publishing
- Consider migrating to Ghost or Buttondown (official APIs)

### HAR Email Format

HAR may change their email format without notice. The parser uses flexible selectors with fallbacks.

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines first.
