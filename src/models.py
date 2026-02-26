"""SQLAlchemy models for the Houston Housing Dispatch system."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class ListingStatus(enum.Enum):
    """Status of a listing in the pipeline."""

    NEW = "new"
    SCORED = "scored"
    SELECTED = "selected"
    USED = "used"
    SKIPPED = "skipped"


class NewsletterStatus(enum.Enum):
    """Status of a newsletter in the pipeline."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHING = "publishing"  # Two-phase commit: mark before publish
    PUBLISHED = "published"
    ARCHIVED = "archived"


class InstagramStatus(enum.Enum):
    """Status of an Instagram draft."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class Listing(Base):
    """A real estate listing parsed from HAR email alerts."""

    __tablename__ = "listings"
    __table_args__ = (
        Index("ix_listings_status", "status"),
        Index("ix_listings_received_at", "received_at"),
        Index("ix_listings_neighborhood", "neighborhood"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core listing data
    address = Column(String(500), unique=True, nullable=False)
    price = Column(Integer, nullable=False)
    bedrooms = Column(Integer, nullable=False)
    bathrooms = Column(Float, nullable=False)
    sqft = Column(Integer, nullable=True)
    year_built = Column(Integer, nullable=True)
    neighborhood = Column(String(200), nullable=True)
    property_type = Column(String(100), nullable=True)  # Single Family, Condo, etc.
    har_link = Column(String(1000), nullable=False)
    description_raw = Column(Text, nullable=True)  # Original description from HAR
    image_urls = Column(JSON, nullable=True)  # List of image URLs

    # Email metadata
    email_id = Column(String(100), nullable=True)  # Gmail message ID
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    parsed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Curation
    score = Column(Float, nullable=True)
    selected_for_newsletter_id = Column(
        Integer, ForeignKey("newsletters.id"), nullable=True
    )

    # Generated content
    generated_description = Column(Text, nullable=True)

    # State
    status = Column(
        Enum(ListingStatus), nullable=False, default=ListingStatus.NEW
    )

    # Relationships
    newsletter = relationship("Newsletter", back_populates="listings")

    def __repr__(self) -> str:
        return f"<Listing {self.address} - ${self.price:,}>"


class Newsletter(Base):
    """A newsletter draft or published edition."""

    __tablename__ = "newsletters"
    __table_args__ = (
        Index("ix_newsletters_status", "status"),
        Index("ix_newsletters_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Content
    title = Column(String(500), nullable=False)
    intro = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)

    # Substack
    substack_draft_id = Column(String(100), nullable=True)
    substack_post_url = Column(String(1000), nullable=True)

    # Approval workflow
    approval_token = Column(String(200), nullable=True, unique=True)
    approval_expires_at = Column(DateTime, nullable=True)
    status = Column(
        Enum(NewsletterStatus), nullable=False, default=NewsletterStatus.DRAFT
    )
    approved_at = Column(DateTime, nullable=True)
    rejection_feedback = Column(Text, nullable=True)

    # Optimistic locking for concurrent approval handling
    version = Column(Integer, nullable=False, default=1)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    listings = relationship("Listing", back_populates="newsletter")
    instagram_draft = relationship(
        "InstagramDraft", back_populates="newsletter", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Newsletter {self.id}: {self.title}>"


class InstagramDraft(Base):
    """An Instagram post draft linked to a newsletter."""

    __tablename__ = "instagram_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    newsletter_id = Column(
        Integer, ForeignKey("newsletters.id"), nullable=False, unique=True
    )

    # Content
    caption = Column(Text, nullable=False)
    image_urls = Column(JSON, nullable=True)  # List of image URLs to post

    # Approval
    approval_token = Column(String(200), nullable=True, unique=True)
    status = Column(
        Enum(InstagramStatus), nullable=False, default=InstagramStatus.DRAFT
    )

    # Instagram
    instagram_post_id = Column(String(100), nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Relationships
    newsletter = relationship("Newsletter", back_populates="instagram_draft")

    def __repr__(self) -> str:
        return f"<InstagramDraft {self.id} for Newsletter {self.newsletter_id}>"


class RawEmail(Base):
    """Raw email storage for reprocessing and debugging."""

    __tablename__ = "raw_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String(100), unique=True, nullable=False)  # Gmail message ID
    subject = Column(String(500), nullable=True)
    sender = Column(String(200), nullable=True)
    received_at = Column(DateTime, nullable=False)
    raw_content = Column(Text, nullable=False)  # Full raw email content
    parse_status = Column(String(50), nullable=False, default="pending")
    parse_error = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<RawEmail {self.email_id}>"
