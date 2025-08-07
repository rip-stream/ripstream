# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Main download service that orchestrates the download workflow."""

import logging
from collections.abc import Callable
from typing import Any

from ripstream.core.url_parser import URLParser
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.base import (
    BaseDownloadProvider,
    DownloadProviderResult,
)
from ripstream.downloader.providers.factory import DownloadProviderFactory
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_providers.base import MetadataResult

logger = logging.getLogger(__name__)


class DownloadService:
    """Main service for orchestrating downloads from URLs."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
    ):
        """Initialize the download service."""
        self.config = config
        self.session_manager = session_manager
        self.progress_tracker = progress_tracker
        self.url_parser = URLParser()
        self._providers: dict[StreamingSource, BaseDownloadProvider] = {}

    async def download_from_url(
        self,
        url: str,
        download_directory: str | None = None,
        credentials: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        """
        Download content from a streaming service URL.

        This method:
        1. Parses the URL to determine service and content type
        2. Fetches metadata using the appropriate metadata provider
        3. Downloads the content using the appropriate download provider

        Args:
            url: The streaming service URL
            download_directory: Directory to download to (optional)
            credentials: Service credentials (optional)
            progress_callback: Progress callback function (optional)

        Returns
        -------
            DownloadProviderResult with download results
        """
        try:
            # Step 1: Parse the URL
            parsed_url = self.url_parser.parse_url(url)
            if not parsed_url.is_valid:
                return self._create_error_result(
                    f"Invalid URL: {url}",
                    {
                        "url": url,
                        "parsed_url": {
                            "service": parsed_url.service.value,
                            "content_type": parsed_url.content_type.value,
                            "content_id": parsed_url.content_id,
                            "url": parsed_url.url,
                            "metadata": parsed_url.metadata,
                        },
                    },
                )

            # Step 2: Get or create download provider
            provider = await self._get_or_create_provider(
                parsed_url.service, credentials
            )

            # Step 3: Download the content
            return await provider.download_content(
                parsed_url.content_id,
                parsed_url.content_type,
                download_directory,
                progress_callback,
            )

        except Exception as e:
            logger.exception("Download from URL failed: %s", url)
            return self._create_error_result(str(e), {"url": url})

    async def download_with_metadata(
        self,
        metadata_result: MetadataResult,
        download_directory: str | None = None,
        credentials: dict[str, Any] | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        """
        Download content using pre-fetched metadata.

        Args:
            metadata_result: Pre-fetched metadata result
            download_directory: Directory to download to (optional)
            credentials: Service credentials (optional)
            progress_callback: Progress callback function (optional)

        Returns
        -------
            DownloadProviderResult with download results
        """
        try:
            # Determine streaming source from metadata
            streaming_source = self._get_streaming_source_from_metadata(metadata_result)

            # Get or create download provider
            provider = await self._get_or_create_provider(streaming_source, credentials)

            # Extract content ID and type from metadata
            content_id = self._extract_content_id_from_metadata(metadata_result)
            content_type = self._determine_content_type_from_metadata(metadata_result)

            # Download the content
            return await provider.download_content(
                content_id,
                content_type,
                download_directory,
                progress_callback,
            )

        except Exception as e:
            logger.exception("Download with metadata failed")
            return self._create_error_result(
                str(e), {"metadata": metadata_result.model_dump()}
            )

    def _validate_url(self, url: str) -> None:
        """Validate URL and raise ValueError if invalid."""
        parsed_url = self.url_parser.parse_url(url)
        if not parsed_url.is_valid:
            msg = f"Invalid URL: {url}"
            raise ValueError(msg)

    async def get_download_info_from_url(
        self, url: str, credentials: dict[str, Any] | None = None
    ) -> Any:
        """Get download information for content from URL."""
        try:
            self._validate_url(url)
            parsed_url = self.url_parser.parse_url(url)

            provider = await self._get_or_create_provider(
                parsed_url.service, credentials
            )
            return await provider.get_download_info(
                parsed_url.content_id, parsed_url.content_type
            )

        except Exception:
            logger.exception("Failed to get download info from URL: %s", url)
            raise

    async def _get_or_create_provider(
        self, service: StreamingSource, credentials: dict[str, Any] | None = None
    ) -> BaseDownloadProvider:
        """Get or create a download provider for the specified service."""
        if service not in self._providers:
            provider = DownloadProviderFactory.create_provider(
                service,
                self.config,
                self.session_manager,
                self.progress_tracker,
                credentials,
            )
            self._providers[service] = provider

        return self._providers[service]

    def _get_streaming_source_from_metadata(
        self, metadata_result: MetadataResult
    ) -> StreamingSource:
        """Extract streaming source from metadata result."""
        service_name = metadata_result.service.lower()

        # Map service names to StreamingSource enum
        service_mapping = {
            "qobuz": StreamingSource.QOBUZ,
            "tidal": StreamingSource.TIDAL,
            "deezer": StreamingSource.DEEZER,
            "youtube": StreamingSource.YOUTUBE,
            "spotify": StreamingSource.SPOTIFY,
        }

        return service_mapping.get(service_name, StreamingSource.UNKNOWN)

    def _validate_content_type(self, content_type: str) -> None:
        """Validate content type and raise ValueError if invalid."""
        valid_types = ["artist", "album", "track", "playlist"]
        if content_type not in valid_types:
            msg = f"Unknown content type: {content_type}"
            raise ValueError(msg)

    def _extract_content_id_from_metadata(self, metadata_result: MetadataResult) -> str:
        """Extract content ID from metadata result."""
        # This is a simplified implementation - in practice, you'd need to
        # extract the ID from the metadata based on the content type
        data = metadata_result.data
        content_type = metadata_result.content_type

        self._validate_content_type(content_type)
        return data.get("id", "")

    def _determine_content_type_from_metadata(
        self, metadata_result: MetadataResult
    ) -> ContentType:
        """Determine content type from metadata result."""
        content_type = metadata_result.content_type

        type_mapping = {
            "artist": ContentType.ARTIST,
            "album": ContentType.ALBUM,
            "track": ContentType.TRACK,
            "playlist": ContentType.PLAYLIST,
        }

        return type_mapping.get(content_type, ContentType.UNKNOWN)

    def _create_error_result(
        self, error_message: str, metadata: dict[str, Any] | None = None
    ) -> DownloadProviderResult:
        """Create an error result."""
        return DownloadProviderResult(
            success=False,
            download_results=[],
            error_message=error_message,
            metadata=metadata or {},
        )

    async def cleanup(self) -> None:
        """Clean up all providers."""
        for provider in self._providers.values():
            await provider.cleanup()
        self._providers.clear()

    def get_supported_services(self) -> list[StreamingSource]:
        """Get list of supported streaming services."""
        return DownloadProviderFactory.get_supported_services()

    def is_service_supported(self, service: StreamingSource) -> bool:
        """Check if a streaming service is supported."""
        return DownloadProviderFactory.is_service_supported(service)
