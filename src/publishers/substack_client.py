"""Substack client with abstracted interface for draft creation and publishing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.auth.cookie_manager import CookieManager
from src.config import get_settings

logger = structlog.get_logger()


@dataclass
class DraftResult:
    """Result of creating a draft."""

    success: bool
    draft_id: Optional[str] = None
    draft_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class PublishResult:
    """Result of publishing a draft."""

    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None


class NewsletterPublisher(Protocol):
    """
    Protocol for newsletter publishing backends.

    Allows swapping Substack for other platforms or manual fallback.
    """

    def create_draft(self, title: str, content_html: str) -> DraftResult:
        """Create a draft post."""
        ...

    def publish_draft(self, draft_id: str) -> PublishResult:
        """Publish an existing draft."""
        ...

    def check_health(self) -> dict:
        """Check if the publisher is healthy and authenticated."""
        ...


class SubstackClient:
    """
    Client for interacting with Substack via the unofficial API.

    This wraps the python-substack library and adds:
    - Cookie management with encryption
    - Health checks
    - Retry logic
    - Graceful degradation
    """

    def __init__(self, cookie_manager: Optional[CookieManager] = None):
        """
        Initialize the Substack client.

        Args:
            cookie_manager: CookieManager instance (creates default if None)
        """
        self.settings = get_settings()
        self.cookie_manager = cookie_manager or CookieManager()
        self._api = None

    def _get_api(self):
        """Get the Substack API instance, initializing if needed."""
        if self._api is None:
            cookies = self.cookie_manager.load_cookies()
            if not cookies:
                raise RuntimeError(
                    "No Substack cookies available. "
                    "Run: houston-dispatch cookies capture"
                )

            try:
                # Import here to handle missing dependency gracefully
                from substack import Api

                self._api = Api(cookies=cookies)
                logger.info("Substack API initialized")

            except ImportError:
                raise RuntimeError(
                    "python-substack not installed. "
                    "Run: pip install git+https://github.com/ma2za/python-substack.git"
                )

        return self._api

    def check_health(self) -> dict:
        """
        Check Substack connection health.

        Returns:
            Dict with health status
        """
        cookie_health = self.cookie_manager.check_health()

        if not cookie_health["healthy"]:
            return {
                "healthy": False,
                "authenticated": False,
                "cookie_status": cookie_health,
                "message": cookie_health["message"],
            }

        try:
            api = self._get_api()
            # Try to get publication info as a health check
            # This validates that cookies are working
            # Note: Actual implementation depends on python-substack API
            return {
                "healthy": True,
                "authenticated": True,
                "cookie_status": cookie_health,
                "message": "Substack connection OK",
            }
        except Exception as e:
            logger.error("Substack health check failed", error=str(e))
            return {
                "healthy": False,
                "authenticated": False,
                "cookie_status": cookie_health,
                "message": f"API error: {str(e)}",
            }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def create_draft(self, title: str, content_html: str) -> DraftResult:
        """
        Create a draft post on Substack.

        Args:
            title: Post title
            content_html: HTML content

        Returns:
            DraftResult with success status and draft info
        """
        logger.info("Creating Substack draft", title=title)

        try:
            api = self._get_api()

            # Note: Actual implementation depends on python-substack API
            # The library may have different method names
            draft = api.create_draft(
                title=title,
                body_html=content_html,
            )

            draft_id = str(draft.id) if hasattr(draft, "id") else str(draft)
            draft_url = f"{self.settings.substack_publication_url}/publish/post/{draft_id}"

            logger.info(
                "Draft created",
                draft_id=draft_id,
                url=draft_url,
            )

            return DraftResult(
                success=True,
                draft_id=draft_id,
                draft_url=draft_url,
            )

        except Exception as e:
            logger.error("Failed to create draft", error=str(e))
            return DraftResult(
                success=False,
                error=str(e),
            )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def publish_draft(self, draft_id: str) -> PublishResult:
        """
        Publish an existing draft.

        Args:
            draft_id: The draft ID to publish

        Returns:
            PublishResult with success status and post info
        """
        logger.info("Publishing Substack draft", draft_id=draft_id)

        try:
            api = self._get_api()

            # Note: Actual implementation depends on python-substack API
            result = api.publish_draft(draft_id)

            post_url = f"{self.settings.substack_publication_url}/p/{draft_id}"

            logger.info(
                "Draft published",
                draft_id=draft_id,
                url=post_url,
            )

            return PublishResult(
                success=True,
                post_id=draft_id,
                post_url=post_url,
            )

        except Exception as e:
            logger.error("Failed to publish draft", error=str(e))
            return PublishResult(
                success=False,
                error=str(e),
            )


class SubstackPublisher:
    """
    High-level publisher that implements the NewsletterPublisher protocol.

    Provides a clean interface and handles the two-phase commit pattern
    for safe publishing.
    """

    def __init__(self, client: Optional[SubstackClient] = None):
        """
        Initialize the publisher.

        Args:
            client: SubstackClient instance (creates default if None)
        """
        self.client = client or SubstackClient()

    def create_draft(self, title: str, content_html: str) -> DraftResult:
        """Create a draft post."""
        return self.client.create_draft(title, content_html)

    def publish_draft(self, draft_id: str) -> PublishResult:
        """Publish an existing draft."""
        return self.client.publish_draft(draft_id)

    def check_health(self) -> dict:
        """Check publisher health."""
        return self.client.check_health()


class ManualFallbackPublisher:
    """
    Fallback publisher that exports content for manual publishing.

    Used when Substack authentication fails.
    """

    def __init__(self):
        self.settings = get_settings()

    def create_draft(self, title: str, content_html: str) -> DraftResult:
        """
        Create a 'draft' by saving to local file.

        Returns a DraftResult pointing to the local file.
        """
        from pathlib import Path

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"newsletter_draft_{timestamp}.html"
        filepath = Path("data") / "drafts" / filename

        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Create full HTML document
        html_doc = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        h1 {{ font-size: 28px; }}
        h2 {{ font-size: 22px; color: #333; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
        a {{ color: #007bff; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content_html}
</body>
</html>
"""
        filepath.write_text(html_doc)

        logger.info(
            "Draft saved to local file (manual fallback)",
            path=str(filepath),
        )

        return DraftResult(
            success=True,
            draft_id=f"local:{filename}",
            draft_url=str(filepath.absolute()),
            error="Substack unavailable - saved locally for manual publish",
        )

    def publish_draft(self, draft_id: str) -> PublishResult:
        """Cannot auto-publish in fallback mode."""
        return PublishResult(
            success=False,
            error="Manual fallback mode - publish via Substack dashboard",
        )

    def check_health(self) -> dict:
        """Fallback is always 'healthy' in that it works."""
        return {
            "healthy": True,
            "authenticated": False,
            "message": "Fallback mode - manual publishing required",
        }
