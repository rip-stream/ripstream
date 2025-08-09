# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Qobuz download provider implementation - adapter for existing QobuzDownloader."""

import logging
from collections.abc import Callable
from typing import Any

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.base import (
    BaseDownloadProvider,
    DownloadProviderResult,
)
from ripstream.downloader.qobuz.downloader import QobuzDownloader
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource

logger = logging.getLogger(__name__)


class QobuzDownloadProvider(BaseDownloadProvider):
    """Qobuz download provider - adapter for the existing QobuzDownloader."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
        credentials: dict[str, Any] | None = None,
    ):
        """Initialize the Qobuz download provider."""
        super().__init__(config, session_manager, progress_tracker, credentials)
        self._downloader: QobuzDownloader | None = None

    @property
    def service_name(self) -> str:
        """Get the name of the streaming service."""
        return "qobuz"

    @property
    def streaming_source(self) -> StreamingSource:
        """Get the StreamingSource enum value."""
        return StreamingSource.QOBUZ

    @property
    def supported_content_types(self) -> list[ContentType]:
        """Get list of supported content types."""
        return [
            ContentType.TRACK,
            ContentType.ALBUM,
            ContentType.PLAYLIST,
            ContentType.ARTIST,
        ]

    async def authenticate(self) -> bool:
        """Authenticate with Qobuz using the existing QobuzDownloader."""
        try:
            if not self._downloader:
                self._downloader = QobuzDownloader(
                    self.config, self.session_manager, self.progress_tracker
                )

            self._authenticated = await self._downloader.authenticate(self.credentials)
        except Exception:
            logger.exception("Qobuz authentication failed")
            self._authenticated = False
        else:
            return self._authenticated
        return False

    def _validate_downloader(self) -> None:
        """Validate downloader is initialized and raise RuntimeError if not."""
        if not self._downloader:
            msg = "Downloader not initialized"
            raise RuntimeError(msg)

    def _validate_content_type(self, content_type: ContentType) -> None:
        """Validate content type and raise ValueError if unsupported."""
        supported_types = [
            ContentType.TRACK,
            ContentType.ALBUM,
            ContentType.PLAYLIST,
            ContentType.ARTIST,
        ]
        if content_type not in supported_types:
            msg = f"Unsupported content type: {content_type}"
            raise ValueError(msg)

    async def get_download_info(
        self,
        content_id: str,
        content_type: ContentType,  # noqa: ARG002
    ) -> Any:
        """Get download information for content using the existing QobuzDownloader."""
        if not self._authenticated:
            await self.authenticate()

        self._validate_downloader()

        return await self._downloader.get_download_info(content_id)

    async def download_content(
        self,
        content_id: str,
        content_type: ContentType,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,  # noqa: ARG002
    ) -> DownloadProviderResult:
        """Download content by ID and type using the existing QobuzDownloader."""
        try:
            if not self._authenticated:
                await self.authenticate()

            self._validate_downloader()
            self._validate_content_type(content_type)

            # Use the existing QobuzDownloader methods based on content type
            if content_type == ContentType.TRACK:
                # For a single track, rely on downloader to compute album folder and prefetch as needed
                result = await self._downloader.download_track_with_album_folder(
                    content_id, download_directory
                )
                results = [result]
            elif content_type == ContentType.ALBUM:
                results = await self._downloader.download_album(
                    content_id, download_directory
                )
            elif content_type == ContentType.PLAYLIST:
                results = await self._downloader.download_playlist(
                    content_id, download_directory
                )
            elif content_type == ContentType.ARTIST:
                results = await self._downloader.download_artist_discography(
                    content_id, download_directory
                )

            # Overall success is based on reported result success only.
            # Filesystem existence checks are handled at the worker level.
            overall_success = bool(results) and all(
                getattr(r, "success", False) for r in results
            )

            return self._create_download_result(
                success=overall_success,
                download_results=results,
                metadata={"content_type": content_type.value, "content_id": content_id},
            )

        except ValueError:
            # Re-raise ValueError exceptions (like validation errors)
            raise
        except Exception as e:
            logger.exception("Qobuz download failed for content %s", content_id)
            return self._create_download_result(
                success=False,
                error_message=str(e),
                metadata={"content_type": content_type.value, "content_id": content_id},
            )

    async def download_artist_discography(
        self,
        artist_id: str,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,  # noqa: ARG002
    ) -> DownloadProviderResult:
        """Download an artist's complete discography using the existing QobuzDownloader."""
        try:
            if not self._authenticated:
                await self.authenticate()

            self._validate_downloader()

            results = await self._downloader.download_artist_discography(
                artist_id, download_directory
            )

            return self._create_download_result(
                success=True,
                download_results=results,
                metadata={"content_type": "artist", "content_id": artist_id},
            )

        except Exception as e:
            logger.exception(
                "Qobuz artist discography download failed for artist %s", artist_id
            )
            return self._create_download_result(
                success=False,
                error_message=str(e),
                metadata={"content_type": "artist", "content_id": artist_id},
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._downloader:
            await self._downloader.cleanup()
            self._downloader = None
        self._authenticated = False
