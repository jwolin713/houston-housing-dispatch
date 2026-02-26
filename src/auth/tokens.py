"""Token management for approval workflows."""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from src.config import get_settings

logger = structlog.get_logger()


class TokenManager:
    """
    Manages signed, time-limited tokens for approval workflows.

    Uses itsdangerous for secure token generation and verification.
    Tokens include the action type, resource ID, and expiration.
    """

    def __init__(self, salt: str = "approval"):
        """
        Initialize the token manager.

        Args:
            salt: Salt for token generation (different salts = different token types)
        """
        self.settings = get_settings()
        self.serializer = URLSafeTimedSerializer(self.settings.secret_key)
        self.salt = salt

    def create_token(
        self,
        action: str,
        resource_id: int,
        extra_data: Optional[dict] = None,
    ) -> str:
        """
        Create a signed token for an approval action.

        Args:
            action: The action type (e.g., 'approve', 'reject')
            resource_id: The ID of the resource being approved
            extra_data: Optional additional data to include

        Returns:
            URL-safe token string
        """
        data = {
            "action": action,
            "id": resource_id,
            "created": datetime.utcnow().isoformat(),
        }
        if extra_data:
            data.update(extra_data)

        token = self.serializer.dumps(data, salt=self.salt)
        logger.debug(
            "Token created",
            action=action,
            resource_id=resource_id,
        )
        return token

    def verify_token(
        self,
        token: str,
        max_age_hours: Optional[int] = None,
    ) -> Optional[dict]:
        """
        Verify and decode a token.

        Args:
            token: The token string to verify
            max_age_hours: Maximum age in hours (default from settings)

        Returns:
            Decoded data dict or None if invalid/expired
        """
        max_age_hours = max_age_hours or self.settings.approval_timeout_hours
        max_age_seconds = max_age_hours * 3600

        try:
            data = self.serializer.loads(
                token,
                salt=self.salt,
                max_age=max_age_seconds,
            )
            logger.debug(
                "Token verified",
                action=data.get("action"),
                resource_id=data.get("id"),
            )
            return data

        except SignatureExpired:
            logger.warning("Token expired", token=token[:20] + "...")
            return None
        except BadSignature:
            logger.warning("Invalid token signature", token=token[:20] + "...")
            return None

    def create_approval_tokens(
        self,
        resource_id: int,
        resource_type: str = "newsletter",
    ) -> dict:
        """
        Create both approve and reject tokens for a resource.

        Args:
            resource_id: The ID of the resource
            resource_type: Type of resource ('newsletter' or 'instagram')

        Returns:
            Dict with 'approve_token' and 'reject_token'
        """
        return {
            "approve_token": self.create_token(
                action="approve",
                resource_id=resource_id,
                extra_data={"type": resource_type},
            ),
            "reject_token": self.create_token(
                action="reject",
                resource_id=resource_id,
                extra_data={"type": resource_type},
            ),
        }

    def get_token_expiry(self) -> datetime:
        """Get the expiry time for newly created tokens."""
        return datetime.utcnow() + timedelta(hours=self.settings.approval_timeout_hours)
