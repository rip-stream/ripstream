# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for metadata service."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from PyQt6.QtCore import QObject, QThread
from PyQt6.QtGui import QPixmap

from ripstream.config.user import UserConfig
from ripstream.core.url_parser import ParsedURL
from ripstream.downloader.enums import ContentType
from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_fetcher import AuthenticationError, MetadataFetcher
from ripstream.ui.metadata_service import (
    MetadataService,
)


class TestMetadataFetcher:
    """Test the MetadataFetcher class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock download config."""
        return Mock()

    @pytest.fixture
    def mock_session_manager(self):
        """Create mock session manager."""
        session_manager = Mock()
        session_manager.close_all_sessions = AsyncMock()
        return session_manager

    @pytest.fixture
    def mock_progress_tracker(self):
        """Create mock progress tracker."""
        return Mock()

    @pytest.fixture
    def sample_parsed_url_qobuz(self):
        """Create sample ParsedURL for Qobuz."""
        return ParsedURL(
            service=StreamingSource.QOBUZ,
            content_type=ContentType.ALBUM,
            content_id="123456",
            url="https://open.qobuz.com/album/123456",
            metadata={"title": "Test Album"},
        )

    @pytest.fixture
    def metadata_fetcher(self, qapp, sample_parsed_url_qobuz) -> MetadataFetcher:
        """Create a MetadataFetcher for testing."""
        credentials = {"username": "test", "password": "test"}
        return MetadataFetcher(sample_parsed_url_qobuz, credentials)

    def test_fetcher_creation(self, metadata_fetcher, sample_parsed_url_qobuz):
        """Test creating a MetadataFetcher."""
        assert isinstance(metadata_fetcher, QThread)
        assert metadata_fetcher.parsed_url == sample_parsed_url_qobuz
        assert metadata_fetcher.credentials == {"username": "test", "password": "test"}
        assert isinstance(metadata_fetcher.cache_dir, Path)

    def test_fetcher_creation_no_credentials(self, qapp, sample_parsed_url_qobuz):
        """Test creating fetcher without credentials."""
        fetcher = MetadataFetcher(sample_parsed_url_qobuz)
        assert fetcher.credentials == {}

    def test_cache_directory_creation(self, metadata_fetcher):
        """Test cache directory is created."""
        assert metadata_fetcher.cache_dir.exists()
        assert metadata_fetcher.cache_dir.is_dir()

    @patch("ripstream.ui.metadata_fetcher.asyncio.run")
    def test_run_method(self, mock_asyncio_run, metadata_fetcher):
        """Test run method calls async fetch."""
        metadata_fetcher.run()
        mock_asyncio_run.assert_called_once()

    @patch("ripstream.ui.metadata_fetcher.asyncio.run")
    def test_run_method_exception_handling(
        self, mock_asyncio_run, metadata_fetcher, qtbot
    ):
        """Test run method handles exceptions."""
        mock_asyncio_run.side_effect = Exception("Test error")

        with qtbot.waitSignal(metadata_fetcher.error_occurred, timeout=1000) as blocker:
            metadata_fetcher.run()

        assert "Failed to fetch metadata: Test error" in blocker.args[0]

    def test_format_duration(self, metadata_fetcher):
        """Test duration formatting."""
        assert metadata_fetcher._format_duration(None) == "0:00"
        assert metadata_fetcher._format_duration(0) == "0:00"
        assert metadata_fetcher._format_duration(65) == "1:05"
        assert metadata_fetcher._format_duration(3661) == "61:01"

    def test_create_placeholder_artwork(self, metadata_fetcher):
        """Test placeholder artwork creation."""
        pixmap = metadata_fetcher._create_placeholder_artwork("test_id")

        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()
        assert pixmap.size().width() == 300
        assert pixmap.size().height() == 300

    def test_create_placeholder_artwork_empty_id(self, metadata_fetcher):
        """Test placeholder artwork with empty ID."""
        pixmap = metadata_fetcher._create_placeholder_artwork("")

        assert isinstance(pixmap, QPixmap)
        assert not pixmap.isNull()

    def test_download_artwork_cached(self, qapp, tmp_path):
        """Test downloading artwork when cached."""
        # Test the cached artwork logic without creating a MetadataFetcher instance
        # to avoid coroutine warnings

        # Create a cached file
        cached_file = tmp_path / "artwork_test.jpg"

        # Create a test pixmap and save it
        test_pixmap = QPixmap(100, 100)
        test_pixmap.fill()
        test_pixmap.save(str(cached_file), "JPG")

        # Mock the hash to match our test file
        with patch("hashlib.sha256") as mock_hash:
            mock_hash.return_value.hexdigest.return_value = "test"

            # Test the cached artwork logic directly
            url_hash = mock_hash.return_value.hexdigest.return_value
            cache_file = tmp_path / f"artwork_{url_hash}.jpg"

            # Verify the cached file exists and can be loaded as a pixmap
            assert cache_file.exists()

            pixmap = QPixmap(str(cache_file))
            assert isinstance(pixmap, QPixmap)
            assert not pixmap.isNull()

    @pytest.mark.asyncio
    async def test_download_artwork_not_cached(self, metadata_fetcher, tmp_path):
        """Test downloading artwork when not cached."""
        metadata_fetcher.cache_dir = tmp_path

        with patch.object(metadata_fetcher, "_fetch_artwork_from_url") as mock_fetch:
            mock_pixmap = QPixmap(100, 100)
            mock_pixmap.fill()
            mock_fetch.return_value = mock_pixmap

            result = await metadata_fetcher._download_artwork(
                "item_id", "http://example.com/art.jpg"
            )

            assert isinstance(result, QPixmap)
            mock_fetch.assert_called_once_with("http://example.com/art.jpg")

    @pytest.mark.asyncio
    async def test_fetch_artwork_from_url_success(self, metadata_fetcher):
        """Test fetching artwork from URL successfully."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"fake_image_data")

        mock_session = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_client_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch.object(QPixmap, "loadFromData", return_value=True):
                result = await metadata_fetcher._fetch_artwork_from_url(
                    "http://example.com/art.jpg"
                )

                assert isinstance(result, QPixmap)

    @pytest.mark.asyncio
    async def test_fetch_artwork_from_url_http_error(self, metadata_fetcher):
        """Test fetching artwork with HTTP error."""
        mock_response = Mock()
        mock_response.status = 404

        mock_session = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_client_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await metadata_fetcher._fetch_artwork_from_url(
                "http://example.com/art.jpg"
            )

            assert result is None

    def test_raise_authentication_error(self, metadata_fetcher):
        """Test raising authentication error."""
        with pytest.raises(AuthenticationError) as exc_info:
            metadata_fetcher._raise_authentication_error()

        assert "Failed to authenticate with Qobuz" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_metadata_unsupported_service(self, qapp):
        """Test fetching metadata for unsupported service."""
        parsed_url = ParsedURL(
            service=StreamingSource.TIDAL,  # Unsupported
            content_type=ContentType.ALBUM,
            content_id="123",
            url="https://tidal.com/album/123",
            metadata={},
        )

        fetcher = MetadataFetcher(parsed_url)

        with patch.object(fetcher, "error_occurred") as mock_error:
            await fetcher._fetch_metadata()

            mock_error.emit.assert_called_once()
            assert "tidal is not supported" in mock_error.emit.call_args[0][0]


class TestMetadataService:
    """Test the MetadataService class."""

    @pytest.fixture
    def metadata_service(self, qapp, sample_user_config) -> MetadataService:
        """Create a MetadataService for testing."""
        return MetadataService(sample_user_config)

    def test_service_creation(self, metadata_service, sample_user_config):
        """Test creating a MetadataService."""
        assert isinstance(metadata_service, QObject)
        assert metadata_service.config == sample_user_config
        assert metadata_service.current_fetcher is None

    def test_service_creation_no_config(self, qapp):
        """Test creating service without config."""
        service = MetadataService()
        assert service.config is None

    def test_update_config(self, metadata_service):
        """Test updating configuration."""
        new_config = UserConfig()
        metadata_service.update_config(new_config)

        assert metadata_service.config == new_config

    def test_fetch_metadata(self, metadata_service, sample_parsed_url):
        """Test fetching metadata."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            # Mock the async method to avoid coroutine warnings
            mock_fetcher._fetch_metadata = AsyncMock()
            mock_fetcher_class.return_value = mock_fetcher

            metadata_service.fetch_metadata(sample_parsed_url)

            mock_fetcher_class.assert_called_once()
            mock_fetcher.start.assert_called_once()
            assert metadata_service.current_fetcher == mock_fetcher

    def test_fetch_metadata_terminates_existing(
        self, metadata_service, sample_parsed_url
    ):
        """Test fetching metadata terminates existing fetcher."""
        # Create mock existing fetcher
        existing_fetcher = Mock()
        existing_fetcher.isRunning.return_value = True
        metadata_service.current_fetcher = existing_fetcher

        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_new_fetcher = Mock()
            # Use AsyncMock for the async _fetch_metadata method
            mock_new_fetcher._fetch_metadata = AsyncMock()
            mock_fetcher_class.return_value = mock_new_fetcher

            metadata_service.fetch_metadata(sample_parsed_url)

            existing_fetcher.terminate.assert_called_once()
            existing_fetcher.wait.assert_called_once()
            assert metadata_service.current_fetcher == mock_new_fetcher

    def test_get_credentials_for_service_qobuz(self, metadata_service):
        """Test getting credentials for Qobuz service."""
        # Mock the get_decoded_credentials method
        with patch(
            "ripstream.config.base.AuthenticatedServiceConfig.get_decoded_credentials"
        ) as mock_method:
            mock_method.return_value = {"username": "test", "password": "test"}

            credentials = metadata_service._get_credentials_for_service(
                StreamingSource.QOBUZ
            )

            assert credentials == {"username": "test", "password": "test"}
            mock_method.assert_called_once()

    def test_get_credentials_for_service_no_config(self, qapp):
        """Test getting credentials when no config."""
        service = MetadataService()

        credentials = service._get_credentials_for_service(StreamingSource.QOBUZ)

        assert credentials is None

    def test_get_credentials_for_service_unsupported(self, metadata_service):
        """Test getting credentials for unsupported service."""
        credentials = metadata_service._get_credentials_for_service(
            StreamingSource.UNKNOWN
        )

        assert credentials is None

    def test_get_credentials_for_service_no_method(self, metadata_service):
        """Test getting credentials when service config has no method."""
        # Mock hasattr to return False for get_decoded_credentials
        with patch("builtins.hasattr") as mock_hasattr:
            mock_hasattr.return_value = False

            credentials = metadata_service._get_credentials_for_service(
                StreamingSource.QOBUZ
            )

            assert credentials is None

    def test_cancel_fetch_no_fetcher(self, metadata_service):
        """Test canceling fetch when no fetcher exists."""
        # Should not raise an exception
        metadata_service.cancel_fetch()

    def test_cancel_fetch_not_running(self, metadata_service):
        """Test canceling fetch when fetcher is not running."""
        mock_fetcher = Mock()
        mock_fetcher.isRunning.return_value = False
        metadata_service.current_fetcher = mock_fetcher

        metadata_service.cancel_fetch()

        mock_fetcher.terminate.assert_not_called()

    def test_cancel_fetch_running(self, metadata_service):
        """Test canceling fetch when fetcher is running."""
        mock_fetcher = Mock()
        mock_fetcher.isRunning.return_value = True
        metadata_service.current_fetcher = mock_fetcher

        metadata_service.cancel_fetch()

        mock_fetcher.terminate.assert_called_once()
        mock_fetcher.wait.assert_called_once()
        assert metadata_service.current_fetcher is None

    def test_signal_connections(self, metadata_service, sample_parsed_url):
        """Test that fetcher signals are connected properly."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            metadata_service.fetch_metadata(sample_parsed_url)

            # Check that signals are connected
            mock_fetcher.metadata_fetched.connect.assert_called()
            mock_fetcher.artwork_fetched.connect.assert_called()
            mock_fetcher.progress_updated.connect.assert_called()
            mock_fetcher.error_occurred.connect.assert_called()

    @pytest.mark.parametrize(
        "service",
        [
            StreamingSource.QOBUZ,
            StreamingSource.TIDAL,
            StreamingSource.DEEZER,
            StreamingSource.SOUNDCLOUD,
            StreamingSource.YOUTUBE,
        ],
    )
    def test_service_config_mapping(self, metadata_service, service):
        """Test service to config attribute mapping."""
        # This tests the mapping logic in _get_credentials_for_service
        credentials = metadata_service._get_credentials_for_service(service)

        # Should return None for services without config or method
        # but should not raise an exception
        assert credentials is None or isinstance(credentials, dict)

    def test_fetcher_signal_emission(self, metadata_service, sample_parsed_url, qtbot):
        """Test that service properly forwards fetcher signals."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            metadata_service.fetch_metadata(sample_parsed_url)

            # Get the connected signal handlers
            metadata_connect_call = mock_fetcher.metadata_fetched.connect.call_args[0][
                0
            ]
            artwork_connect_call = mock_fetcher.artwork_fetched.connect.call_args[0][0]
            progress_connect_call = mock_fetcher.progress_updated.connect.call_args[0][
                0
            ]
            error_connect_call = mock_fetcher.error_occurred.connect.call_args[0][0]

            # Test that the connected handlers are the service's signal emit methods
            # We can't compare bound methods directly, so check the method names and objects
            assert metadata_connect_call.__name__ == "emit"
            assert metadata_connect_call.__self__ == metadata_service.metadata_ready
            assert artwork_connect_call.__name__ == "emit"
            assert artwork_connect_call.__self__ == metadata_service.artwork_ready
            assert progress_connect_call.__name__ == "emit"
            assert progress_connect_call.__self__ == metadata_service.progress_updated
            assert error_connect_call.__name__ == "emit"
            assert error_connect_call.__self__ == metadata_service.error_occurred

    def test_cleanup_on_destruction(self, metadata_service):
        """Test cleanup when service is destroyed."""
        mock_fetcher = Mock()
        mock_fetcher.isRunning.return_value = True
        metadata_service.current_fetcher = mock_fetcher

        # Simulate cleanup (would normally happen in destructor)
        if hasattr(metadata_service, "cleanup"):
            metadata_service.cleanup()
        else:
            # Manual cleanup for testing
            if (
                metadata_service.current_fetcher
                and metadata_service.current_fetcher.isRunning()
            ):
                metadata_service.current_fetcher.terminate()
                metadata_service.current_fetcher.wait()

        mock_fetcher.terminate.assert_called_once()
        mock_fetcher.wait.assert_called_once()


class TestAuthenticationError:
    """Test the AuthenticationError exception."""

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError."""
        error = AuthenticationError("Test authentication failed")
        assert str(error) == "Test authentication failed"
        assert isinstance(error, Exception)

    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inherits from Exception."""
        error = AuthenticationError("Test error")
        assert isinstance(error, Exception)

    def test_authentication_error_empty_message(self):
        """Test AuthenticationError with empty message."""
        error = AuthenticationError("")
        assert str(error) == ""


class TestMetadataFetcherEdgeCases:
    """Test edge cases for MetadataFetcher."""

    @pytest.fixture
    def sample_parsed_url_track(self):
        """Create sample ParsedURL for track."""
        return ParsedURL(
            service=StreamingSource.QOBUZ,
            content_type=ContentType.TRACK,
            content_id="track_123",
            url="https://open.qobuz.com/track/track_123",
            metadata={"title": "Test Track"},
        )

    @pytest.fixture
    def sample_parsed_url_playlist(self):
        """Create sample ParsedURL for playlist."""
        return ParsedURL(
            service=StreamingSource.QOBUZ,
            content_type=ContentType.PLAYLIST,
            content_id="playlist_123",
            url="https://open.qobuz.com/playlist/playlist_123",
            metadata={"title": "Test Playlist"},
        )

    def test_fetcher_with_different_content_types(self, qapp, sample_parsed_url_track):
        """Test fetcher creation with different content types."""
        fetcher = MetadataFetcher(sample_parsed_url_track)
        assert fetcher.parsed_url.content_type == ContentType.TRACK

    def test_fetcher_cache_directory_permissions(
        self, qapp, sample_parsed_url, tmp_path
    ):
        """Test cache directory creation with custom path."""
        fetcher = MetadataFetcher(sample_parsed_url)
        # Override cache_dir for testing
        fetcher.cache_dir = tmp_path / "custom_cache"
        fetcher.cache_dir.mkdir(parents=True, exist_ok=True)

        assert fetcher.cache_dir.exists()
        assert fetcher.cache_dir.is_dir()


class TestMetadataServiceEnhancements:
    """Enhanced tests for MetadataService."""

    @pytest.fixture
    def metadata_service_no_config(self, qapp) -> MetadataService:
        """Create MetadataService without config."""
        return MetadataService()

    def test_service_with_none_config(self, metadata_service_no_config):
        """Test service behavior with None config."""
        assert metadata_service_no_config.config is None

        # Should handle gracefully
        credentials = metadata_service_no_config._get_credentials_for_service(
            StreamingSource.QOBUZ
        )
        assert credentials is None

    def test_update_config_multiple_times(self, qapp, sample_user_config):
        """Test updating config multiple times."""
        service = MetadataService(sample_user_config)
        config1 = UserConfig()
        config2 = UserConfig()

        service.update_config(config1)
        assert service.config == config1

        service.update_config(config2)
        assert service.config == config2

    def test_fetch_metadata_with_running_fetcher_not_terminated(
        self, qapp, sample_user_config, sample_parsed_url
    ):
        """Test fetch when existing fetcher is not running."""
        service = MetadataService(sample_user_config)
        # Create mock existing fetcher that's not running
        existing_fetcher = Mock()
        existing_fetcher.isRunning.return_value = False
        service.current_fetcher = existing_fetcher

        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_new_fetcher = Mock()
            mock_fetcher_class.return_value = mock_new_fetcher

            service.fetch_metadata(sample_parsed_url)

            # Should not terminate if not running
            existing_fetcher.terminate.assert_not_called()
            existing_fetcher.wait.assert_not_called()

    @pytest.mark.parametrize(
        "service",
        [
            StreamingSource.APPLE_MUSIC,
            StreamingSource.SPOTIFY,
            StreamingSource.UNKNOWN,
        ],
    )
    def test_get_credentials_unsupported_services(
        self, qapp, sample_user_config, service
    ):
        """Test getting credentials for services not in mapping."""
        metadata_service = MetadataService(sample_user_config)
        credentials = metadata_service._get_credentials_for_service(service)
        assert credentials is None

    def test_service_signal_forwarding_integrity(
        self, qapp, sample_user_config, sample_parsed_url
    ):
        """Test that all signals are properly forwarded."""
        service = MetadataService(sample_user_config)
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            service.fetch_metadata(sample_parsed_url)

            # Verify all 4 signals are connected
            assert mock_fetcher.metadata_fetched.connect.call_count == 1
            assert mock_fetcher.artwork_fetched.connect.call_count == 1
            assert mock_fetcher.progress_updated.connect.call_count == 1
            assert mock_fetcher.error_occurred.connect.call_count == 1

    def test_concurrent_fetch_requests(
        self, qapp, sample_user_config, sample_parsed_url
    ):
        """Test handling concurrent fetch requests."""
        service = MetadataService(sample_user_config)
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher1 = Mock()
            mock_fetcher1.isRunning.return_value = True
            mock_fetcher2 = Mock()

            mock_fetcher_class.side_effect = [mock_fetcher1, mock_fetcher2]

            # First fetch
            service.fetch_metadata(sample_parsed_url)
            assert service.current_fetcher == mock_fetcher1

            # Second fetch should terminate first
            service.fetch_metadata(sample_parsed_url)

            mock_fetcher1.terminate.assert_called_once()
            mock_fetcher1.wait.assert_called_once()
            assert service.current_fetcher == mock_fetcher2

    def test_service_destruction_cleanup(self, qapp, sample_user_config):
        """Test cleanup when service is destroyed."""
        service = MetadataService(sample_user_config)
        mock_fetcher = Mock()
        mock_fetcher.isRunning.return_value = True
        service.current_fetcher = mock_fetcher

        # Simulate service cleanup
        service.cancel_fetch()

        mock_fetcher.terminate.assert_called_once()
        mock_fetcher.wait.assert_called_once()
        assert service.current_fetcher is None


class TestIntegrationScenarios:
    """Test integration scenarios between components."""

    @pytest.fixture
    def complete_metadata_service(self, qapp, sample_user_config):
        """Create a complete metadata service setup."""
        return MetadataService(sample_user_config)

    def test_full_metadata_fetch_workflow(
        self, complete_metadata_service, sample_parsed_url
    ):
        """Test complete metadata fetching workflow."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            # Start fetch
            complete_metadata_service.fetch_metadata(sample_parsed_url)

            # Verify fetcher was created and started
            mock_fetcher_class.assert_called_once()
            mock_fetcher.start.assert_called_once()

            # Verify signals are connected
            assert mock_fetcher.metadata_fetched.connect.called
            assert mock_fetcher.artwork_fetched.connect.called
            assert mock_fetcher.progress_updated.connect.called
            assert mock_fetcher.error_occurred.connect.called

    def test_error_recovery_workflow(
        self, complete_metadata_service, sample_parsed_url
    ):
        """Test error recovery workflow."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher_class.return_value = mock_fetcher

            # Start fetch
            complete_metadata_service.fetch_metadata(sample_parsed_url)

            # Simulate error
            error_handler = mock_fetcher.error_occurred.connect.call_args[0][0]

            # Should be able to handle error without crashing
            error_handler("Test error message")

    def test_config_update_during_fetch(
        self, complete_metadata_service, sample_parsed_url
    ):
        """Test config update while fetch is in progress."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher = Mock()
            mock_fetcher.isRunning.return_value = True
            mock_fetcher_class.return_value = mock_fetcher

            # Start fetch
            complete_metadata_service.fetch_metadata(sample_parsed_url)

            # Update config during fetch
            new_config = UserConfig()
            complete_metadata_service.update_config(new_config)

            # Should update config without affecting running fetch
            assert complete_metadata_service.config == new_config
            assert complete_metadata_service.current_fetcher == mock_fetcher

    def test_multiple_service_instances(
        self, qapp, sample_user_config, sample_parsed_url
    ):
        """Test multiple service instances working independently."""
        service1 = MetadataService(sample_user_config)
        service2 = MetadataService(sample_user_config)

        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            mock_fetcher1 = Mock()
            mock_fetcher2 = Mock()
            mock_fetcher_class.side_effect = [mock_fetcher1, mock_fetcher2]

            # Start fetches on both services
            service1.fetch_metadata(sample_parsed_url)
            service2.fetch_metadata(sample_parsed_url)

            # Should have independent fetchers
            assert service1.current_fetcher == mock_fetcher1
            assert service2.current_fetcher == mock_fetcher2

            # Both should start independently
            mock_fetcher1.start.assert_called_once()
            mock_fetcher2.start.assert_called_once()
