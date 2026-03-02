"""Initialize file-based credentials from environment variables on Railway.

Railway's filesystem is ephemeral, so credentials stored as files (Gmail OAuth
tokens, Substack cookies) must be loaded from environment variables on startup.

To set these up:
1. Base64-encode each credential file:
   python -c "import base64; print(base64.b64encode(open('credentials.json','rb').read()).decode())"
2. Set the base64 string as an environment variable in Railway.
"""

import base64
import os
from pathlib import Path

import structlog

logger = structlog.get_logger()


def init_credentials():
    """Write base64-encoded credential env vars to files.

    Environment variables:
        GMAIL_CREDENTIALS_B64: base64-encoded credentials.json
        GMAIL_TOKEN_B64: base64-encoded token.json
        SUBSTACK_COOKIES_B64: base64-encoded .substack_cookies.enc
    """
    mappings = [
        ("GMAIL_CREDENTIALS_B64", os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")),
        ("GMAIL_TOKEN_B64", os.environ.get("GMAIL_TOKEN_FILE", "token.json")),
        ("SUBSTACK_COOKIES_B64", os.environ.get("SUBSTACK_COOKIES_PATH", ".substack_cookies.enc")),
    ]

    for env_var, file_path in mappings:
        b64_value = os.environ.get(env_var)
        if not b64_value:
            continue

        path = Path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(b64_value))
            logger.info("Wrote credential file from env", file=str(path), env_var=env_var)
        except Exception as e:
            logger.error("Failed to write credential file", file=str(path), error=str(e))

    # Ensure data directory exists for SQLite
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
