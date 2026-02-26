---
title: "feat: Houston Housing Dispatch Newsletter Automation System"
type: feat
status: active
date: 2026-02-25
---

# Houston Housing Dispatch Newsletter Automation System

## Overview

Build an end-to-end automation system for the Houston Housing Dispatch Substack newsletter that:
1. Ingests real estate listings from HAR email alerts
2. Uses AI to curate the most interesting 15-20 properties
3. Generates newsletter drafts matching the existing editorial voice
4. Implements a human-in-the-loop approval workflow
5. Auto-publishes to Substack and creates Instagram draft posts

The system processes listings daily and publishes 2-3x per week when enough quality listings accumulate.

## Problem Statement / Motivation

Currently, writing the Houston Housing Dispatch requires:
- Manually reviewing HAR email alerts
- Subjectively selecting interesting properties
- Writing descriptions for 15-20 listings
- Formatting and publishing to Substack
- Creating corresponding Instagram content

This process takes several hours per edition. Automation would:
- Reduce time from hours to minutes (review/approve only)
- Enable more frequent publishing (2-3x/week vs weekly)
- Maintain consistent editorial voice
- Ensure no interesting listings are missed

## Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HOUSTON HOUSING DISPATCH AUTOMATION                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  Gmail API   │───▶│  mail-parser │───▶│ BeautifulSoup│                   │
│  │  (IMAP)      │    │  (parse)     │    │  (extract)   │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                                        │                           │
│         │              EMAIL INGESTION           ▼                           │
│         └────────────────────────────────► [SQLite DB]                       │
│                                                  │                           │
│                                                  ▼                           │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │                    AI CURATION (Daily 8 AM)                    │          │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │          │
│  │  │ Property    │  │ Diversity   │  │ Claude API          │    │          │
│  │  │ Scoring     │──│ Selection   │──│ (ranking + select)  │    │          │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘    │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │                    CONTENT GENERATION                          │          │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │          │
│  │  │ Voice Guide │  │ Claude API  │  │ Newsletter          │    │          │
│  │  │ + Examples  │──│ (generate)  │──│ Assembly            │    │          │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘    │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │                    SUBSTACK DRAFT                              │          │
│  │  ┌─────────────┐  ┌─────────────────────────────────────┐     │          │
│  │  │ python-     │  │ Cookie-based auth (unofficial API)  │     │          │
│  │  │ substack    │──│ Create draft, store reference       │     │          │
│  │  └─────────────┘  └─────────────────────────────────────┘     │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────┐          │
│  │                    APPROVAL WORKFLOW                           │          │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │          │
│  │  │ Email with  │  │ Secure      │  │ On Approve:         │    │          │
│  │  │ Preview     │──│ Magic Links │──│ Publish + Instagram │    │          │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘    │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                              │                                               │
│                        ┌─────┴─────┐                                         │
│                        │ Approved? │                                         │
│                        └─────┬─────┘                                         │
│                     No ▼           ▼ Yes                                     │
│              ┌────────────┐  ┌────────────────────────────────┐             │
│              │ Archive    │  │ Publish Substack               │             │
│              │ + Feedback │  │ + Generate Instagram Draft     │             │
│              └────────────┘  │ + Send IG Approval Email       │             │
│                              └────────────────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.11+ | Best LLM library support, email parsing, async |
| **AI/LLM** | Claude API (Anthropic) | Quality content generation, existing relationship |
| **Email Parsing** | mail-parser + BeautifulSoup | Proven libraries, handles HAR email format |
| **Email Access** | Gmail API (OAuth 2.0) | You already receive HAR alerts; native integration |
| **Database** | SQLite (local) or PostgreSQL (hosted) | Simple start, can scale |
| **Substack** | python-substack (unofficial) | Only option; cookie-based auth |
| **Instagram** | Meta Graph API | Official API, scheduled publishing |
| **Notifications** | Resend or SendGrid | Approval emails with preview |
| **Scheduler** | APScheduler or cron | Daily processing jobs |
| **Web Framework** | FastAPI | Approval endpoints, dashboard |

## Technical Considerations

### Critical: Substack Has No Official API

The unofficial `python-substack` library uses browser session cookies for authentication. This creates risks:

- **Cookie expiration**: Tokens last ~30 days; must refresh manually
- **API instability**: Substack can change internal APIs without notice
- **No webhook support**: Cannot receive events from Substack

**Mitigation:**
1. Implement cookie health checks before operations
2. Alert immediately on auth failures
3. Document manual cookie refresh procedure
4. Build fallback: generate content, allow manual Substack publish

### Instagram Limitations

Meta Graph API does NOT support creating draft posts. Our approach:
- Store drafts locally in database
- Generate approval email with preview
- On approval, publish immediately (or schedule via `publish_time`)

### Email Parsing Reliability

HAR email format may change without notice. Mitigations:
1. Use flexible CSS selectors with fallbacks
2. Store raw email for reprocessing
3. Alert on parsing failures
4. Allow manual listing entry as backup

### Property Scoring Algorithm

```python
def score_property(listing: Listing) -> float:
    score = 0.0

    # Price anomaly (underpriced for area)
    area_median = get_area_median(listing.neighborhood)
    if listing.price < area_median * 0.9:
        score += 30
    elif listing.price < area_median:
        score += 15

    # Architectural interest
    if listing.year_built < 1940:
        score += 20  # Historic
    if listing.year_built > 2024:
        score += 15  # New construction

    # Unique features (from description analysis)
    unique_keywords = ['pool', 'renovated', 'views', 'corner lot', 'guest house']
    for keyword in unique_keywords:
        if keyword in listing.description.lower():
            score += 10

    # Freshness (days on market)
    if listing.days_on_market < 3:
        score += 25
    elif listing.days_on_market < 7:
        score += 10

    # Neighborhood desirability
    premium_neighborhoods = ['Heights', 'Montrose', 'River Oaks', 'West U']
    if listing.neighborhood in premium_neighborhoods:
        score += 15

    return score
```

### Neighborhood Diversity Selection

After scoring, select for diversity:
```python
def select_diverse_listings(scored: List[Listing], target: int = 18) -> List[Listing]:
    selected = []
    neighborhoods_used = set()

    for listing in sorted(scored, key=lambda x: x.score, reverse=True):
        if len(selected) >= target:
            break

        # Ensure neighborhood diversity (max 3 per neighborhood)
        if neighborhoods_used.count(listing.neighborhood) < 3:
            selected.append(listing)
            neighborhoods_used.add(listing.neighborhood)

    return selected
```

## System-Wide Impact

### State Lifecycle

| State | Stored In | Transitions To | Cleanup |
|-------|-----------|----------------|---------|
| `email_received` | SQLite | `parsed` or `parse_failed` | Archive after 30 days |
| `listing_stored` | SQLite | `selected` or `skipped` | Mark as used after newsletter |
| `draft_created` | SQLite + Substack | `approved` or `rejected` | Archive after 48 hours |
| `approved` | SQLite | `published` | - |
| `rejected` | SQLite | Archived | Store feedback for learning |
| `published` | SQLite | Final | - |

### Error Propagation

| Error Source | Detection | Propagation | Recovery |
|--------------|-----------|-------------|----------|
| Gmail API failure | Connection error | Blocks email ingestion | Retry with backoff, alert after 3 failures |
| Parse failure | Exception in parser | Single email skipped | Log raw email, alert, continue |
| Claude API failure | API error/timeout | Blocks curation | Retry 3x, then alert and wait |
| Substack auth failure | 401/redirect | Blocks draft creation | **Alert immediately**, manual cookie refresh |
| Substack publish failure | API error | Draft exists unpublished | Alert, allow manual publish |
| Instagram API failure | API error | Blocks IG post only | Alert, newsletter still published |

### API Rate Limits

| API | Limit | Our Usage | Buffer |
|-----|-------|-----------|--------|
| Gmail API | 250 quota units/sec | ~10/day | Safe |
| Claude API | Varies by plan | ~5 calls/day | Safe |
| Substack (unofficial) | Unknown | ~2 calls/day | Monitor |
| Instagram Graph | 200 calls/hour, 25 posts/day | ~3 posts/week | Safe |
| Resend | 100 emails/day (free) | ~6/day | Safe |

## Acceptance Criteria

### Core Functionality

- [ ] **Email Ingestion**: System connects to Gmail, fetches HAR alerts, parses listing data
- [ ] **Duplicate Detection**: Same address within 30 days is recognized and updated (not duplicated)
- [ ] **AI Curation**: System scores listings and selects 15-20 diverse, interesting properties
- [ ] **Content Generation**: Newsletter matches existing editorial voice and format
- [ ] **Substack Draft**: Draft appears in Substack dashboard correctly formatted
- [ ] **Approval Email**: User receives email with preview and approve/reject links
- [ ] **Publish Flow**: Approved newsletters publish to Substack automatically
- [ ] **Instagram Draft**: System generates caption and stores draft for approval
- [ ] **Instagram Publish**: Approved Instagram posts publish via Meta Graph API

### Edge Cases & Error Handling

- [ ] **Sparse Data**: If <10 quality listings, system waits (doesn't publish thin newsletter)
- [ ] **No Listings**: If 0 listings for 3+ days, alert admin
- [ ] **Parse Failures**: Failed emails logged, raw content preserved, alert sent
- [ ] **Substack Auth Failure**: Immediate alert with instructions for cookie refresh
- [ ] **Approval Timeout**: After 24 hours, send reminder; after 48 hours, archive draft
- [ ] **Rejection Handling**: Archived with feedback, next day starts fresh
- [ ] **Instagram Failure**: Newsletter still publishes; Instagram failure logged separately

### Security

- [ ] **Approval Links**: Signed, time-limited tokens (expire after 24 hours)
- [ ] **Cookie Storage**: Substack cookies encrypted at rest
- [ ] **API Keys**: All secrets in environment variables, never in code
- [ ] **Instagram Tokens**: Long-lived tokens with refresh flow

### Observability

- [ ] **Logging**: All pipeline steps logged with timestamps
- [ ] **Metrics**: Track listings processed, newsletters published, approval times
- [ ] **Alerts**: Email alerts for any pipeline failure
- [ ] **Dashboard**: Simple web UI showing recent activity and system status

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Newsletter frequency | 2-3x per week | Count published posts |
| Time to review | <15 minutes | Timestamp: draft created → approved |
| Listing quality | User approves >80% of drafts | Approval rate |
| Voice consistency | Matches existing style | Manual review initially |
| System uptime | >99% | Pipeline success rate |

## Dependencies & Risks

### Dependencies

| Dependency | Type | Risk Level | Mitigation |
|------------|------|------------|------------|
| HAR email format | External | Medium | Flexible parsing, fallback to manual entry |
| Substack unofficial API | External | **High** | Cookie monitoring, manual publish fallback |
| Claude API | External | Low | Well-documented, reliable |
| Meta Graph API | External | Medium | Official API, but approval required |
| Gmail API | External | Low | Official, well-supported |

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Substack API breaks | Medium | High | Manual publish fallback, monitor library updates |
| HAR changes email format | Low | Medium | Flexible parsing, store raw emails |
| Cookie expires unnoticed | Medium | High | Health checks, immediate alerts |
| Meta app approval rejected | Low | Medium | Apply early, have manual posting fallback |
| AI generates poor content | Low | Medium | Human review before publish |

## Implementation Phases

### Phase 1: Email Ingestion & Storage

**Files to create:**
```
src/
├── __init__.py
├── config.py              # Environment variables, settings
├── models.py              # SQLAlchemy models (Listing, Newsletter, Draft)
├── email/
│   ├── __init__.py
│   ├── gmail_client.py    # Gmail API connection
│   ├── parser.py          # HAR email parsing with BeautifulSoup
│   └── processor.py       # Orchestrates fetch → parse → store
└── database.py            # SQLite/PostgreSQL setup
```

**Acceptance:**
- Connect to Gmail, fetch HAR emails
- Parse listing data (address, price, beds/baths, link)
- Store in database with deduplication
- Log all operations

### Phase 2: AI Curation & Selection

**Files to create:**
```
src/
├── curation/
│   ├── __init__.py
│   ├── scorer.py          # Property scoring algorithm
│   ├── selector.py        # Diversity-aware selection
│   └── curator.py         # Orchestrates score → select → rank
└── ai/
    ├── __init__.py
    └── claude_client.py   # Claude API wrapper
```

**Acceptance:**
- Score all unprocessed listings
- Select 15-20 with neighborhood diversity
- Group by neighborhood
- Store curated set with scores

### Phase 3: Content Generation

**Files to create:**
```
src/
├── generation/
│   ├── __init__.py
│   ├── voice_guide.py     # Editorial voice reference
│   ├── templates.py       # Newsletter structure templates
│   └── generator.py       # Claude-powered content generation
└── assets/
    └── voice_examples.json # Example newsletter snippets
```

**Acceptance:**
- Generate intro paragraph
- Generate description for each listing
- Match existing editorial voice
- Assemble complete newsletter markdown

### Phase 4: Substack Integration

**Files to create:**
```
src/
├── publishers/
│   ├── __init__.py
│   ├── substack_client.py # python-substack wrapper with health checks
│   └── draft_manager.py   # Draft creation, status tracking
└── auth/
    ├── __init__.py
    └── cookie_manager.py  # Secure cookie storage, health checks
```

**Acceptance:**
- Create draft in Substack
- Store draft reference in database
- Health check before operations
- Alert on auth failures

### Phase 5: Approval Workflow

**Files to create:**
```
src/
├── api/
│   ├── __init__.py
│   ├── main.py            # FastAPI app
│   ├── routes/
│   │   ├── approval.py    # Approve/reject endpoints
│   │   └── dashboard.py   # Status dashboard
│   └── auth.py            # Signed token verification
├── notifications/
│   ├── __init__.py
│   ├── email_sender.py    # Resend integration
│   └── templates/
│       └── approval_email.html
└── workflows/
    ├── __init__.py
    └── approval.py        # State machine for approval flow
```

**Acceptance:**
- Send approval email with preview
- Secure approve/reject links
- Publish on approval
- Archive on rejection
- Timeout handling

### Phase 6: Instagram Integration

**Files to create:**
```
src/
├── publishers/
│   └── instagram_client.py # Meta Graph API wrapper
├── generation/
│   └── instagram_generator.py # Caption + image selection
└── notifications/
    └── templates/
        └── instagram_approval.html
```

**Acceptance:**
- Generate Instagram caption from newsletter
- Select/prepare images
- Store local draft
- Separate approval flow
- Publish via Graph API

### Phase 7: Scheduling & Operations

**Files to create:**
```
src/
├── scheduler/
│   ├── __init__.py
│   └── jobs.py            # APScheduler job definitions
├── monitoring/
│   ├── __init__.py
│   ├── health_checks.py   # API health monitoring
│   └── alerting.py        # Failure notifications
└── cli.py                 # Manual operation commands
```

**Acceptance:**
- Daily job runs at 8 AM
- Health checks before operations
- Alerts on failures
- Manual trigger capability

## Data Models

```python
# models.py

class Listing(Base):
    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True)
    address = Column(String, unique=True)
    price = Column(Integer)
    bedrooms = Column(Integer)
    bathrooms = Column(Float)
    sqft = Column(Integer, nullable=True)
    year_built = Column(Integer, nullable=True)
    neighborhood = Column(String)
    har_link = Column(String)
    description_raw = Column(Text)  # From HAR

    # Metadata
    email_id = Column(String)  # Gmail message ID
    received_at = Column(DateTime)
    parsed_at = Column(DateTime)

    # Curation
    score = Column(Float, nullable=True)
    selected_for_newsletter_id = Column(Integer, ForeignKey('newsletters.id'), nullable=True)

    # State
    status = Column(Enum('new', 'scored', 'selected', 'used', 'skipped'))


class Newsletter(Base):
    __tablename__ = 'newsletters'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    intro = Column(Text)
    content_markdown = Column(Text)
    content_html = Column(Text)

    # Substack
    substack_draft_id = Column(String, nullable=True)
    substack_post_url = Column(String, nullable=True)

    # Approval
    approval_token = Column(String)
    approval_expires_at = Column(DateTime)
    status = Column(Enum('draft', 'pending_approval', 'approved', 'rejected', 'published', 'archived'))
    approved_at = Column(DateTime, nullable=True)
    rejection_feedback = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime)
    published_at = Column(DateTime, nullable=True)

    # Relations
    listings = relationship('Listing', backref='newsletter')
    instagram_draft = relationship('InstagramDraft', backref='newsletter', uselist=False)


class InstagramDraft(Base):
    __tablename__ = 'instagram_drafts'

    id = Column(Integer, primary_key=True)
    newsletter_id = Column(Integer, ForeignKey('newsletters.id'))
    caption = Column(Text)
    image_urls = Column(JSON)  # List of image URLs

    # Approval
    approval_token = Column(String)
    status = Column(Enum('draft', 'pending_approval', 'approved', 'rejected', 'published'))

    # Instagram
    instagram_post_id = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
```

## Editorial Voice Guide

Based on analysis of existing Houston Housing Dispatch newsletters:

### Tone
- **Conversational insider**: Write like a knowledgeable friend, not a salesperson
- **Observational**: Notice interesting details others might miss
- **Practical**: Focus on what matters to buyers (parking, layout, condition)
- **Light editorial**: Occasional wit ("someone thought about Houston summers")

### Structure per Listing
```
**$XXX,XXX — [Address]**
X bed / X bath / X,XXX sqft / [Type] / [Year]

[2-3 sentences highlighting what makes this property interesting. Focus on unique
features, neighborhood context, or value proposition. Avoid generic descriptions.]

[HAR Link]
```

### Example Descriptions

**Good** (matches voice):
> "A 1920 bungalow that's been fully gutted and rebuilt—keeping the character but adding the systems a century-old house needs. The private driveway for two cars is genuinely rare on these tight Heights streets."

**Bad** (too generic):
> "Beautiful home with updated kitchen and spacious backyard. Great location near shops and restaurants. Won't last long!"

### Intro Paragraph Style
- Contextualizes the week's offerings
- Mentions 2-3 neighborhood themes
- Sets expectations for what's included
- 2-3 sentences max

**Example:**
> "Clean lines from Montrose to Meyerland, plus a few homes that skipped the gray-box memo. The Heights delivers two traditional builds worth a look, and River Oaks has a French-Mediterranean hybrid that feels lifted from another era."

## Configuration

```python
# config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Gmail
    GMAIL_CREDENTIALS_FILE: str
    GMAIL_TOKEN_FILE: str
    HAR_EMAIL_LABEL: str = "HAR Alerts"

    # Claude
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Substack
    SUBSTACK_PUBLICATION_URL: str
    SUBSTACK_COOKIES_PATH: str  # Encrypted file path

    # Instagram
    INSTAGRAM_USER_ID: str
    INSTAGRAM_ACCESS_TOKEN: str

    # Notifications
    RESEND_API_KEY: str
    NOTIFICATION_EMAIL: str  # Where to send approvals

    # App
    SECRET_KEY: str  # For signing approval tokens
    DATABASE_URL: str = "sqlite:///houston_dispatch.db"

    # Scheduling
    CURATION_HOUR: int = 8  # Run at 8 AM
    MIN_LISTINGS_TO_PUBLISH: int = 10
    MAX_LISTINGS_PER_NEWSLETTER: int = 20
    APPROVAL_TIMEOUT_HOURS: int = 24

    class Config:
        env_file = ".env"
```

## Sources & References

### Internal References
- Newsletter format analysis: [houstonhousingdispatch.substack.com](https://houstonhousingdispatch.substack.com/)

### External References

**Email Parsing:**
- [mail-parser on GitHub](https://github.com/SpamScope/mail-parser)
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)

**AI Content Generation:**
- [LangChain Documentation](https://docs.langchain.com)
- [Anthropic Claude API](https://docs.anthropic.com)

**Substack Integration:**
- [python-substack (unofficial)](https://github.com/ma2za/python-substack)
- Note: No official API exists

**Instagram:**
- [Meta Graph API Content Publishing](https://developers.facebook.com/docs/instagram-api/guides/content-publishing)
- [Instagram API 2026 Rate Limits](https://developers.facebook.com/docs/graph-api/overview/rate-limiting)

**Approval Workflows:**
- [LangGraph Human-in-the-Loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)

### Key Statistics
- Instagram rate limit: 200 calls/hour, 25 posts/day
- Substack cookies valid: ~30 days
- HAR covers: 50,000+ active listings in Houston metro

---

## Technical Review Findings (2026-02-25)

### Review Summary

| Agent | Verdict |
|-------|---------|
| architecture-strategist | Sound with improvements needed |
| code-simplicity-reviewer | **Major simplification recommended** |
| spec-flow-analyzer | Critical gaps identified |
| learnings-researcher | No prior solutions (greenfield) |

### 🔴 Critical Issues (Must Address)

**1. No Transaction/Rollback Strategy**
- If Substack publish succeeds but database update fails, orphaned posts could cause duplicates
- **Action:** Implement two-phase commit: mark "publishing" → publish → verify → mark "published"

**2. Concurrent Approval Handling**
- Double-clicking approve (phone + laptop) could trigger duplicate publishes
- **Action:** Add optimistic locking; first approval wins

**3. Substack API Risk Mitigation**
- `python-substack` uses browser cookies, can break without notice
- **Action:** Abstract behind interface; build "degraded mode" that emails markdown when Substack fails

### 🟡 Simplification Recommendations

The plan may be over-engineered for a personal newsletter tool. Consider:

| Current | Simplified Alternative |
|---------|----------------------|
| 7 phases | 3 phases: Email→DB, AI+Draft, Approval+Publish |
| Property scoring algorithm | Single Claude prompt handles scoring + selection |
| SQLAlchemy + 3 models | JSON files (`listings.json`, `newsletters.json`) |
| FastAPI web framework | CLI: `python approve.py <token>` |
| APScheduler | Single cron job |
| 6-state machine | 3 states: `draft`, `approved`, `published` |

**Estimated reduction:** 1,500+ lines → ~400 lines

### 🔵 User Flow Gaps

| Gap | Recommendation |
|-----|----------------|
| No edit before approval | Accept for V1 or add simple edit capability |
| Listing staleness | Accept risk for V1; property could sell between selection and publish |
| Multiple pending drafts | Enforce single active draft rule |
| Timezone not specified | Add `TIMEZONE = "America/Chicago"` to config |
| Cookie refresh procedure | Document step-by-step guide before launch |

### YAGNI - Consider Skipping

- Dashboard web UI (check Substack directly)
- Metrics tracking (premature; add if needed)
- PostgreSQL option (SQLite is sufficient for 2-3 newsletters/week)
- Configurable `CURATION_HOUR` (hardcode 8 AM)
- Rejection feedback storage (just delete bad drafts)

### Alternative Simplified Architecture

```
houston-dispatch/
├── main.py           # fetch → curate → generate → draft
├── config.py         # .env loader
├── gmail.py          # Fetch HAR emails (~50 lines)
├── parser.py         # Extract listing data (~80 lines)
├── generator.py      # Claude scoring + descriptions (~100 lines)
├── substack.py       # Create draft, publish (~60 lines)
├── approve.py        # CLI approval script
└── data/
    ├── listings.json
    └── newsletters.json
```

### Implementation Strategy

**Recommended approach:** Start with simplified MVP, add complexity only when needed.

1. Phase 1: Basic email → Claude → Substack draft flow
2. Phase 2: Add approval workflow (CLI-based)
3. Phase 3: Add Instagram (only if actually wanted)

The editorial voice guide and curation criteria are valuable—keep those. The infrastructure choices can be much simpler.
