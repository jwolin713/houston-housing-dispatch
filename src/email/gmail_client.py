"""Gmail API client for fetching HAR email alerts."""

import base64
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings

logger = structlog.get_logger()

# Gmail API scopes needed
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


@dataclass
class EmailMessage:
    """Represents a fetched email message."""

    id: str
    subject: str
    sender: str
    received_at: datetime
    body_html: str
    body_text: str


class GmailClient:
    """Client for interacting with Gmail API to fetch HAR alerts."""

    def __init__(self):
        self.settings = get_settings()
        self._service = None

    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth credentials."""
        creds = None
        token_path = Path(self.settings.gmail_token_file)
        creds_path = Path(self.settings.gmail_credentials_file)

        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing Gmail credentials")
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {creds_path}. "
                        "Download from Google Cloud Console."
                    )
                logger.info("Starting OAuth flow for Gmail")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            token_path.write_text(creds.to_json())
            logger.info("Gmail credentials saved", path=str(token_path))

        return creds

    @property
    def service(self):
        """Get the Gmail API service, initializing if needed."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def _get_label_id(self, label_name: str) -> Optional[str]:
        """Get label ID by name."""
        try:
            results = self.service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])
            for label in labels:
                if label["name"] == label_name:
                    return label["id"]
            return None
        except HttpError as e:
            logger.error("Failed to get labels", error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def fetch_emails(
        self,
        label_name: Optional[str] = None,
        max_results: int = 50,
        after_date: Optional[datetime] = None,
    ) -> list[EmailMessage]:
        """
        Fetch emails from Gmail.

        Args:
            label_name: Optional label to filter by (e.g., "HAR Alerts")
            max_results: Maximum number of emails to fetch
            after_date: Only fetch emails after this date

        Returns:
            List of EmailMessage objects
        """
        label_name = label_name or self.settings.har_email_label
        logger.info(
            "Fetching emails",
            label=label_name,
            max_results=max_results,
            after_date=after_date,
        )

        # Build query - search for HAR emails by subject
        query_parts = ['subject:"HAR.com Saved Search"']
        if after_date:
            # Gmail query format: after:YYYY/MM/DD
            query_parts.append(f"after:{after_date.strftime('%Y/%m/%d')}")

        query = " ".join(query_parts)

        # Optionally also filter by label if it exists
        label_ids = []
        if label_name:
            label_id = self._get_label_id(label_name)
            if label_id:
                label_ids.append(label_id)
                logger.info("Using label filter", label=label_name)
            else:
                logger.info("Label not found, using subject search only", label=label_name)

        try:
            # List messages
            results = (
                self.service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=label_ids if label_ids else None,
                    q=query,
                    maxResults=max_results,
                )
                .execute()
            )

            messages = results.get("messages", [])
            logger.info("Found messages", count=len(messages))

            # Fetch full message details
            emails = []
            for msg in messages:
                email = self._get_message(msg["id"])
                if email:
                    emails.append(email)

            return emails

        except HttpError as e:
            logger.error("Failed to fetch emails", error=str(e))
            raise

    def _get_message(self, message_id: str) -> Optional[EmailMessage]:
        """Fetch and parse a single message."""
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            headers = {
                h["name"]: h["value"] for h in message["payload"].get("headers", [])
            }

            # Parse date
            date_str = headers.get("Date", "")
            try:
                # Try common date formats
                from email.utils import parsedate_to_datetime

                received_at = parsedate_to_datetime(date_str)
            except (ValueError, TypeError):
                received_at = datetime.utcnow()

            # Extract body
            body_html = ""
            body_text = ""
            payload = message["payload"]

            def extract_body(part: dict) -> tuple[str, str]:
                """Recursively extract body from message parts."""
                html = ""
                text = ""
                mime_type = part.get("mimeType", "")

                if "body" in part and "data" in part["body"]:
                    data = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8", errors="replace"
                    )
                    if mime_type == "text/html":
                        html = data
                    elif mime_type == "text/plain":
                        text = data

                if "parts" in part:
                    for subpart in part["parts"]:
                        sub_html, sub_text = extract_body(subpart)
                        if sub_html:
                            html = sub_html
                        if sub_text:
                            text = sub_text

                return html, text

            body_html, body_text = extract_body(payload)

            return EmailMessage(
                id=message_id,
                subject=headers.get("Subject", ""),
                sender=headers.get("From", ""),
                received_at=received_at,
                body_html=body_html,
                body_text=body_text,
            )

        except HttpError as e:
            logger.error("Failed to get message", message_id=message_id, error=str(e))
            return None

    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read by removing UNREAD label."""
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True
        except HttpError as e:
            logger.error("Failed to mark as read", message_id=message_id, error=str(e))
            return False
