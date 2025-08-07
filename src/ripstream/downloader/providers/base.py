# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Base abstract classes for download providers."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from ripstream.downloader.base import DownloadableContent, DownloadResult
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource


class DownloadProviderResult(BaseModel):
    """Result container for download provider operations."""

    success: bool = Field(..., description="Whether the operation was successful")
    download_results: list[DownloadResult] = Field(
        default_factory=list, description="List of download results"
    )
    error_message: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional operation metadata"
    )


class BaseDownloadProvider(ABC):
    """Abstract base class for all download providers."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
        credentials: dict[str, Any] | None = None,
    ):
        """Initialize the download provider with configuration and credentials."""
        self.config = config
        self.session_manager = session_manager
        self.progress_tracker = progress_tracker
        self.credentials = credentials or {}
        self._authenticated = False

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Get the name of the streaming service."""
        ...

    @property
    @abstractmethod
    def streaming_source(self) -> StreamingSource:
        """Get the StreamingSource enum value."""
        ...

    @property
    @abstractmethod
    def supported_content_types(self) -> list[ContentType]:
        """Get list of supported content types."""
        ...

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the streaming service."""
        ...

    @abstractmethod
    async def get_download_info(
        self, content_id: str, content_type: ContentType
    ) -> DownloadableContent:
        """Get download information for content."""
        ...

    @abstractmethod
    async def download_content(
        self,
        content_id: str,
        content_type: ContentType,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        """Download content by ID and type."""
        ...

    async def download_artist_discography(
        self,
        artist_id: str,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        """Download an artist's complete discography."""
        # Default implementation - override in subclasses if needed
        return await self.download_content(
            artist_id, ContentType.ARTIST, download_directory, progress_callback
        )

    async def download_album(
        self,
        album_id: str,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        """Download an album."""
        return await self.download_content(
            album_id, ContentType.ALBUM, download_directory, progress_callback
        )

    async def download_playlist(
        self,
        playlist_id: str,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        """Download a playlist."""
        return await self.download_content(
            playlist_id, ContentType.PLAYLIST, download_directory, progress_callback
        )

    async def download_track(
        self,
        track_id: str,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        """Download a single track."""
        return await self.download_content(
            track_id, ContentType.TRACK, download_directory, progress_callback
        )

    @property
    def is_authenticated(self) -> bool:
        """Check if the provider is authenticated."""
        return self._authenticated

    def can_download(self, content_type: ContentType) -> bool:
        """Check if the provider supports downloading the given content type."""
        return content_type in self.supported_content_types

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources. Override in subclasses if needed."""
        ...

    def _create_download_result(
        self,
        success: bool,
        download_results: list[DownloadResult] | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DownloadProviderResult:
        """Create a standardized download provider result."""
        return DownloadProviderResult(
            success=success,
            download_results=download_results or [],
            error_message=error_message,
            metadata=metadata or {},
        )
