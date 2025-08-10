# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Factory for creating download providers based on streaming service."""

import logging
from typing import Any, ClassVar

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.base import BaseDownloadProvider
from ripstream.downloader.providers.deezer import DeezerDownloadProvider
from ripstream.downloader.providers.qobuz import QobuzDownloadProvider
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource

logger = logging.getLogger(__name__)


class DownloadProviderFactory:
    """Factory for creating service-specific download providers."""

    _providers: ClassVar[dict[StreamingSource, type[BaseDownloadProvider]]] = {
        StreamingSource.QOBUZ: QobuzDownloadProvider,
        StreamingSource.DEEZER: DeezerDownloadProvider,
        # TODO: Add other providers as they are implemented
        # StreamingSource.TIDAL: TidalDownloadProvider,
        # StreamingSource.YOUTUBE: YouTubeDownloadProvider,
    }

    @classmethod
    def create_provider(
        cls,
        service: StreamingSource,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
        credentials: dict[str, Any] | None = None,
    ) -> BaseDownloadProvider:
        """Create a download provider for the specified service."""
        if service not in cls._providers:
            supported_services = ", ".join(s.value for s in cls._providers)
            msg = (
                f"Unsupported streaming service: {service.value}. "
                f"Supported services: {supported_services}"
            )
            raise ValueError(msg)

        provider_class = cls._providers[service]
        logger.info("Creating download provider for service: %s", service.value)
        return provider_class(config, session_manager, progress_tracker, credentials)

    @classmethod
    def get_supported_services(cls) -> list[StreamingSource]:
        """Get list of supported streaming services."""
        return list(cls._providers.keys())

    @classmethod
    def is_service_supported(cls, service: StreamingSource) -> bool:
        """Check if a streaming service is supported."""
        return service in cls._providers

    @classmethod
    def register_provider(
        cls,
        service: StreamingSource,
        provider_class: type[BaseDownloadProvider],
    ) -> None:
        """Register a new download provider for a service."""
        if not issubclass(provider_class, BaseDownloadProvider):
            msg = "Provider class must inherit from BaseDownloadProvider"
            raise TypeError(msg)

        logger.info("Registering download provider for service: %s", service.value)
        cls._providers[service] = provider_class
