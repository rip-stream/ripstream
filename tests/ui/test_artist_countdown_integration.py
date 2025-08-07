# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Integration tests for artist countdown functionality."""

import asyncio
import threading
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ripstream.core.url_parser import ParsedURL
from ripstream.downloader.enums import ContentType
from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_fetcher import MetadataFetcher
from ripstream.ui.metadata_providers.qobuz import QobuzMetadataProvider
from ripstream.ui.metadata_service import MetadataService


class TestArtistCountdownIntegration:
    """Integration tests for the complete artist countdown flow."""

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
    def mock_credentials(self):
        """Mock credentials for testing."""
        return {"username": "test", "password": "test"}

    @pytest.fixture
    def mock_artist_model(self):
        """Mock artist model with multiple albums."""
        artist = Mock()
        artist.name = "Integration Test Artist"
        artist.info.biography = "Test biography for integration"
        artist.album_ids = [f"album_{i}" for i in range(1, 6)]  # 5 albums

        # Mock covers
        covers = Mock()
        thumbnail = Mock()
        thumbnail.url = "https://example.com/integration_thumbnail.jpg"
        covers.get_best_image.return_value = thumbnail
        artist.covers = covers

        return artist

    @pytest.fixture
    def mock_album_metadata_generator(self):
        """Generate mock album metadata for each album."""

        def generate_album_metadata(album_id):
            return {
                "content_type": "album",
                "service": "Qobuz",
                "album_info": {
                    "id": album_id,
                    "title": f"Album {album_id}",
                    "artist": "Integration Test Artist",
                },
                "items": [
                    {"id": f"{album_id}_track_1", "title": f"Track 1 from {album_id}"},
                    {"id": f"{album_id}_track_2", "title": f"Track 2 from {album_id}"},
                ],
            }

        return generate_album_metadata

    @pytest.mark.asyncio
    async def test_complete_artist_countdown_flow(
        self,
        artist_parsed_url,
        mock_credentials,
        mock_artist_model,
        mock_album_metadata_generator,
    ):
        """Test the complete flow from MetadataFetcher through to progress updates."""
        # Track all progress emissions
        progress_emissions = []
        album_emissions = []

        def track_progress(remaining, total, service):
            progress_emissions.append((remaining, total, service))

        def track_album(album_metadata):
            album_emissions.append(album_metadata)

        # Create MetadataFetcher
        fetcher = MetadataFetcher(artist_parsed_url, mock_credentials)

        # Connect signals
        fetcher.artist_progress_updated.connect(track_progress)
        fetcher.album_fetched.connect(track_album)

        # Mock the provider creation and authentication
        with patch(
            "ripstream.ui.metadata_fetcher.MetadataProviderFactory"
        ) as mock_factory:
            # Create mock provider
            mock_provider = Mock(spec=QobuzMetadataProvider)
            mock_provider.service_name = "Qobuz"
            mock_provider.authenticate = AsyncMock(return_value=True)
            mock_provider.cleanup = AsyncMock()

            # Mock the streaming method
            async def mock_fetch_artist_streaming(
                content_id, album_callback=None, counter_init_callback=None
            ):
                # Initialize counter if callback provided
                if counter_init_callback:
                    counter_init_callback(len(mock_artist_model.album_ids), "Qobuz")

                # Simulate album fetching
                if album_callback:
                    for album_id in mock_artist_model.album_ids:
                        album_metadata = mock_album_metadata_generator(album_id)
                        album_callback(album_metadata)
                        # Small delay to simulate real fetching
                        await asyncio.sleep(0.01)

                # Return initial artist metadata
                return Mock(
                    content_type="artist",
                    service="Qobuz",
                    data={
                        "content_type": "artist",
                        "artist_info": {
                            "id": content_id,
                            "name": mock_artist_model.name,
                            "total_items": len(mock_artist_model.album_ids),
                            "remaining_items": len(mock_artist_model.album_ids),
                        },
                        "items": [],
                        "album_ids": mock_artist_model.album_ids,
                    },
                )

            mock_provider.fetch_artist_metadata_streaming = mock_fetch_artist_streaming

            # Setup factory
            mock_factory.is_service_supported.return_value = True
            mock_factory.create_provider.return_value = mock_provider

            # Run the fetcher
            await fetcher._fetch_metadata()

            # Verify progress emissions
            assert len(progress_emissions) == 5  # One for each album

            # Check countdown sequence
            expected_remaining = [4, 3, 2, 1, 0]  # Countdown from 4 to 0
            for i, (remaining, total, service) in enumerate(progress_emissions):
                assert remaining == expected_remaining[i]
                assert total == 5
                assert service == "Qobuz"

            # Verify all albums were processed
            assert len(album_emissions) == 5
            for i, album_metadata in enumerate(album_emissions):
                expected_album_id = f"album_{i + 1}"
                assert album_metadata["album_info"]["id"] == expected_album_id

    @pytest.mark.asyncio
    async def test_metadata_service_integration(
        self,
        artist_parsed_url,
        mock_credentials,
        mock_artist_model,
        mock_album_metadata_generator,
    ):
        """Test integration through MetadataService."""
        from ripstream.config.user import UserConfig

        # Track emissions
        metadata_emissions = []
        album_emissions = []
        progress_emissions = []

        def track_metadata(metadata):
            metadata_emissions.append(metadata)

        def track_album(album_metadata):
            album_emissions.append(album_metadata)

        def track_progress(remaining, total, service):
            progress_emissions.append((remaining, total, service))

        # Create MetadataService
        config = UserConfig()
        service = MetadataService(config)

        # Connect signals
        service.metadata_ready.connect(track_metadata)
        service.album_ready.connect(track_album)
        service.artist_progress_updated.connect(track_progress)

        # Mock the entire provider chain
        with patch(
            "ripstream.ui.metadata_service.MetadataFetcher"
        ) as mock_fetcher_class:
            # Create mock fetcher instance
            mock_fetcher = Mock()
            mock_fetcher.metadata_fetched = Mock()
            mock_fetcher.album_fetched = Mock()
            mock_fetcher.artwork_fetched = Mock()
            mock_fetcher.progress_updated = Mock()
            mock_fetcher.artist_progress_updated = Mock()
            mock_fetcher.error_occurred = Mock()
            mock_fetcher.start = Mock()
            mock_fetcher.isRunning = Mock(return_value=False)

            # Setup signal connections to actually work
            class MockSignal:
                def __init__(self):
                    self.connected_slots = []

                def connect(self, slot):
                    self.connected_slots.append(slot)

                def emit(self, *args):
                    for slot in self.connected_slots:
                        slot(*args)

            mock_fetcher.metadata_fetched = MockSignal()
            mock_fetcher.album_fetched = MockSignal()
            mock_fetcher.artist_progress_updated = MockSignal()
            mock_fetcher.artwork_fetched = MockSignal()
            mock_fetcher.progress_updated = MockSignal()
            mock_fetcher.error_occurred = MockSignal()

            mock_fetcher_class.return_value = mock_fetcher

            # Start fetching
            service.fetch_metadata(artist_parsed_url)

            # Simulate the complete flow
            # 1. Emit initial metadata
            initial_metadata = {
                "content_type": "artist",
                "service": "Qobuz",
                "artist_info": {
                    "name": "Integration Test Artist",
                    "total_items": 5,
                    "remaining_items": 5,
                },
                "items": [],
            }
            mock_fetcher.metadata_fetched.emit(initial_metadata)

            # 2. Simulate album fetching with progress updates
            for i in range(5):
                # Emit album
                album_metadata = mock_album_metadata_generator(f"album_{i + 1}")
                mock_fetcher.album_fetched.emit(album_metadata)

                # Emit progress (remaining count decreases)
                remaining = 4 - i
                mock_fetcher.artist_progress_updated.emit(remaining, 5, "Qobuz")

            # Verify all signals were forwarded correctly
            assert len(metadata_emissions) == 1
            assert metadata_emissions[0]["content_type"] == "artist"

            assert len(album_emissions) == 5
            assert len(progress_emissions) == 5

            # Verify countdown sequence
            for i, (remaining, total, service) in enumerate(progress_emissions):
                assert remaining == 4 - i  # 4, 3, 2, 1, 0
                assert total == 5
                assert service == "Qobuz"

    def test_thread_safety_under_concurrent_load(
        self, artist_parsed_url, mock_credentials
    ):
        """Test thread safety when multiple threads access the counter simultaneously."""
        fetcher = MetadataFetcher(artist_parsed_url, mock_credentials)

        # Initialize counter
        fetcher._initialize_artist_counter(100, "TestService")

        # Create many threads that will decrement simultaneously
        threads = []
        for _ in range(100):
            thread = threading.Thread(target=fetcher._decrement_remaining_items)
            threads.append(thread)

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify final state - the key test is that we reach exactly 0
        # This proves the thread safety of the counter mechanism
        assert fetcher._remaining_items == 0
        assert fetcher._total_items == 100
        assert fetcher._service_name == "TestService"

        # Additional verification: try to decrement when already at 0
        # This should not change the state
        fetcher._decrement_remaining_items()
        assert fetcher._remaining_items == 0  # Should remain 0

    @pytest.mark.parametrize(
        ("album_count", "expected_emissions"),
        [
            (1, 1),
            (3, 3),
            (5, 5),
            (10, 10),
            (0, 0),  # Edge case: no albums
        ],
    )
    def test_countdown_with_various_album_counts(
        self, artist_parsed_url, mock_credentials, album_count, expected_emissions
    ):
        """Test countdown behavior with various album counts."""
        fetcher = MetadataFetcher(artist_parsed_url, mock_credentials)

        # Initialize counter
        fetcher._initialize_artist_counter(album_count, "TestService")

        # Track emissions
        emissions = []

        def track_emission(remaining, total, service):
            emissions.append((remaining, total, service))

        fetcher.artist_progress_updated.connect(track_emission)

        # Simulate album fetching
        for _ in range(album_count):
            fetcher._decrement_remaining_items()

        # Verify emissions
        assert len(emissions) == expected_emissions

        if expected_emissions > 0:
            # Verify countdown sequence
            for i, (remaining, total, service) in enumerate(emissions):
                assert remaining == album_count - 1 - i
                assert total == album_count
                assert service == "TestService"

        # Verify final state
        assert fetcher._remaining_items == 0
        assert fetcher._total_items == album_count

    def test_mixed_content_type_handling(self, mock_credentials):
        """Test that countdown only works for artist content, not other types."""
        # Test with different content types
        content_types = [
            (ContentType.ARTIST, True),  # Should decrement
            (ContentType.ALBUM, False),  # Should not decrement
            (ContentType.TRACK, False),  # Should not decrement
            (ContentType.PLAYLIST, False),  # Should not decrement
        ]

        for content_type, should_decrement in content_types:
            # Create ParsedURL for specific content type
            parsed_url = ParsedURL(
                service=StreamingSource.QOBUZ,
                content_type=content_type,
                content_id="test_123",
                url=f"https://example.com/{content_type.value}/test_123",
                metadata={"name": "Test Content"},
            )

            fetcher = MetadataFetcher(parsed_url, mock_credentials)

            # Initialize counter
            fetcher._initialize_artist_counter(5, "TestService")

            # Track emissions
            emissions = []

            def track_emission(remaining, total, service, emissions=emissions):
                emissions.append((remaining, total, service))

            fetcher.artist_progress_updated.connect(track_emission)

            # Mock album metadata
            album_metadata = {
                "content_type": "album",
                "album_info": {"id": "test_album", "title": "Test Album"},
                "items": [],
            }

            # Mock async task creation
            with patch("asyncio.create_task") as mock_create_task:
                mock_task = Mock()
                mock_create_task.return_value = mock_task

                # Call _on_album_fetched
                fetcher._on_album_fetched(album_metadata)

            # Verify behavior based on content type
            if should_decrement:
                assert len(emissions) == 1
                assert emissions[0] == (4, 5, "TestService")  # Decremented
                assert fetcher._remaining_items == 4
            else:
                assert len(emissions) == 0  # No emissions
                assert fetcher._remaining_items == 5  # Unchanged

    def test_error_recovery_and_cleanup(self, artist_parsed_url, mock_credentials):
        """Test that the system handles errors gracefully and cleans up properly."""
        fetcher = MetadataFetcher(artist_parsed_url, mock_credentials)

        # Initialize counter
        fetcher._initialize_artist_counter(3, "TestService")

        # Track emissions
        emissions = []

        def track_emission(remaining, total, service):
            emissions.append((remaining, total, service))

        fetcher.artist_progress_updated.connect(track_emission)

        # Simulate partial processing with error
        fetcher._decrement_remaining_items()  # 2 remaining
        fetcher._decrement_remaining_items()  # 1 remaining

        # Verify partial state
        assert len(emissions) == 2
        assert fetcher._remaining_items == 1

        # Simulate cleanup/reset by reinitializing
        fetcher._initialize_artist_counter(5, "NewService")

        # Verify reset state
        assert fetcher._remaining_items == 5
        assert fetcher._total_items == 5
        assert fetcher._service_name == "NewService"

        # Continue processing
        fetcher._decrement_remaining_items()  # 4 remaining

        # Verify new emissions
        assert len(emissions) == 3
        assert emissions[2] == (4, 5, "NewService")
