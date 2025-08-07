# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Factory for creating metadata providers based on streaming service."""

import logging
from typing import Any, ClassVar

from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_providers.base import BaseMetadataProvider
from ripstream.ui.metadata_providers.qobuz import QobuzMetadataProvider
from ripstream.ui.metadata_providers.youtube import YouTubeMetadataProvider

logger = logging.getLogger(__name__)


class MetadataProviderFactory:
    """Factory for creating service-specific metadata providers."""

    _providers: ClassVar[dict[StreamingSource, type[BaseMetadataProvider]]] = {
        StreamingSource.QOBUZ: QobuzMetadataProvider,
        StreamingSource.YOUTUBE: YouTubeMetadataProvider,
        # TODO: Note: Deezer and Tidal are not yet fully implemented
        # StreamingSource.DEEZER: DeezerMetadataProvider,
        # StreamingSource.TIDAL: TidalMetadataProvider,
    }

    @classmethod
    def create_provider(
        cls,
        service: StreamingSource,
        credentials: dict[str, Any] | None = None,
    ) -> BaseMetadataProvider:
        """Create a metadata provider for the specified service."""
        if service not in cls._providers:
            supported_services = ", ".join(s.value for s in cls._providers)
            msg = (
                f"Unsupported streaming service: {service.value}. "
                f"Supported services: {supported_services}"
            )
            raise ValueError(msg)

        provider_class = cls._providers[service]
        logger.info("Creating metadata provider for service: %s", service.value)
        return provider_class(credentials)

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
        provider_class: type[BaseMetadataProvider],
    ) -> None:
        """Register a new metadata provider for a service."""
        if not issubclass(provider_class, BaseMetadataProvider):
            msg = "Provider class must inherit from BaseMetadataProvider"
            raise TypeError(msg)

        logger.info("Registering metadata provider for service: %s", service.value)
        cls._providers[service] = provider_class
