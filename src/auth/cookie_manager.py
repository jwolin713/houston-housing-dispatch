"""Secure cookie storage and management for Substack authentication."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import structlog
from cryptography.fernet import Fernet, InvalidToken

from src.config import get_settings

logger = structlog.get_logger()


class CookieManager:
    """
    Manages encrypted storage of Substack session cookies.

    Cookies are encrypted at rest using Fernet symmetric encryption.
    The encryption key is derived from the application's SECRET_KEY.
    """

    def __init__(self, cookies_path: Optional[str] = None):
        """
        Initialize the cookie manager.

        Args:
            cookies_path: Path to encrypted cookies file (default from settings)
        """
        self.settings = get_settings()
        self.cookies_path = Path(cookies_path or self.settings.substack_cookies_path)
        self._cipher = self._get_cipher()

    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher from secret key."""
        import base64
        import hashlib

        # Derive a 32-byte key from the secret
        key = hashlib.sha256(self.settings.secret_key.encode()).digest()
        key_b64 = base64.urlsafe_b64encode(key)
        return Fernet(key_b64)

    def save_cookies(self, cookies: dict, metadata: Optional[dict] = None) -> None:
        """
        Save cookies to encrypted file.

        Args:
            cookies: Dict of cookie name -> value
            metadata: Optional metadata (e.g., capture date, expiry estimate)
        """
        data = {
            "cookies": cookies,
            "saved_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        json_data = json.dumps(data)
        encrypted = self._cipher.encrypt(json_data.encode())

        self.cookies_path.write_bytes(encrypted)
        logger.info("Cookies saved", path=str(self.cookies_path))

    def load_cookies(self) -> Optional[dict]:
        """
        Load cookies from encrypted file.

        Returns:
            Dict of cookies or None if not found/invalid
        """
        if not self.cookies_path.exists():
            logger.warning("Cookie file not found", path=str(self.cookies_path))
            return None

        try:
            encrypted = self.cookies_path.read_bytes()
            decrypted = self._cipher.decrypt(encrypted)
            data = json.loads(decrypted.decode())

            logger.info(
                "Cookies loaded",
                saved_at=data.get("saved_at"),
                cookie_count=len(data.get("cookies", {})),
            )

            return data.get("cookies")

        except InvalidToken:
            logger.error("Failed to decrypt cookies - wrong key or corrupted file")
            return None
        except json.JSONDecodeError:
            logger.error("Failed to parse cookie data")
            return None
        except Exception as e:
            logger.error("Failed to load cookies", error=str(e))
            return None

    def get_cookie_age_days(self) -> Optional[int]:
        """Get age of saved cookies in days."""
        if not self.cookies_path.exists():
            return None

        try:
            encrypted = self.cookies_path.read_bytes()
            decrypted = self._cipher.decrypt(encrypted)
            data = json.loads(decrypted.decode())

            saved_at = datetime.fromisoformat(data.get("saved_at", ""))
            age = datetime.utcnow() - saved_at
            return age.days

        except Exception:
            return None

    def check_health(self) -> dict:
        """
        Check cookie health status.

        Returns:
            Dict with health status and recommendations
        """
        result = {
            "healthy": False,
            "exists": self.cookies_path.exists(),
            "age_days": None,
            "expires_soon": False,
            "message": "",
        }

        if not result["exists"]:
            result["message"] = "No cookies saved. Run cookie capture procedure."
            return result

        age = self.get_cookie_age_days()
        result["age_days"] = age

        if age is None:
            result["message"] = "Unable to read cookie age."
            return result

        # Substack cookies typically last ~30 days
        if age > 25:
            result["expires_soon"] = True
            result["message"] = f"Cookies are {age} days old. Refresh recommended."
        elif age > 20:
            result["expires_soon"] = True
            result["healthy"] = True
            result["message"] = f"Cookies are {age} days old. Will need refresh soon."
        else:
            result["healthy"] = True
            result["message"] = f"Cookies are {age} days old. OK."

        return result

    def delete_cookies(self) -> bool:
        """Delete saved cookies."""
        if self.cookies_path.exists():
            self.cookies_path.unlink()
            logger.info("Cookies deleted", path=str(self.cookies_path))
            return True
        return False

    @staticmethod
    def get_cookie_capture_instructions() -> str:
        """Get instructions for capturing Substack cookies."""
        return """
SUBSTACK COOKIE CAPTURE PROCEDURE:

1. Open Chrome/Firefox and go to your Substack dashboard
2. Log in to your Substack account
3. Open Developer Tools (F12 or Cmd+Option+I)
4. Go to Application tab (Chrome) or Storage tab (Firefox)
5. Under Cookies, find 'substack.com'
6. Copy these cookie values:
   - substack.sid (session ID)
   - Any other 'substack' prefixed cookies

7. Run the cookie import command:
   houston-dispatch cookies import --sid "your_sid_value"

Note: Cookies typically expire after ~30 days. You'll need to
refresh them periodically. The system will alert you when
cookies are nearing expiration.
"""
