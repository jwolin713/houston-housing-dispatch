"""Health check implementations for external services."""

from datetime import datetime

import structlog

from src.auth.cookie_manager import CookieManager
from src.config import get_settings
from src.publishers.instagram_client import InstagramClient
from src.publishers.substack_client import SubstackClient

logger = structlog.get_logger()


class HealthChecker:
    """Runs health checks on all external services."""

    def __init__(self):
        self.settings = get_settings()

    def check_all(self) -> dict:
        """
        Run all health checks.

        Returns:
            Dict with all check results
        """
        checks = {
            "substack": self._check_substack(),
            "cookies": self._check_cookies(),
            "instagram": self._check_instagram(),
            "database": self._check_database(),
        }

        all_healthy = all(
            check.get("healthy", False)
            for check in checks.values()
        )

        return {
            "all_healthy": all_healthy,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        }

    def _check_substack(self) -> dict:
        """Check Substack API health."""
        try:
            client = SubstackClient()
            return client.check_health()
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    def _check_cookies(self) -> dict:
        """Check Substack cookie status."""
        try:
            manager = CookieManager()
            return manager.check_health()
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    def _check_instagram(self) -> dict:
        """Check Instagram API health."""
        # Skip if not configured
        if not self.settings.instagram_access_token:
            return {
                "healthy": True,
                "skipped": True,
                "message": "Instagram not configured",
            }

        try:
            client = InstagramClient()
            return client.check_health()
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }

    def _check_database(self) -> dict:
        """Check database connectivity."""
        try:
            from src.database import get_db

            with get_db() as db:
                # Simple query to verify connection
                db.execute("SELECT 1")

            return {
                "healthy": True,
                "message": "Database connection OK",
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }
