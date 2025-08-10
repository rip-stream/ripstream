# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""SQLAlchemy ORM models for download history and pending downloads."""

import pathlib
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ripstream.models.enums import DownloadStatus, MediaType, StreamingSource


class Base(DeclarativeBase):
    """Base class for all database models."""


class FavoriteArtist(Base):
    """User's favorite artists with optional photo URL for quick listing."""

    __tablename__ = "favorite_artists"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Source identification
    source: Mapped[StreamingSource] = mapped_column(
        Enum(StreamingSource), nullable=False
    )
    source_artist_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Basic metadata
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    artist_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "source", "source_artist_id", name="uq_favorite_artist_source_id"
        ),
    )


class DownloadSession(Base):
    """Represents a download session (e.g., downloading all albums from an artist)."""

    __tablename__ = "download_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    source: Mapped[StreamingSource] = mapped_column(
        Enum(StreamingSource), nullable=False
    )

    # Session metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source identifiers
    source_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Artist/Album/Playlist ID from service
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Session status
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(DownloadStatus), default=DownloadStatus.PENDING
    )
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, default=0)
    skipped_items: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Configuration and metadata
    download_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    downloads: Mapped[list["DownloadRecord"]] = relationship(
        "DownloadRecord", back_populates="session", cascade="all, delete-orphan"
    )

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100.0

    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)

    def update_progress(self) -> None:
        """Update progress counters based on download records."""
        self.completed_items = sum(
            1 for d in self.downloads if d.status == DownloadStatus.COMPLETED
        )
        self.failed_items = sum(
            1 for d in self.downloads if d.status == DownloadStatus.FAILED
        )
        self.skipped_items = sum(
            1 for d in self.downloads if d.status == DownloadStatus.SKIPPED
        )
        self.updated_at = datetime.now(UTC)

    @property
    def failed_downloads(self) -> list["DownloadRecord"]:
        """Get failed downloads in this session."""
        return [d for d in self.downloads if d.status == DownloadStatus.FAILED]

    @property
    def can_retry_downloads(self) -> list["DownloadRecord"]:
        """Get failed downloads that can be retried in this session."""
        return [d for d in self.downloads if d.can_retry]

    @property
    def has_failed_downloads(self) -> bool:
        """Check if session has any failed downloads."""
        return self.failed_items > 0

    @property
    def has_retryable_downloads(self) -> bool:
        """Check if session has any downloads that can be retried."""
        return len(self.can_retry_downloads) > 0

    def retry_failed_downloads(self) -> list["DownloadRecord"]:
        """Retry all failed downloads in this session that can be retried."""
        retried = []
        for download in self.can_retry_downloads:
            try:
                download.reset_for_retry()
                retried.append(download)
            except ValueError:
                # Skip downloads that cannot be retried
                continue
        return retried


class DownloadRecord(Base):
    """Individual download record for tracks, albums, etc."""

    __tablename__ = "download_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("download_sessions.id"), nullable=True
    )

    # Media identification
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    source: Mapped[StreamingSource] = mapped_column(
        Enum(StreamingSource), nullable=False
    )
    source_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Track/Album ID from service
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Media metadata
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    artist: Mapped[str] = mapped_column(String(500), nullable=False)
    album: Mapped[str | None] = mapped_column(String(500), nullable=True)
    album_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    album_artist: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Track-specific metadata
    track_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disc_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Download status and progress
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(DownloadStatus), default=DownloadStatus.PENDING
    )
    progress_percentage: Mapped[float] = mapped_column(Float, default=0.0)

    # File information
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # AudioQuality enum value

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Additional metadata
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    session: Mapped["DownloadSession | None"] = relationship(
        "DownloadSession", back_populates="downloads"
    )

    # Unique constraint to prevent duplicate downloads
    __table_args__ = (
        UniqueConstraint(
            "source", "source_id", "media_type", name="uq_download_source_media"
        ),
    )

    @property
    def is_completed(self) -> bool:
        """Check if download is completed."""
        return self.status == DownloadStatus.COMPLETED

    @property
    def can_retry(self) -> bool:
        """Check if download can be retried."""
        return self.status == DownloadStatus.FAILED and self.retry_count < 3

    @property
    def is_failed(self) -> bool:
        """Check if download is failed."""
        return self.status == DownloadStatus.FAILED

    @property
    def is_active(self) -> bool:
        """Check if download is active (pending or downloading)."""
        return self.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)

    @property
    def is_skipped(self) -> bool:
        """Check if download is skipped."""
        return self.status == DownloadStatus.SKIPPED

    @property
    def has_exceeded_retry_limit(self) -> bool:
        """Check if download has exceeded retry limit."""
        return self.retry_count >= 3

    @property
    def display_status(self) -> str:
        """Get human-readable status description."""
        if self.status == DownloadStatus.PENDING:
            return "Pending"
        if self.status == DownloadStatus.DOWNLOADING:
            return f"Downloading ({self.progress_percentage:.1f}%)"
        if self.status == DownloadStatus.COMPLETED:
            return "Completed"
        if self.status == DownloadStatus.FAILED:
            if self.has_exceeded_retry_limit:
                return "Failed (max retries exceeded)"
            return f"Failed (retry {self.retry_count}/3)"
        if self.status == DownloadStatus.SKIPPED:
            return "Skipped"
        return "Unknown"

    def reset_for_retry(self) -> None:
        """Reset download for retry."""
        if not self.can_retry:
            msg = "Download cannot be retried"
            raise ValueError(msg)

        self.status = DownloadStatus.PENDING
        self.error_message = None
        self.started_at = None
        self.completed_at = None
        self.progress_percentage = 0.0
        self.updated_at = datetime.now(UTC)

    def mark_started(self) -> None:
        """Mark download as started."""
        self.status = DownloadStatus.DOWNLOADING
        self.started_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.error_message = None

    def mark_completed(
        self, file_path: str, file_size_bytes: int | None = None
    ) -> None:
        """Mark download as completed."""
        self.status = DownloadStatus.COMPLETED
        self.progress_percentage = 100.0
        self.file_path = file_path
        if file_size_bytes is not None:
            self.file_size_bytes = file_size_bytes
        self.completed_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """Mark download as failed."""
        self.status = DownloadStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1
        self.updated_at = datetime.now(UTC)

    def mark_skipped(self, reason: str) -> None:
        """Mark download as skipped."""
        self.status = DownloadStatus.SKIPPED
        self.error_message = reason
        self.updated_at = datetime.now(UTC)

    def update_progress(self, percentage: float) -> None:
        """Update download progress."""
        self.progress_percentage = max(0.0, min(100.0, percentage))
        self.updated_at = datetime.now(UTC)


class DownloadHistory(Base):
    """Historical record of completed downloads for duplicate detection."""

    __tablename__ = "download_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Media identification
    source: Mapped[StreamingSource] = mapped_column(
        Enum(StreamingSource), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)

    # Basic metadata for quick lookup
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    artist: Mapped[str] = mapped_column(String(500), nullable=False)
    album: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # File information
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quality: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Download information
    downloaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    download_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # File verification
    file_exists: Mapped[bool] = mapped_column(Boolean, default=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Unique constraint to prevent duplicate history entries
    __table_args__ = (
        UniqueConstraint(
            "source", "source_id", "media_type", name="uq_history_source_media"
        ),
    )

    @classmethod
    def from_download_record(cls, record: DownloadRecord) -> "DownloadHistory":
        """Create history entry from completed download record."""
        return cls(
            source=record.source,
            source_id=record.source_id,
            media_type=record.media_type,
            title=record.title,
            artist=record.artist,
            album=record.album,
            file_path=record.file_path or "",
            file_size_bytes=record.file_size_bytes,
            file_format=record.file_format,
            quality=record.quality,
            downloaded_at=record.completed_at or datetime.now(UTC),
            download_session_id=record.session_id,
        )

    def verify_file_exists(self) -> bool:
        """Verify that the downloaded file still exists."""
        exists = pathlib.Path(self.file_path).exists()
        self.file_exists = exists
        self.last_verified_at = datetime.now(UTC)
        return exists


class UISessionState(Base):
    """Persisted UI working session snapshot for restoring on next launch.

    This table stores a single logical record identified by a unique key. The
    record contains the last used URL, the selected artist filter, and a
    condensed metadata snapshot sufficient to rebuild the discography view
    without re-fetching from the network.
    """

    __tablename__ = "ui_session_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Unique logical key for the record (allows future multiple sessions)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    # Minimal UI state
    last_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    artist_filter: Mapped[str | None] = mapped_column(String(32), nullable=True)
    view_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    search_query: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Snapshot of last discography metadata to quickly rebuild UI
    metadata_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
