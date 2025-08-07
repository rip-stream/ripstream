# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for artist countdown functionality in QobuzMetadataProvider."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from ripstream.ui.metadata_providers.qobuz import QobuzMetadataProvider


class TestQobuzMetadataProviderArtistCountdown:
    """Test the artist countdown functionality in QobuzMetadataProvider."""

    @pytest.fixture
    def mock_credentials(self):
        """Mock credentials for testing."""
        return {"username": "test", "password": "test"}

    @pytest.fixture
    def qobuz_provider(self, mock_credentials):
        """Create QobuzMetadataProvider instance."""
        return QobuzMetadataProvider(mock_credentials)

    @pytest.fixture
    def mock_qobuz_downloader(self):
        """Mock QobuzDownloader."""
        downloader = Mock()
        downloader.get_artist_metadata = AsyncMock()
        return downloader

    @pytest.fixture
    def mock_artist_model(self):
        """Mock artist model with album IDs."""
        artist = Mock()
        artist.name = "Test Artist"
        artist.info.biography = "Test biography"
        artist.album_ids = ["album_1", "album_2", "album_3", "album_4", "album_5"]

        # Mock covers
        covers = Mock()
        thumbnail = Mock()
        thumbnail.url = "https://example.com/thumbnail.jpg"
        covers.get_best_image.return_value = thumbnail
        artist.covers = covers

        return artist

    @pytest.fixture
    def authenticated_provider(self, qobuz_provider, mock_qobuz_downloader):
        """Create authenticated QobuzMetadataProvider."""
        qobuz_provider._authenticated = True
        qobuz_provider.qobuz_downloader = mock_qobuz_downloader
        return qobuz_provider

    def test_fetch_artist_metadata_streaming_signature(self, authenticated_provider):
        """Test that fetch_artist_metadata_streaming has the correct signature."""
        import inspect

        sig = inspect.signature(authenticated_provider.fetch_artist_metadata_streaming)
        params = list(sig.parameters.keys())

        # Should have artist_id, album_callback, counter_init_callback (self is not included in params)
        assert len(params) == 3
        assert params[0] == "artist_id"
        assert params[1] == "album_callback"
        assert params[2] == "counter_init_callback"

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_with_counter_callback(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test fetch_artist_metadata_streaming calls counter_init_callback."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Mock callbacks
        album_callback = Mock()
        counter_init_callback = Mock()

        # Mock _fetch_albums_async to avoid actual album fetching
        with patch.object(
            authenticated_provider, "_fetch_albums_async", new_callable=AsyncMock
        ) as mock_fetch_albums:
            # Call the method
            await authenticated_provider.fetch_artist_metadata_streaming(
                "artist_123",
                album_callback=album_callback,
                counter_init_callback=counter_init_callback,
            )

            # Verify counter_init_callback was called with correct parameters
            counter_init_callback.assert_called_once_with(
                5, "Qobuz"
            )  # 5 albums, Qobuz service

            # Verify _fetch_albums_async was called
            mock_fetch_albums.assert_called_once_with(
                mock_artist_model.album_ids, album_callback
            )

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_without_counter_callback(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test fetch_artist_metadata_streaming works without counter_init_callback."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Mock album callback only
        album_callback = Mock()

        # Mock _fetch_albums_async
        with patch.object(
            authenticated_provider, "_fetch_albums_async", new_callable=AsyncMock
        ) as mock_fetch_albums:
            # Call the method without counter callback
            await authenticated_provider.fetch_artist_metadata_streaming(
                "artist_123", album_callback=album_callback, counter_init_callback=None
            )

            # Verify _fetch_albums_async was still called
            mock_fetch_albums.assert_called_once_with(
                mock_artist_model.album_ids, album_callback
            )

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_without_album_callback(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test fetch_artist_metadata_streaming works without album_callback."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Mock counter callback only
        counter_init_callback = Mock()

        # Call the method without album callback
        await authenticated_provider.fetch_artist_metadata_streaming(
            "artist_123",
            album_callback=None,
            counter_init_callback=counter_init_callback,
        )

        # Verify counter callback was not called (no album fetching)
        counter_init_callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_result_includes_remaining_items(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test that result includes remaining_items field."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Call the method
        result = await authenticated_provider.fetch_artist_metadata_streaming(
            "artist_123"
        )

        # Verify result structure
        assert result.content_type == "artist"
        assert result.service == "Qobuz"
        assert "artist_info" in result.data

        artist_info = result.data["artist_info"]
        assert artist_info["total_items"] == 5
        assert artist_info["remaining_items"] == 5  # Should match total_items initially
        assert artist_info["name"] == "Test Artist"

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_result_includes_album_ids(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test that result includes album_ids field."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Call the method
        result = await authenticated_provider.fetch_artist_metadata_streaming(
            "artist_123"
        )

        # Verify album_ids are included
        assert "album_ids" in result.data
        assert result.data["album_ids"] == [
            "album_1",
            "album_2",
            "album_3",
            "album_4",
            "album_5",
        ]

    @pytest.mark.parametrize(
        ("album_count", "expected_total", "expected_remaining"),
        [
            (0, 0, 0),
            (1, 1, 1),
            (3, 3, 3),
            (10, 10, 10),
            (100, 100, 100),
        ],
    )
    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_various_album_counts(
        self,
        authenticated_provider,
        mock_qobuz_downloader,
        album_count,
        expected_total,
        expected_remaining,
    ):
        """Test fetch_artist_metadata_streaming with various album counts."""
        # Create mock artist with specific album count
        artist = Mock()
        artist.name = "Test Artist"
        artist.info.biography = "Test biography"
        artist.album_ids = [f"album_{i}" for i in range(album_count)]

        # Mock covers
        covers = Mock()
        thumbnail = Mock()
        thumbnail.url = "https://example.com/thumbnail.jpg"
        covers.get_best_image.return_value = thumbnail
        artist.covers = covers

        mock_qobuz_downloader.get_artist_metadata.return_value = artist

        # Mock counter callback
        counter_init_callback = Mock()

        # Mock _fetch_albums_async
        with patch.object(
            authenticated_provider, "_fetch_albums_async", new_callable=AsyncMock
        ):
            # Call the method
            result = await authenticated_provider.fetch_artist_metadata_streaming(
                "artist_123",
                album_callback=Mock(),
                counter_init_callback=counter_init_callback,
            )

            # Verify counts
            artist_info = result.data["artist_info"]
            assert artist_info["total_items"] == expected_total
            assert artist_info["remaining_items"] == expected_remaining

            # Verify counter callback was called with correct count
            if album_count > 0:
                counter_init_callback.assert_called_once_with(album_count, "Qobuz")
            else:
                counter_init_callback.assert_called_once_with(0, "Qobuz")

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_counter_callback_timing(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test that counter_init_callback is called before _fetch_albums_async."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Track call order
        call_order = []

        def track_counter_init(total, service):
            call_order.append(f"counter_init({total}, {service})")

        def track_fetch_albums(album_ids, callback):
            call_order.append(f"fetch_albums({len(album_ids)} albums)")

        counter_init_callback = Mock(side_effect=track_counter_init)
        album_callback = Mock()

        # Mock _fetch_albums_async
        with patch.object(
            authenticated_provider,
            "_fetch_albums_async",
            side_effect=track_fetch_albums,
        ):
            # Call the method
            await authenticated_provider.fetch_artist_metadata_streaming(
                "artist_123",
                album_callback=album_callback,
                counter_init_callback=counter_init_callback,
            )

            # Verify call order
            assert len(call_order) == 2
            assert call_order[0] == "counter_init(5, Qobuz)"
            assert call_order[1] == "fetch_albums(5 albums)"

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_error_handling(
        self, authenticated_provider, mock_qobuz_downloader
    ):
        """Test error handling in fetch_artist_metadata_streaming."""
        # Setup mock to raise exception
        mock_qobuz_downloader.get_artist_metadata.side_effect = Exception("API Error")

        # Call should raise the exception
        with pytest.raises(Exception, match="API Error"):
            await authenticated_provider.fetch_artist_metadata_streaming("artist_123")

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_not_authenticated(
        self, qobuz_provider
    ):
        """Test fetch_artist_metadata_streaming when not authenticated."""
        # Provider is not authenticated by default
        assert not qobuz_provider._authenticated

        # Call should raise RuntimeError
        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await qobuz_provider.fetch_artist_metadata_streaming("artist_123")

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_no_downloader(self, qobuz_provider):
        """Test fetch_artist_metadata_streaming when downloader is None."""
        # Set authenticated but no downloader
        qobuz_provider._authenticated = True
        qobuz_provider.qobuz_downloader = None

        # Call should raise RuntimeError
        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await qobuz_provider.fetch_artist_metadata_streaming("artist_123")

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_callback_exception_handling(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test that exceptions in callbacks don't break the main flow."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Create callback that raises exception
        def failing_counter_callback(total, service):
            msg = "Callback failed"
            raise ValueError(msg)

        album_callback = Mock()

        # Mock _fetch_albums_async
        with (
            patch.object(
                authenticated_provider, "_fetch_albums_async", new_callable=AsyncMock
            ),
            pytest.raises(ValueError, match="Callback failed"),
        ):
            # Call should not raise exception despite callback failure
            await authenticated_provider.fetch_artist_metadata_streaming(
                "artist_123",
                album_callback=album_callback,
                counter_init_callback=failing_counter_callback,
            )

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_streaming_integration_flow(
        self, authenticated_provider, mock_qobuz_downloader, mock_artist_model
    ):
        """Test the complete integration flow of fetch_artist_metadata_streaming."""
        # Setup mock
        mock_qobuz_downloader.get_artist_metadata.return_value = mock_artist_model

        # Track all interactions
        counter_calls = []
        album_calls = []

        def track_counter(total, service):
            counter_calls.append((total, service))

        def track_album(album_metadata):
            album_calls.append(album_metadata)

        counter_callback = Mock(side_effect=track_counter)
        album_callback = Mock(side_effect=track_album)

        # Mock _fetch_albums_async to simulate album fetching
        def mock_fetch_albums(album_ids, callback):
            for album_id in album_ids:
                callback({"id": album_id, "title": f"Album {album_id}"})

        with patch.object(
            authenticated_provider, "_fetch_albums_async", side_effect=mock_fetch_albums
        ):
            # Call the method
            result = await authenticated_provider.fetch_artist_metadata_streaming(
                "artist_123",
                album_callback=album_callback,
                counter_init_callback=counter_callback,
            )

            # Verify counter was initialized
            assert len(counter_calls) == 1
            assert counter_calls[0] == (5, "Qobuz")

            # Verify albums were processed
            assert len(album_calls) == 5
            for i, call in enumerate(album_calls):
                assert call["id"] == f"album_{i + 1}"

            # Verify result structure
            assert result.content_type == "artist"
            assert result.data["artist_info"]["total_items"] == 5
            assert result.data["artist_info"]["remaining_items"] == 5
