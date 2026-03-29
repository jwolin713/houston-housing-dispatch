"""Email ingestion module for HAR alerts."""

from src.email.gmail_client import GmailClient
from src.email.parser import HAREmailParser
from src.email.processor import EmailProcessor

__all__ = ["GmailClient", "HAREmailParser", "EmailProcessor"]
