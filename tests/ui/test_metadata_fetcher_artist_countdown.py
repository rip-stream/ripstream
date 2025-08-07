# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for artist countdown functionality in MetadataFetcher."""

import threading
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ripstream.core.url_parser import ParsedURL
from ripstream.downloader.enums import ContentType
from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_fetcher import MetadataFetcher


class TestMetadataFetcherArtistCountdown:
    """Test the artist countdown functionality in MetadataFetcher."""

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
    def album_parsed_url(self):
        """Create ParsedURL for album content."""
        return ParsedURL(
            service=StreamingSource.QOBUZ,
            content_type=ContentType.ALBUM,
            content_id="album_123",
            url="https://open.qobuz.com/album/album_123",
            metadata={"title": "Test Album"},
        )

    @pytest.fixture
    def mock_credentials(self):
        """Mock credentials for testing."""
        return {"username": "test", "password": "test"}

    @pytest.fixture
    def sample_album_metadata(self):
        """Sample album metadata for testing."""
        return {
            "content_type": "album",
            "service": "Qobuz",
            "album_info": {
                "id": "album_123",
                "title": "Test Album",
                "artist": "Test Artist",
            },
            "items": [{"id": "track_1", "title": "Track 1"}],
        }

    @pytest.fixture
    def sample_artist_metadata(self):
        """Sample artist metadata for testing."""
        return {
            "content_type": "artist",
            "service": "Qobuz",
            "artist_info": {
                "id": "artist_123",
                "name": "Test Artist",
                "total_items": 3,
                "remaining_items": 3,
            },
            "items": [],
            "album_ids": ["album_1", "album_2", "album_3"],
        }

    @pytest.fixture
    def metadata_fetcher_artist(self, artist_parsed_url, mock_credentials):
        """Create MetadataFetcher for artist content."""
        return MetadataFetcher(artist_parsed_url, mock_credentials)

    @pytest.fixture
    def metadata_fetcher_album(self, album_parsed_url, mock_credentials):
        """Create MetadataFetcher for album content."""
        return MetadataFetcher(album_parsed_url, mock_credentials)

    def test_initialization_with_artist_counter_defaults(self, metadata_fetcher_artist):
        """Test that artist counter is initialized with default values."""
        assert metadata_fetcher_artist._remaining_items == 0
        assert metadata_fetcher_artist._total_items == 0
        assert metadata_fetcher_artist._service_name == ""
        assert hasattr(metadata_fetcher_artist._remaining_items_lock, "acquire")
        assert hasattr(metadata_fetcher_artist._remaining_items_lock, "release")

    def test_initialization_with_album_counter_defaults(self, metadata_fetcher_album):
        """Test that album fetcher also has counter defaults."""
        assert metadata_fetcher_album._remaining_items == 0
        assert metadata_fetcher_album._total_items == 0
        assert metadata_fetcher_album._service_name == ""
        assert hasattr(metadata_fetcher_album._remaining_items_lock, "acquire")
        assert hasattr(metadata_fetcher_album._remaining_items_lock, "release")

    def test_artist_progress_signal_exists(self, metadata_fetcher_artist):
        """Test that artist_progress_updated signal exists."""
        assert hasattr(metadata_fetcher_artist, "artist_progress_updated")
        # Signal should have the correct signature: int, int, str
        signal = metadata_fetcher_artist.artist_progress_updated
        assert signal is not None

    @pytest.mark.parametrize(
        ("total_items", "service_name"),
        [
            (5, "Qobuz"),
            (10, "Tidal"),
            (1, "Deezer"),
            (0, "YouTube"),
        ],
    )
    def test_initialize_artist_counter(
        self, metadata_fetcher_artist, total_items, service_name
    ):
        """Test _initialize_artist_counter with various parameters."""
        metadata_fetcher_artist._initialize_artist_counter(total_items, service_name)

        assert metadata_fetcher_artist._remaining_items == total_items
        assert metadata_fetcher_artist._total_items == total_items
        assert metadata_fetcher_artist._service_name == service_name

    def test_initialize_artist_counter_thread_safety(self, metadata_fetcher_artist):
        """Test that _initialize_artist_counter is thread-safe."""
        results = []

        def init_counter(total, service):
            metadata_fetcher_artist._initialize_artist_counter(total, service)
            results.append((
                metadata_fetcher_artist._remaining_items,
                metadata_fetcher_artist._total_items,
                metadata_fetcher_artist._service_name,
            ))

        # Create multiple threads trying to initialize simultaneously
        threads = []
        for i in range(5):
            thread = threading.Thread(target=init_counter, args=(i + 1, f"Service{i}"))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have 5 results, and the final state should be consistent
        assert len(results) == 5
        final_remaining = metadata_fetcher_artist._remaining_items
        final_total = metadata_fetcher_artist._total_items
        final_service = metadata_fetcher_artist._service_name

        # Final state should match one of the initialization calls
        assert final_remaining == final_total
        assert final_service.startswith("Service")

    def test_decrement_remaining_items_with_items(self, metadata_fetcher_artist):
        """Test _decrement_remaining_items when items remain."""
        # Initialize counter
        metadata_fetcher_artist._initialize_artist_counter(3, "Qobuz")

        # Mock the signal
        signal_mock = Mock()
        metadata_fetcher_artist.artist_progress_updated = signal_mock

        # Decrement
        metadata_fetcher_artist._decrement_remaining_items()

        # Check state
        assert metadata_fetcher_artist._remaining_items == 2
        assert metadata_fetcher_artist._total_items == 3
        assert metadata_fetcher_artist._service_name == "Qobuz"

        # Check signal emission
        signal_mock.emit.assert_called_once_with(2, 3, "Qobuz")

    def test_decrement_remaining_items_to_zero(self, metadata_fetcher_artist):
        """Test _decrement_remaining_items when reaching zero."""
        # Initialize counter with 1 item
        metadata_fetcher_artist._initialize_artist_counter(1, "Qobuz")

        # Mock the signal
        signal_mock = Mock()
        metadata_fetcher_artist.artist_progress_updated = signal_mock

        # Decrement
        metadata_fetcher_artist._decrement_remaining_items()

        # Check state
        assert metadata_fetcher_artist._remaining_items == 0
        assert metadata_fetcher_artist._total_items == 1

        # Check signal emission
        signal_mock.emit.assert_called_once_with(0, 1, "Qobuz")

    def test_decrement_remaining_items_when_zero(self, metadata_fetcher_artist):
        """Test _decrement_remaining_items when already at zero."""
        # Initialize counter with 0 items
        metadata_fetcher_artist._initialize_artist_counter(0, "Qobuz")

        # Mock the signal
        signal_mock = Mock()
        metadata_fetcher_artist.artist_progress_updated = signal_mock

        # Decrement
        metadata_fetcher_artist._decrement_remaining_items()

        # Check state (should remain 0)
        assert metadata_fetcher_artist._remaining_items == 0
        assert metadata_fetcher_artist._total_items == 0

        # Signal should not be emitted
        signal_mock.emit.assert_not_called()

    def test_decrement_remaining_items_thread_safety(self, metadata_fetcher_artist):
        """Test that _decrement_remaining_items is thread-safe."""
        # Initialize with 10 items
        metadata_fetcher_artist._initialize_artist_counter(10, "Qobuz")

        # Mock the signal to track emissions
        emissions = []

        def track_emission(remaining, total, service):
            emissions.append((remaining, total, service))

        signal_mock = Mock()
        signal_mock.emit.side_effect = track_emission
        metadata_fetcher_artist.artist_progress_updated = signal_mock

        # Create multiple threads to decrement simultaneously
        threads = []
        for _ in range(10):
            thread = threading.Thread(
                target=metadata_fetcher_artist._decrement_remaining_items
            )
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Final state should be 0
        assert metadata_fetcher_artist._remaining_items == 0
        assert metadata_fetcher_artist._total_items == 10

        # Should have exactly 10 emissions (one per decrement)
        assert len(emissions) == 10

        # Emissions should show decreasing remaining counts
        remaining_counts = [emission[0] for emission in emissions]
        assert set(remaining_counts) == set(range(10))

    def test_on_album_fetched_artist_content(
        self, metadata_fetcher_artist, sample_album_metadata
    ):
        """Test _on_album_fetched for artist content decrements counter."""
        # Initialize counter
        metadata_fetcher_artist._initialize_artist_counter(3, "Qobuz")

        # Mock signals
        album_signal_mock = Mock()
        progress_signal_mock = Mock()
        metadata_fetcher_artist.album_fetched = album_signal_mock
        metadata_fetcher_artist.artist_progress_updated = progress_signal_mock

        # Mock async task creation and artwork method
        with (
            patch("asyncio.get_running_loop") as mock_get_loop,
            patch.object(
                metadata_fetcher_artist,
                "_fetch_album_artwork_async",
                new_callable=AsyncMock,
            ),
        ):
            # Mock a running event loop
            mock_loop = Mock()
            mock_task = Mock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop

            # Call _on_album_fetched
            metadata_fetcher_artist._on_album_fetched(sample_album_metadata)

        # Check that album_fetched signal was emitted
        album_signal_mock.emit.assert_called_once_with(sample_album_metadata)

        # Check that counter was decremented and progress signal emitted
        assert metadata_fetcher_artist._remaining_items == 2
        progress_signal_mock.emit.assert_called_once_with(2, 3, "Qobuz")

        # Check that artwork task was created
        mock_loop.create_task.assert_called_once()

    def test_on_album_fetched_album_content(
        self, metadata_fetcher_album, sample_album_metadata
    ):
        """Test _on_album_fetched for album content does not decrement counter."""
        # Initialize counter (should not be used for album content)
        metadata_fetcher_album._initialize_artist_counter(3, "Qobuz")

        # Mock signals
        album_signal_mock = Mock()
        progress_signal_mock = Mock()
        metadata_fetcher_album.album_fetched = album_signal_mock
        metadata_fetcher_album.artist_progress_updated = progress_signal_mock

        # Mock async task creation and artwork method
        with (
            patch("asyncio.get_running_loop") as mock_get_loop,
            patch.object(
                metadata_fetcher_album,
                "_fetch_album_artwork_async",
                new_callable=AsyncMock,
            ),
        ):
            # Mock a running event loop
            mock_loop = Mock()
            mock_task = Mock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop

            # Call _on_album_fetched
            metadata_fetcher_album._on_album_fetched(sample_album_metadata)

        # Check that album_fetched signal was emitted
        album_signal_mock.emit.assert_called_once_with(sample_album_metadata)

        # Check that counter was NOT decremented
        assert metadata_fetcher_album._remaining_items == 3  # Should remain unchanged
        progress_signal_mock.emit.assert_not_called()

        # Check that artwork task was still created
        mock_loop.create_task.assert_called_once()

    @pytest.mark.parametrize(
        ("content_type", "should_decrement"),
        [
            (ContentType.ARTIST, True),
            (ContentType.ALBUM, False),
            (ContentType.TRACK, False),
            (ContentType.PLAYLIST, False),
        ],
    )
    def test_on_album_fetched_content_type_behavior(
        self, mock_credentials, sample_album_metadata, content_type, should_decrement
    ):
        """Test _on_album_fetched behavior for different content types."""
        # Create ParsedURL with specific content type
        parsed_url = ParsedURL(
            service=StreamingSource.QOBUZ,
            content_type=content_type,
            content_id="test_123",
            url="https://example.com/test_123",
            metadata={"name": "Test"},
        )

        fetcher = MetadataFetcher(parsed_url, mock_credentials)

        # Initialize counter
        fetcher._initialize_artist_counter(5, "TestService")

        # Mock signals
        album_signal_mock = Mock()
        progress_signal_mock = Mock()
        fetcher.album_fetched = album_signal_mock
        fetcher.artist_progress_updated = progress_signal_mock

        # Mock async task creation and artwork method
        with (
            patch("asyncio.get_running_loop") as mock_get_loop,
            patch.object(fetcher, "_fetch_album_artwork_async", new_callable=AsyncMock),
        ):
            # Mock a running event loop
            mock_loop = Mock()
            mock_task = Mock()
            mock_loop.create_task.return_value = mock_task
            mock_get_loop.return_value = mock_loop

            # Call _on_album_fetched
            fetcher._on_album_fetched(sample_album_metadata)

        # Check album signal emission (should always happen)
        album_signal_mock.emit.assert_called_once_with(sample_album_metadata)

        # Check counter behavior based on content type
        if should_decrement:
            assert fetcher._remaining_items == 4  # Decremented
            progress_signal_mock.emit.assert_called_once_with(4, 5, "TestService")
        else:
            assert fetcher._remaining_items == 5  # Unchanged
            progress_signal_mock.emit.assert_not_called()
