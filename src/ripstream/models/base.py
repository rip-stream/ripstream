# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Base model classes with common functionality."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from ripstream.models.enums import DownloadStatus, StreamingSource

# Define a type alias for metadata values - common types used in music metadata
MetadataValue = str | int | float | bool | list[str] | dict[str, str] | None


class RipStreamBaseModel(BaseModel):
    """Base model for all RipStream models with common configuration."""

    model_config = ConfigDict(
        # Enable validation on assignment
        validate_assignment=True,
        # Use enum values instead of enum objects in serialization
        use_enum_values=True,
        # Allow extra fields for extensibility
        extra="allow",
        # Validate default values
        validate_default=True,
        # Enable arbitrary types for complex objects
        arbitrary_types_allowed=True,
    )


class MediaInfo(RipStreamBaseModel):
    """Base information for all media types."""

    id: str = Field(..., description="Unique identifier from the streaming source")
    source: StreamingSource = Field(..., description="Streaming source")
    url: str | None = Field(None, description="Original URL if available")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)


class DownloadableMedia(RipStreamBaseModel):
    """Base class for media that can be downloaded."""

    download_id: UUID = Field(
        default_factory=uuid4, description="Internal download tracking ID"
    )
    status: DownloadStatus = Field(
        default=DownloadStatus.PENDING, description="Download status"
    )
    download_path: str | None = Field(
        None, description="Local file path after download"
    )
    error_message: str | None = Field(
        None, description="Error message if download failed"
    )
    download_started_at: datetime | None = Field(
        None, description="Download start time"
    )
    download_completed_at: datetime | None = Field(
        None, description="Download completion time"
    )
    retry_count: int = Field(default=0, description="Number of download retry attempts")

    def mark_downloading(self) -> None:
        """Mark the media as currently downloading."""
        self.status = DownloadStatus.DOWNLOADING
        self.download_started_at = datetime.now(UTC)
        self.error_message = None

    def mark_completed(self, download_path: str) -> None:
        """Mark the media as successfully downloaded."""
        self.status = DownloadStatus.COMPLETED
        self.download_path = download_path
        self.download_completed_at = datetime.now(UTC)
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """Mark the media as failed to download."""
        self.status = DownloadStatus.FAILED
        self.error_message = error_message
        self.retry_count += 1

    def mark_skipped(self, reason: str) -> None:
        """Mark the media as skipped."""
        self.status = DownloadStatus.SKIPPED
        self.error_message = reason

    @property
    def is_downloaded(self) -> bool:
        """Check if the media has been successfully downloaded."""
        return self.status == DownloadStatus.COMPLETED

    @property
    def can_retry(self) -> bool:
        """Check if the media can be retried (failed but not too many times)."""
        return self.status == DownloadStatus.FAILED and self.retry_count < 3


class SearchableMedia(RipStreamBaseModel):
    """Base class for media that can be searched."""

    search_query: str | None = Field(None, description="Original search query")
    search_rank: int | None = Field(None, description="Rank in search results")
    relevance_score: float | None = Field(None, description="Search relevance score")

    def set_search_info(
        self, query: str, rank: int, score: float | None = None
    ) -> None:
        """Set search-related information."""
        self.search_query = query
        self.search_rank = rank
        self.relevance_score = score


class MetadataContainer(RipStreamBaseModel):
    """Container for metadata with validation and formatting capabilities."""

    raw_metadata: dict[str, MetadataValue] = Field(
        default_factory=dict, description="Raw metadata from source"
    )
    custom_metadata: dict[str, MetadataValue] = Field(
        default_factory=dict, description="User-defined metadata"
    )

    def add_raw_metadata(self, key: str, value: MetadataValue) -> None:
        """Add raw metadata from the streaming source."""
        self.raw_metadata[key] = value

    def add_custom_metadata(self, key: str, value: MetadataValue) -> None:
        """Add custom user-defined metadata."""
        self.custom_metadata[key] = value

    def get_metadata(self, key: str, default: MetadataValue = None) -> MetadataValue:
        """Get metadata value, checking custom first, then raw."""
        return self.custom_metadata.get(key, self.raw_metadata.get(key, default))
