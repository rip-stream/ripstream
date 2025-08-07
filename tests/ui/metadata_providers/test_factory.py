# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for metadata provider factory."""

import pytest

from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_providers.base import BaseMetadataProvider
from ripstream.ui.metadata_providers.factory import MetadataProviderFactory
from ripstream.ui.metadata_providers.qobuz import QobuzMetadataProvider
from ripstream.ui.metadata_providers.youtube import YouTubeMetadataProvider


class TestMetadataProviderFactory:
    """Test cases for MetadataProviderFactory."""

    @pytest.mark.parametrize(
        ("streaming_source", "expected_provider_class", "expected_service_name"),
        [
            (StreamingSource.QOBUZ, QobuzMetadataProvider, "Qobuz"),
            (StreamingSource.YOUTUBE, YouTubeMetadataProvider, "YouTube"),
        ],
    )
    def test_create_supported_provider(
        self, streaming_source, expected_provider_class, expected_service_name
    ):
        """Test creating supported metadata providers."""
        provider = MetadataProviderFactory.create_provider(streaming_source)
        assert isinstance(provider, expected_provider_class)
        assert isinstance(provider, BaseMetadataProvider)
        assert provider.service_name == expected_service_name
        assert provider.streaming_source == streaming_source

    @pytest.mark.parametrize(
        "streaming_source",
        [
            StreamingSource.DEEZER,
            StreamingSource.TIDAL,
            StreamingSource.SPOTIFY,
        ],
    )
    def test_create_unsupported_provider(self, streaming_source):
        """Test creating unsupported metadata providers raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported streaming service"):
            MetadataProviderFactory.create_provider(streaming_source)

    def test_create_provider_with_credentials(self):
        """Test creating a provider with credentials."""
        credentials = {"username": "test", "password": "test"}
        provider = MetadataProviderFactory.create_provider(
            StreamingSource.QOBUZ, credentials
        )
        assert provider.credentials == credentials

    def test_unsupported_service(self):
        """Test creating provider for unsupported service."""
        with pytest.raises(ValueError, match="Unsupported streaming service"):
            MetadataProviderFactory.create_provider(StreamingSource.SPOTIFY)

    def test_get_supported_services(self):
        """Test getting list of supported services."""
        services = MetadataProviderFactory.get_supported_services()
        expected_services = [
            StreamingSource.QOBUZ,
            StreamingSource.YOUTUBE,
        ]
        assert set(services) == set(expected_services)

    @pytest.mark.parametrize(
        ("streaming_source", "expected_supported"),
        [
            (StreamingSource.QOBUZ, True),
            (StreamingSource.YOUTUBE, True),
            (StreamingSource.DEEZER, False),
            (StreamingSource.TIDAL, False),
            (StreamingSource.SPOTIFY, False),
        ],
    )
    def test_is_service_supported(self, streaming_source, expected_supported):
        """Test checking if service is supported."""
        assert (
            MetadataProviderFactory.is_service_supported(streaming_source)
            == expected_supported
        )

    def test_register_provider(self):
        """Test registering a new provider."""

        class CustomProvider(BaseMetadataProvider):
            @property
            def service_name(self) -> str:
                return "Custom"

            @property
            def streaming_source(self) -> StreamingSource:
                return StreamingSource.SPOTIFY

            async def authenticate(self) -> bool:
                return True

            async def fetch_artist_metadata(self, artist_id: str):
                raise NotImplementedError

            async def fetch_album_metadata(self, album_id: str):
                raise NotImplementedError

            async def fetch_track_metadata(self, track_id: str):
                raise NotImplementedError

            async def fetch_playlist_metadata(self, playlist_id: str):
                raise NotImplementedError

            async def cleanup(self) -> None:
                pass

        # Register the custom provider
        MetadataProviderFactory.register_provider(
            StreamingSource.SPOTIFY, CustomProvider
        )

        # Test that it's now supported
        assert MetadataProviderFactory.is_service_supported(StreamingSource.SPOTIFY)

        # Test creating the custom provider
        provider = MetadataProviderFactory.create_provider(StreamingSource.SPOTIFY)
        assert isinstance(provider, CustomProvider)

    def test_register_invalid_provider(self):
        """Test registering an invalid provider class."""

        class InvalidProvider:
            pass

        with pytest.raises(
            TypeError, match="Provider class must inherit from BaseMetadataProvider"
        ):
            MetadataProviderFactory.register_provider(
                StreamingSource.APPLE_MUSIC,
                InvalidProvider,  # type: ignore
            )
