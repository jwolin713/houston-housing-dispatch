"""Instagram client using Meta Graph API."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
import structlog

from src.config import get_settings

logger = structlog.get_logger()

GRAPH_API_URL = "https://graph.facebook.com/v18.0"


@dataclass
class InstagramPostResult:
    """Result of posting to Instagram."""

    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None


class InstagramClient:
    """
    Client for posting to Instagram via Meta Graph API.

    Note: The Graph API does NOT support creating draft posts.
    Posts are either scheduled or published immediately.
    """

    def __init__(self):
        self.settings = get_settings()

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self.settings.instagram_access_token}",
            "Content-Type": "application/json",
        }

    def check_health(self) -> dict:
        """
        Check Instagram API connection health.

        Returns:
            Dict with health status
        """
        if not self.settings.instagram_user_id or not self.settings.instagram_access_token:
            return {
                "healthy": False,
                "authenticated": False,
                "message": "Instagram credentials not configured",
            }

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{GRAPH_API_URL}/{self.settings.instagram_user_id}",
                    params={"access_token": self.settings.instagram_access_token},
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "healthy": True,
                        "authenticated": True,
                        "username": data.get("username"),
                        "message": "Instagram connection OK",
                    }
                else:
                    error = response.json().get("error", {}).get("message", "Unknown error")
                    return {
                        "healthy": False,
                        "authenticated": False,
                        "message": f"API error: {error}",
                    }

        except Exception as e:
            logger.error("Instagram health check failed", error=str(e))
            return {
                "healthy": False,
                "authenticated": False,
                "message": f"Connection error: {str(e)}",
            }

    def create_media_container(
        self,
        image_url: str,
        caption: str,
    ) -> Optional[str]:
        """
        Create a media container (required step before publishing).

        Args:
            image_url: Public URL of the image to post
            caption: Post caption

        Returns:
            Container ID or None if failed
        """
        logger.info("Creating Instagram media container")

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{GRAPH_API_URL}/{self.settings.instagram_user_id}/media",
                    params={
                        "image_url": image_url,
                        "caption": caption,
                        "access_token": self.settings.instagram_access_token,
                    },
                )

                if response.status_code == 200:
                    container_id = response.json().get("id")
                    logger.info("Media container created", container_id=container_id)
                    return container_id
                else:
                    error = response.json().get("error", {}).get("message", "Unknown error")
                    logger.error("Failed to create media container", error=error)
                    return None

        except Exception as e:
            logger.error("Failed to create media container", error=str(e))
            return None

    def publish_container(self, container_id: str) -> InstagramPostResult:
        """
        Publish a media container to Instagram.

        Args:
            container_id: The container ID to publish

        Returns:
            InstagramPostResult with post details
        """
        logger.info("Publishing Instagram post", container_id=container_id)

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{GRAPH_API_URL}/{self.settings.instagram_user_id}/media_publish",
                    params={
                        "creation_id": container_id,
                        "access_token": self.settings.instagram_access_token,
                    },
                )

                if response.status_code == 200:
                    post_id = response.json().get("id")
                    # Instagram doesn't return a direct URL, construct it
                    post_url = f"https://www.instagram.com/p/{post_id}/"

                    logger.info("Instagram post published", post_id=post_id)

                    return InstagramPostResult(
                        success=True,
                        post_id=post_id,
                        post_url=post_url,
                    )
                else:
                    error = response.json().get("error", {}).get("message", "Unknown error")
                    logger.error("Failed to publish Instagram post", error=error)
                    return InstagramPostResult(
                        success=False,
                        error=error,
                    )

        except Exception as e:
            logger.error("Failed to publish Instagram post", error=str(e))
            return InstagramPostResult(
                success=False,
                error=str(e),
            )

    def post_image(
        self,
        image_url: str,
        caption: str,
    ) -> InstagramPostResult:
        """
        Post a single image to Instagram.

        This is a convenience method that combines container creation
        and publishing.

        Args:
            image_url: Public URL of the image
            caption: Post caption

        Returns:
            InstagramPostResult with post details
        """
        # Step 1: Create container
        container_id = self.create_media_container(image_url, caption)
        if not container_id:
            return InstagramPostResult(
                success=False,
                error="Failed to create media container",
            )

        # Step 2: Wait for container to be ready (Instagram recommends polling)
        import time
        time.sleep(5)  # Simple wait; in production, poll the container status

        # Step 3: Publish
        return self.publish_container(container_id)

    def create_carousel_container(
        self,
        image_urls: list[str],
        caption: str,
    ) -> Optional[str]:
        """
        Create a carousel (multi-image) media container.

        Args:
            image_urls: List of public image URLs (2-10 images)
            caption: Post caption

        Returns:
            Container ID or None if failed
        """
        if len(image_urls) < 2 or len(image_urls) > 10:
            logger.error("Carousel requires 2-10 images", count=len(image_urls))
            return None

        logger.info("Creating Instagram carousel container", image_count=len(image_urls))

        try:
            with httpx.Client() as client:
                # First, create containers for each child image
                child_ids = []
                for url in image_urls:
                    response = client.post(
                        f"{GRAPH_API_URL}/{self.settings.instagram_user_id}/media",
                        params={
                            "image_url": url,
                            "is_carousel_item": "true",
                            "access_token": self.settings.instagram_access_token,
                        },
                    )
                    if response.status_code == 200:
                        child_ids.append(response.json().get("id"))
                    else:
                        logger.error("Failed to create carousel child", url=url)
                        return None

                # Then create the carousel container
                response = client.post(
                    f"{GRAPH_API_URL}/{self.settings.instagram_user_id}/media",
                    params={
                        "media_type": "CAROUSEL",
                        "caption": caption,
                        "children": ",".join(child_ids),
                        "access_token": self.settings.instagram_access_token,
                    },
                )

                if response.status_code == 200:
                    container_id = response.json().get("id")
                    logger.info("Carousel container created", container_id=container_id)
                    return container_id
                else:
                    error = response.json().get("error", {}).get("message", "Unknown error")
                    logger.error("Failed to create carousel container", error=error)
                    return None

        except Exception as e:
            logger.error("Failed to create carousel container", error=str(e))
            return None


class InstagramDraftManager:
    """
    Manages local Instagram 'drafts' since the API doesn't support them.

    Drafts are stored in the database and published on approval.
    """

    def __init__(self, client: Optional[InstagramClient] = None):
        self.client = client or InstagramClient()
        self.settings = get_settings()

    def generate_caption(
        self,
        newsletter_title: str,
        featured_listings: list[dict],
        substack_url: str,
    ) -> str:
        """
        Generate an Instagram caption from newsletter content.

        Args:
            newsletter_title: Title of the newsletter
            featured_listings: List of featured listing dicts
            substack_url: URL to the Substack post

        Returns:
            Generated caption text
        """
        # Pick top 2-3 listings for highlights
        highlights = featured_listings[:3]

        # Build caption
        lines = [
            f"New listings just dropped 🏠",
            "",
        ]

        for listing in highlights:
            neighborhood = listing.get("neighborhood", "Houston")
            price = listing.get("price", 0)
            lines.append(f"📍 {neighborhood} — ${price:,}")

        lines.extend([
            "",
            f"Full details in today's newsletter (link in bio)",
            "",
            "#houstonrealestate #houstonhomes #htx #houstonhousing "
            "#houstonrealtor #houstonhomesforsale #houstontx",
        ])

        return "\n".join(lines)

    def select_images(
        self,
        listings: list,
        max_images: int = 4,
    ) -> list[str]:
        """
        Select images from listings for the Instagram post.

        Args:
            listings: List of Listing objects
            max_images: Maximum images to include

        Returns:
            List of image URLs
        """
        images = []

        for listing in listings:
            if listing.image_urls:
                # Take first image from each listing
                images.append(listing.image_urls[0])
                if len(images) >= max_images:
                    break

        return images
