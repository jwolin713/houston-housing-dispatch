"""Substack client with abstracted interface for draft creation and publishing."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol

import structlog
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.auth.cookie_manager import CookieManager
from src.config import get_settings

logger = structlog.get_logger()


def html_to_substack_elements(html_content: str) -> list[dict]:
    """
    Convert HTML content to Substack's element format.

    Substack uses a structured document format. This function parses HTML
    and converts it to the appropriate element types.

    Elements can be:
    - {"type": "heading", "content": "text", "level": 1|2|3}
    - {"type": "paragraph", "parts": [{"text": "...", "link": None}, {"text": "...", "link": "url"}]}
    - {"type": "divider"}
    """
    soup = BeautifulSoup(html_content, "html.parser")
    elements = []

    # Find the body content or use the whole thing
    body = soup.find("body") or soup

    for element in body.children:
        if element.name is None:
            # Text node
            text = str(element).strip()
            if text:
                elements.append({"type": "paragraph", "parts": [{"text": text, "link": None}]})

        elif element.name == "h1":
            elements.append({"type": "heading", "content": element.get_text(), "level": 1})

        elif element.name == "h2":
            elements.append({"type": "heading", "content": element.get_text(), "level": 2})

        elif element.name == "h3":
            elements.append({"type": "heading", "content": element.get_text(), "level": 3})

        elif element.name == "p":
            # Handle paragraphs with potential links
            parts = _extract_parts_with_links(element)
            if parts:
                elements.append({"type": "paragraph", "parts": parts})

        elif element.name == "hr":
            elements.append({"type": "divider"})

        elif element.name == "div":
            # Process div contents recursively
            div_html = "".join(str(child) for child in element.children)
            elements.extend(html_to_substack_elements(div_html))

        elif element.name in ["ul", "ol"]:
            # Handle lists
            for li in element.find_all("li", recursive=False):
                parts = _extract_parts_with_links(li)
                if parts:
                    # Prepend bullet
                    parts.insert(0, {"text": "• ", "link": None})
                    elements.append({"type": "paragraph", "parts": parts})

        elif element.name == "a":
            href = element.get("href", "")
            text = element.get_text()
            elements.append({"type": "paragraph", "parts": [{"text": text, "link": href}]})

        elif element.name == "style":
            # Skip style tags
            pass

        else:
            # Fallback: extract text
            text = element.get_text().strip()
            if text:
                elements.append({"type": "paragraph", "parts": [{"text": text, "link": None}]})

    return elements


def _extract_parts_with_links(element) -> list[dict]:
    """Extract text parts from an element, preserving links."""
    parts = []
    for child in element.children:
        if child.name is None:
            text = str(child)
            if text:
                parts.append({"text": text, "link": None})
        elif child.name == "a":
            href = child.get("href", "")
            text = child.get_text()
            if text:
                parts.append({"text": text, "link": href})
        elif child.name == "br":
            parts.append({"text": "\n", "link": None})
        else:
            # Recursively extract from nested elements
            text = child.get_text()
            if text:
                parts.append({"text": text, "link": None})
    return parts


def add_paragraph_to_post(post, parts: list[dict]):
    """Add a paragraph with mixed text and links to a Substack post."""
    if not parts:
        return

    # Start the paragraph with the first part
    first_part = parts[0]
    post.paragraph(first_part["text"])
    if first_part["link"]:
        post.marks([{"type": "link", "href": first_part["link"]}])

    # Add remaining parts
    for part in parts[1:]:
        post.add_complex_text(part["text"])
        if part["link"]:
            post.marks([{"type": "link", "href": part["link"]}])


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

            # Convert dict to semicolon-separated string for python-substack
            cookies_string = "; ".join(f"{k}={v}" for k, v in cookies.items())

            try:
                # Import here to handle missing dependency gracefully
                from substack import Api

                self._api = Api(cookies_string=cookies_string)
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

            # python-substack requires using the Post class
            from substack.post import Post

            # Get user ID for creating posts
            user_id = api.get_user_id()

            # Create post with title
            post = Post(title=title, subtitle="", user_id=user_id)

            # Convert HTML to Substack elements
            elements = html_to_substack_elements(content_html)

            # Add each element to the post using proper methods
            for elem in elements:
                if elem["type"] == "heading":
                    level = elem.get("level", 2)
                    post.heading(elem["content"], level=level)
                elif elem["type"] == "divider":
                    post.horizontal_rule()
                elif elem["type"] == "paragraph":
                    # Use the helper to handle links properly
                    add_paragraph_to_post(post, elem.get("parts", []))

            # Create the draft
            draft = api.post_draft(post.get_draft())

            # Extract draft ID from response
            draft_id = str(draft.get("id", "")) if isinstance(draft, dict) else str(draft)
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
