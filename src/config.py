"""Application configuration using Pydantic settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gmail API
    gmail_credentials_file: str = "credentials.json"
    gmail_token_file: str = "token.json"
    har_email_label: str = "HAR Alerts"

    # Claude API
    anthropic_api_key: str = ""  # Optional when use_ai=False
    claude_model: str = "claude-sonnet-4-20250514"
    use_ai: bool = False  # Set to True to use Claude API for scoring/descriptions

    # Substack
    substack_publication_url: str
    substack_cookies_path: str = ".substack_cookies.enc"

    # Instagram (Meta Graph API)
    instagram_user_id: str = ""
    instagram_access_token: str = ""

    # Email Notifications (Resend)
    resend_api_key: str = ""
    notification_email: str

    # Zillow/Apify enrichment
    apify_api_token: str = ""
    apify_zillow_actor_id: str = "maxcopell/zillow-detail-scraper"
    zillow_enrichment_enabled: bool = True

    # Application
    secret_key: str
    base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///data/houston_dispatch.db"

    # Scheduling
    curation_hour: int = 8
    min_listings_to_publish: int = 10
    max_listings_per_newsletter: int = 20
    approval_timeout_hours: int = 24

    # Timezone
    timezone: str = "America/Chicago"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def database_path(self) -> Path:
        """Get the database file path."""
        if self.database_url.startswith("sqlite:///"):
            return Path(self.database_url.replace("sqlite:///", ""))
        return Path("data/houston_dispatch.db")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
