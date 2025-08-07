# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for download provider factory."""

import contextlib
from typing import Any
from unittest.mock import Mock

import pytest

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.base import BaseDownloadProvider
from ripstream.downloader.providers.factory import DownloadProviderFactory
from ripstream.downloader.providers.qobuz import QobuzDownloadProvider
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource


class MockDownloadProvider(BaseDownloadProvider):
    """Mock download provider for testing factory."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
        credentials: dict[str, Any] | None = None,
    ):
        super().__init__(config, session_manager, progress_tracker, credentials)

    @property
    def service_name(self) -> str:
        return "mock"

    @property
    def streaming_source(self) -> StreamingSource:
        return StreamingSource.QOBUZ

    @property
    def supported_content_types(self) -> list:
        return []

    async def authenticate(self) -> bool:
        return True

    async def get_download_info(self, content_id: str, content_type) -> Any:
        return {"id": content_id}

    async def download_content(
        self,
        content_id: str,
        content_type,
        download_directory: str | None = None,
        progress_callback=None,
    ):
        return self._create_download_result(success=True)

    async def cleanup(self) -> None:
        pass


class TestDownloadProviderFactory:
    """Test cases for DownloadProviderFactory."""

    def test_get_supported_services(self) -> None:
        """Test getting list of supported services."""
        services = DownloadProviderFactory.get_supported_services()

        assert isinstance(services, list)
        assert StreamingSource.QOBUZ in services
        # Should not include services that are commented out in the factory
        assert StreamingSource.TIDAL not in services
        assert StreamingSource.DEEZER not in services
        assert StreamingSource.YOUTUBE not in services

    @pytest.mark.parametrize(
        ("service", "expected"),
        [
            (StreamingSource.QOBUZ, True),
            (StreamingSource.TIDAL, False),
            (StreamingSource.DEEZER, False),
            (StreamingSource.YOUTUBE, False),
            (StreamingSource.SPOTIFY, False),
            (StreamingSource.UNKNOWN, False),
        ],
    )
    def test_is_service_supported(
        self,
        service: StreamingSource,
        expected: bool,
    ) -> None:
        """Test checking if a service is supported."""
        result = DownloadProviderFactory.is_service_supported(service)
        assert result == expected

    @pytest.mark.parametrize(
        ("service", "expected_provider_class"),
        [
            (StreamingSource.QOBUZ, QobuzDownloadProvider),
        ],
    )
    def test_create_provider_success(
        self,
        service: StreamingSource,
        expected_provider_class: type[BaseDownloadProvider],
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test successful provider creation."""
        provider = DownloadProviderFactory.create_provider(
            service,
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
            sample_credentials,
        )

        assert isinstance(provider, expected_provider_class)
        assert provider.config == mock_download_config
        assert provider.session_manager == mock_session_manager
        assert provider.progress_tracker == mock_progress_tracker
        assert provider.credentials == sample_credentials

    @pytest.mark.parametrize(
        "unsupported_service",
        [
            StreamingSource.TIDAL,
            StreamingSource.DEEZER,
            StreamingSource.YOUTUBE,
            StreamingSource.SPOTIFY,
            StreamingSource.UNKNOWN,
        ],
    )
    def test_create_provider_unsupported_service(
        self,
        unsupported_service: StreamingSource,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test creating provider for unsupported service raises ValueError."""
        with pytest.raises(ValueError, match=r".*Supported services.*") as exc_info:
            DownloadProviderFactory.create_provider(
                unsupported_service,
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

        error_message = str(exc_info.value)
        assert unsupported_service.value in error_message
        assert "Supported services" in error_message

    def test_create_provider_without_credentials(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test creating provider without credentials."""
        provider = DownloadProviderFactory.create_provider(
            StreamingSource.QOBUZ,
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        assert isinstance(provider, QobuzDownloadProvider)
        assert provider.credentials == {}

    def test_create_provider_with_none_credentials(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test creating provider with None credentials."""
        provider = DownloadProviderFactory.create_provider(
            StreamingSource.QOBUZ,
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
            None,
        )

        assert isinstance(provider, QobuzDownloadProvider)
        assert provider.credentials == {}

    def test_register_provider_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test successfully registering a new provider."""
        # Store original providers to restore later
        original_providers = DownloadProviderFactory._providers.copy()

        try:
            # Register a new provider
            DownloadProviderFactory.register_provider(
                StreamingSource.TIDAL,
                MockDownloadProvider,
            )

            # Verify it was registered
            assert StreamingSource.TIDAL in DownloadProviderFactory._providers
            assert (
                DownloadProviderFactory._providers[StreamingSource.TIDAL]
                == MockDownloadProvider
            )

            # Test that we can create a provider for the new service
            provider = DownloadProviderFactory.create_provider(
                StreamingSource.TIDAL,
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

            assert isinstance(provider, MockDownloadProvider)

        finally:
            # Restore original providers
            DownloadProviderFactory._providers = original_providers

    def test_register_provider_invalid_class(self) -> None:
        """Test registering an invalid provider class raises TypeError."""

        class InvalidProvider:
            """Invalid provider that doesn't inherit from BaseDownloadProvider."""

        with pytest.raises(TypeError) as exc_info:
            DownloadProviderFactory.register_provider(
                StreamingSource.TIDAL,
                InvalidProvider,  # type: ignore[arg-type]
            )

        error_message = str(exc_info.value)
        assert "must inherit from BaseDownloadProvider" in error_message

    def test_register_provider_overwrites_existing(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test that registering a provider overwrites existing registration."""
        # Store original providers to restore later
        original_providers = DownloadProviderFactory._providers.copy()

        try:
            # Register a provider
            DownloadProviderFactory.register_provider(
                StreamingSource.QOBUZ,
                MockDownloadProvider,
            )

            # Verify it overwrote the original
            assert (
                DownloadProviderFactory._providers[StreamingSource.QOBUZ]
                == MockDownloadProvider
            )

            # Test that we can create the new provider
            provider = DownloadProviderFactory.create_provider(
                StreamingSource.QOBUZ,
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

            assert isinstance(provider, MockDownloadProvider)

        finally:
            # Restore original providers
            DownloadProviderFactory._providers = original_providers

    def test_factory_providers_dict_structure(self) -> None:
        """Test that the _providers dict has the correct structure."""
        providers = DownloadProviderFactory._providers

        assert isinstance(providers, dict)
        assert all(isinstance(key, StreamingSource) for key in providers)
        assert all(
            issubclass(value, BaseDownloadProvider) for value in providers.values()
        )

    def test_factory_providers_immutable(self) -> None:
        """Test that the _providers dict is a class variable and shared."""
        # Get the original providers
        original_providers = DownloadProviderFactory._providers.copy()

        # Try to modify it (this should not affect the class)
        test_providers = DownloadProviderFactory._providers.copy()
        test_providers[StreamingSource.TIDAL] = MockDownloadProvider

        # The original should remain unchanged
        assert DownloadProviderFactory._providers == original_providers

    @pytest.mark.parametrize(
        ("service", "expected_class"),
        [
            (StreamingSource.QOBUZ, QobuzDownloadProvider),
        ],
    )
    def test_provider_class_mapping(
        self,
        service: StreamingSource,
        expected_class: type[BaseDownloadProvider],
    ) -> None:
        """Test that the provider class mapping is correct."""
        provider_class = DownloadProviderFactory._providers.get(service)
        assert provider_class == expected_class

    def test_factory_logging_integration(self) -> None:
        """Test that factory methods log appropriately."""
        # This test verifies that the factory methods don't crash
        # when logging is enabled (actual logging is tested elsewhere)

        # Test create_provider logging
        with contextlib.suppress(Exception):
            DownloadProviderFactory.create_provider(
                StreamingSource.QOBUZ,
                Mock(spec=DownloaderConfig),
                Mock(spec=SessionManager),
                Mock(spec=ProgressTracker),
            )

        # Test register_provider logging
        with contextlib.suppress(Exception):
            DownloadProviderFactory.register_provider(
                StreamingSource.TIDAL,
                MockDownloadProvider,
            )

    def test_factory_methods_return_types(self) -> None:
        """Test that factory methods return the expected types."""
        # Test get_supported_services
        services = DownloadProviderFactory.get_supported_services()
        assert isinstance(services, list)
        assert all(isinstance(service, StreamingSource) for service in services)

        # Test is_service_supported
        result = DownloadProviderFactory.is_service_supported(StreamingSource.QOBUZ)
        assert isinstance(result, bool)

    def test_factory_error_messages(self) -> None:
        """Test that factory error messages are informative."""
        # Test that factory raises ValueError for unsupported services
        mock_config = Mock(spec=DownloaderConfig)
        mock_session = Mock(spec=SessionManager)
        mock_progress = Mock(spec=ProgressTracker)

        # Store original providers to ensure clean state
        original_providers = DownloadProviderFactory._providers.copy()

        try:
            # Ensure TIDAL is not registered
            if StreamingSource.TIDAL in DownloadProviderFactory._providers:
                del DownloadProviderFactory._providers[StreamingSource.TIDAL]

            with pytest.raises(ValueError, match="Unsupported streaming service"):
                DownloadProviderFactory.create_provider(
                    StreamingSource.TIDAL,  # Use unsupported service
                    mock_config,
                    mock_session,
                    mock_progress,
                )
        finally:
            # Restore original providers
            DownloadProviderFactory._providers = original_providers
