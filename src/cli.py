"""Command-line interface for Houston Housing Dispatch."""

import argparse
import json
import sys
from datetime import datetime

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


def cmd_run(args):
    """Run the daily pipeline manually."""
    from src.scheduler.jobs import run_daily_pipeline

    print("Running daily pipeline...")
    result = run_daily_pipeline()
    print(f"\nResult: {json.dumps(result, indent=2)}")


def cmd_ingest(args):
    """Run email ingestion only."""
    from src.database import init_db
    from src.email.processor import EmailProcessor

    init_db()

    print(f"Ingesting emails from the last {args.days} days...")
    processor = EmailProcessor()
    stats = processor.process_emails(days_back=args.days)

    print(f"\nResults:")
    print(f"  Emails fetched: {stats['emails_fetched']}")
    print(f"  Emails processed: {stats['emails_processed']}")
    print(f"  New listings: {stats['listings_new']}")
    print(f"  Updated listings: {stats['listings_updated']}")
    print(f"  Errors: {stats['errors']}")


def cmd_curate(args):
    """Run curation to see what would be selected."""
    from src.database import init_db
    from src.curation.curator import Curator

    init_db()

    curator = Curator()

    print("Checking readiness...")
    readiness = curator.check_readiness()
    print(f"  Ready: {readiness['ready']}")
    print(f"  Total candidates: {readiness['total_candidates']}")
    print(f"  Quality candidates: {readiness['quality_candidates']}")
    print(f"  Required: {readiness['minimum_required']}")

    if args.preview:
        print("\nTop listings preview:")
        preview = curator.get_curated_preview(limit=5)
        for i, listing in enumerate(preview, 1):
            print(f"  {i}. ${listing['price']:,} - {listing['address']}")
            print(f"     {listing['neighborhood']} | Score: {listing['score']:.1f}")


def cmd_health(args):
    """Check system health."""
    from src.monitoring.health_checks import HealthChecker

    checker = HealthChecker()
    results = checker.check_all()

    print(f"\nHealth Check - {results['timestamp']}")
    print("=" * 50)

    for name, check in results["checks"].items():
        status = "✓" if check.get("healthy") else "✗"
        message = check.get("message", check.get("error", ""))
        print(f"  {status} {name}: {message}")

    print("=" * 50)
    print(f"Overall: {'HEALTHY' if results['all_healthy'] else 'UNHEALTHY'}")


def cmd_cookies_status(args):
    """Check cookie status."""
    from src.auth.cookie_manager import CookieManager

    manager = CookieManager()
    health = manager.check_health()

    print("\nCookie Status")
    print("=" * 50)
    print(f"  Exists: {health['exists']}")
    print(f"  Healthy: {health['healthy']}")
    print(f"  Age (days): {health['age_days']}")
    print(f"  Expires soon: {health['expires_soon']}")
    print(f"  Message: {health['message']}")


def cmd_cookies_capture(args):
    """Capture new Substack cookies."""
    from src.auth.cookie_manager import CookieManager

    print(CookieManager.get_cookie_capture_instructions())

    if args.sid:
        manager = CookieManager()
        cookies = {"substack.sid": args.sid}
        manager.save_cookies(cookies)
        print("\n✓ Cookies saved successfully!")


def cmd_server(args):
    """Start the FastAPI server."""
    import uvicorn

    print(f"Starting server on {args.host}:{args.port}...")
    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_scheduler(args):
    """Start the scheduler daemon."""
    from src.scheduler.jobs import PipelineScheduler

    scheduler = PipelineScheduler()

    print("Starting scheduler...")
    print("Scheduled jobs:")
    for job in scheduler.get_jobs():
        print(f"  - {job['name']}: next run at {job['next_run']}")

    scheduler.start()

    try:
        # Keep running until interrupted
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nShutting down...")
        scheduler.stop()


def cmd_stats(args):
    """Show system statistics."""
    from src.database import init_db, get_db
    from src.models import Listing, Newsletter, ListingStatus, NewsletterStatus

    init_db()

    with get_db() as db:
        total_listings = db.query(Listing).count()
        new_listings = db.query(Listing).filter(
            Listing.status == ListingStatus.NEW
        ).count()
        total_newsletters = db.query(Newsletter).count()
        published = db.query(Newsletter).filter(
            Newsletter.status == NewsletterStatus.PUBLISHED
        ).count()

        print("\nHouston Housing Dispatch Statistics")
        print("=" * 50)
        print(f"  Total listings: {total_listings}")
        print(f"  New (unprocessed): {new_listings}")
        print(f"  Total newsletters: {total_newsletters}")
        print(f"  Published: {published}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Houston Housing Dispatch - Newsletter Automation CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run the daily pipeline manually")
    run_parser.set_defaults(func=cmd_run)

    # ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Run email ingestion")
    ingest_parser.add_argument(
        "--days", type=int, default=7, help="Days back to fetch (default: 7)"
    )
    ingest_parser.set_defaults(func=cmd_ingest)

    # curate command
    curate_parser = subparsers.add_parser("curate", help="Check curation status")
    curate_parser.add_argument(
        "--preview", action="store_true", help="Show top listings preview"
    )
    curate_parser.set_defaults(func=cmd_curate)

    # health command
    health_parser = subparsers.add_parser("health", help="Check system health")
    health_parser.set_defaults(func=cmd_health)

    # cookies command
    cookies_parser = subparsers.add_parser("cookies", help="Manage Substack cookies")
    cookies_subparsers = cookies_parser.add_subparsers(dest="cookies_command")

    cookies_status = cookies_subparsers.add_parser("status", help="Check cookie status")
    cookies_status.set_defaults(func=cmd_cookies_status)

    cookies_capture = cookies_subparsers.add_parser(
        "capture", help="Capture new cookies"
    )
    cookies_capture.add_argument("--sid", help="Substack session ID to save")
    cookies_capture.set_defaults(func=cmd_cookies_capture)

    # server command
    server_parser = subparsers.add_parser("server", help="Start the API server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    server_parser.set_defaults(func=cmd_server)

    # scheduler command
    scheduler_parser = subparsers.add_parser("scheduler", help="Start the scheduler")
    scheduler_parser.set_defaults(func=cmd_scheduler)

    # stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    stats_parser.set_defaults(func=cmd_stats)

    # Parse and execute
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, "func"):
        args.func(args)
    elif args.command == "cookies" and args.cookies_command is None:
        cookies_parser.print_help()


if __name__ == "__main__":
    main()
