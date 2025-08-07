# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for artist progress functionality in MetadataService."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ripstream.config.user import UserConfig
from ripstream.core.url_parser import ParsedURL
from ripstream.downloader.enums import ContentType
from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_service import MetadataService


class TestMetadataServiceArtistProgress:
    """Test the artist progress functionality in MetadataService."""

    @pytest.fixture
    def sample_config(self):
        """Create sample UserConfig for testing."""
        return UserConfig()

    @pytest.fixture
    def metadata_service(self, sample_config):
        """Create MetadataService instance."""
        return MetadataService(sample_config)

    @pytest.fixture
    def artist_parsed_url(self):
        """Create ParsedURL for artist content."""
        return ParsedURL(
            service=StreamingSource.QOBUZ,
            content_type=ContentType.ARTIST,
            content_id="artist_123",
            url="https://open.qobuz.com/artist/artist_123",
            metadata={"name": "Test Artist"},
        )

    @pytest.fixture
    def mock_metadata_fetcher(self):
        """Create mock MetadataFetcher."""
        fetcher = Mock()
        fetcher.metadata_fetched = Mock()
        fetcher.album_fetched = Mock()
        fetcher.artwork_fetched = Mock()
        fetcher.progress_updated = Mock()
        fetcher.artist_progress_updated = Mock()
        fetcher.error_occurred = Mock()
        fetcher.start = Mock()
        fetcher.isRunning = Mock(return_value=False)
        fetcher.terminate = Mock()
        fetcher.wait = Mock()
        # Add async method to prevent warnings
        fetcher._fetch_metadata = AsyncMock()
        return fetcher

    def test_artist_progress_signal_exists(self, metadata_service):
        """Test that artist_progress_updated signal exists."""
        assert hasattr(metadata_service, "artist_progress_updated")
        signal = metadata_service.artist_progress_updated
        assert signal is not None

    def test_signal_connections_include_artist_progress(
        self, metadata_service, artist_parsed_url, mock_metadata_fetcher
    ):
        """Test that artist_progress_updated signal is connected when fetching metadata."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher",
            return_value=mock_metadata_fetcher,
        ):
            # Fetch metadata to trigger signal connections
            metadata_service.fetch_metadata(artist_parsed_url)

            # Verify all signals are connected
            mock_metadata_fetcher.metadata_fetched.connect.assert_called_once()
            mock_metadata_fetcher.album_fetched.connect.assert_called_once()
            mock_metadata_fetcher.artwork_fetched.connect.assert_called_once()
            mock_metadata_fetcher.progress_updated.connect.assert_called_once()
            mock_metadata_fetcher.artist_progress_updated.connect.assert_called_once()
            mock_metadata_fetcher.error_occurred.connect.assert_called_once()

    def test_artist_progress_signal_forwarding(self, metadata_service):
        """Test that artist_progress_updated signal forwards correctly."""
        # Mock the signal emission tracking
        emissions = []

        def track_emission(remaining, total, service):
            emissions.append((remaining, total, service))

        metadata_service.artist_progress_updated.connect(track_emission)

        # Emit the signal
        metadata_service.artist_progress_updated.emit(5, 10, "Qobuz")

        # Check that the signal was forwarded
        assert len(emissions) == 1
        assert emissions[0] == (5, 10, "Qobuz")

    @pytest.mark.parametrize(
        ("remaining", "total", "service"),
        [
            (0, 5, "Qobuz"),
            (3, 10, "Tidal"),
            (1, 1, "Deezer"),
            (15, 20, "YouTube"),
        ],
    )
    def test_artist_progress_signal_parameters(
        self, metadata_service, remaining, total, service
    ):
        """Test artist_progress_updated signal with various parameters."""
        emissions = []

        def track_emission(r, t, s):
            emissions.append((r, t, s))

        metadata_service.artist_progress_updated.connect(track_emission)
        metadata_service.artist_progress_updated.emit(remaining, total, service)

        assert len(emissions) == 1
        assert emissions[0] == (remaining, total, service)

    def test_cleanup_with_running_fetcher(
        self, metadata_service, artist_parsed_url, mock_metadata_fetcher
    ):
        """Test cleanup when fetcher is running."""
        # Set up running fetcher
        mock_metadata_fetcher.isRunning.return_value = True

        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher",
            return_value=mock_metadata_fetcher,
        ):
            # Start fetching
            metadata_service.fetch_metadata(artist_parsed_url)

            # Cleanup
            metadata_service.cleanup()

            # Verify cleanup was called
            mock_metadata_fetcher.terminate.assert_called_once()
            mock_metadata_fetcher.wait.assert_called_once()

    def test_multiple_fetch_requests_cleanup_previous(
        self, metadata_service, artist_parsed_url
    ):
        """Test that multiple fetch requests properly cleanup previous fetchers."""
        mock_fetcher1 = Mock()
        mock_fetcher1.isRunning.return_value = True
        mock_fetcher1.terminate = Mock()
        mock_fetcher1.wait = Mock()
        mock_fetcher1.metadata_fetched = Mock()
        mock_fetcher1.album_fetched = Mock()
        mock_fetcher1.artwork_fetched = Mock()
        mock_fetcher1.progress_updated = Mock()
        mock_fetcher1.artist_progress_updated = Mock()
        mock_fetcher1.error_occurred = Mock()
        mock_fetcher1.start = Mock()
        mock_fetcher1._fetch_metadata = AsyncMock()

        mock_fetcher2 = Mock()
        mock_fetcher2.isRunning.return_value = False
        mock_fetcher2.metadata_fetched = Mock()
        mock_fetcher2.album_fetched = Mock()
        mock_fetcher2.artwork_fetched = Mock()
        mock_fetcher2.progress_updated = Mock()
        mock_fetcher2.artist_progress_updated = Mock()
        mock_fetcher2.error_occurred = Mock()
        mock_fetcher2.start = Mock()
        mock_fetcher2._fetch_metadata = AsyncMock()

        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher",
            side_effect=[mock_fetcher1, mock_fetcher2],
        ):
            # First fetch request
            metadata_service.fetch_metadata(artist_parsed_url)

            # Second fetch request should cleanup first
            metadata_service.fetch_metadata(artist_parsed_url)

            # Verify first fetcher was terminated
            mock_fetcher1.terminate.assert_called_once()
            mock_fetcher1.wait.assert_called_once()

            # Verify second fetcher was started
            mock_fetcher2.start.assert_called_once()

    def test_signal_connection_order(
        self, metadata_service, artist_parsed_url, mock_metadata_fetcher
    ):
        """Test that signals are connected in the correct order."""
        connection_order = []

        # Mock connect methods to track order
        def track_metadata_connect(slot):
            connection_order.append("metadata_fetched")

        def track_album_connect(slot):
            connection_order.append("album_fetched")

        def track_artwork_connect(slot):
            connection_order.append("artwork_fetched")

        def track_progress_connect(slot):
            connection_order.append("progress_updated")

        def track_artist_progress_connect(slot):
            connection_order.append("artist_progress_updated")

        def track_error_connect(slot):
            connection_order.append("error_occurred")

        mock_metadata_fetcher.metadata_fetched.connect.side_effect = (
            track_metadata_connect
        )
        mock_metadata_fetcher.album_fetched.connect.side_effect = track_album_connect
        mock_metadata_fetcher.artwork_fetched.connect.side_effect = (
            track_artwork_connect
        )
        mock_metadata_fetcher.progress_updated.connect.side_effect = (
            track_progress_connect
        )
        mock_metadata_fetcher.artist_progress_updated.connect.side_effect = (
            track_artist_progress_connect
        )
        mock_metadata_fetcher.error_occurred.connect.side_effect = track_error_connect

        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher",
            return_value=mock_metadata_fetcher,
        ):
            metadata_service.fetch_metadata(artist_parsed_url)

        # Verify connection order
        expected_order = [
            "metadata_fetched",
            "album_fetched",
            "artwork_fetched",
            "progress_updated",
            "artist_progress_updated",
            "error_occurred",
        ]
        assert connection_order == expected_order

    def test_artist_progress_signal_disconnection_on_cleanup(
        self, metadata_service, artist_parsed_url, mock_metadata_fetcher
    ):
        """Test that artist_progress_updated signal is properly handled during cleanup."""
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher",
            return_value=mock_metadata_fetcher,
        ):
            # Start fetching
            metadata_service.fetch_metadata(artist_parsed_url)

            # Verify fetcher is set
            assert metadata_service.current_fetcher == mock_metadata_fetcher

            # Cleanup
            metadata_service.cleanup()

            # Verify cleanup was called on the fetcher
            if mock_metadata_fetcher.isRunning.return_value:
                mock_metadata_fetcher.terminate.assert_called()
                mock_metadata_fetcher.wait.assert_called()

    def test_service_handles_artist_progress_emission_during_fetch(
        self, metadata_service, artist_parsed_url
    ):
        """Test that service properly handles artist progress emissions during active fetch."""
        # Track emissions
        progress_emissions = []

        def track_progress(remaining, total, service):
            progress_emissions.append((remaining, total, service))

        metadata_service.artist_progress_updated.connect(track_progress)

        # Create a fetcher that will emit progress signals
        mock_fetcher = Mock()
        mock_fetcher.metadata_fetched = Mock()
        mock_fetcher.album_fetched = Mock()
        mock_fetcher.artwork_fetched = Mock()
        mock_fetcher.progress_updated = Mock()
        mock_fetcher.error_occurred = Mock()
        mock_fetcher.start = Mock()
        mock_fetcher.isRunning = Mock(return_value=False)

        # Create a mock signal that can emit
        class MockSignal:
            def __init__(self):
                self.connected_slots = []

            def connect(self, slot):
                self.connected_slots.append(slot)

            def emit(self, *args):
                for slot in self.connected_slots:
                    slot(*args)

        mock_artist_progress_signal = MockSignal()
        mock_fetcher.artist_progress_updated = mock_artist_progress_signal

        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher", return_value=mock_fetcher
        ):
            # Start fetching
            metadata_service.fetch_metadata(artist_parsed_url)

            # Simulate progress emissions from fetcher
            mock_artist_progress_signal.emit(3, 5, "Qobuz")
            mock_artist_progress_signal.emit(2, 5, "Qobuz")
            mock_artist_progress_signal.emit(1, 5, "Qobuz")
            mock_artist_progress_signal.emit(0, 5, "Qobuz")

        # Verify all progress emissions were forwarded
        assert len(progress_emissions) == 4
        assert progress_emissions[0] == (3, 5, "Qobuz")
        assert progress_emissions[1] == (2, 5, "Qobuz")
        assert progress_emissions[2] == (1, 5, "Qobuz")
        assert progress_emissions[3] == (0, 5, "Qobuz")
