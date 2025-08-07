# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Comprehensive tests for QobuzMetadataProvider."""

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.session import SessionManager
from ripstream.models.album import Album, AlbumCredits, AlbumInfo
from ripstream.models.artwork import CoverImage, Covers
from ripstream.models.audio import AudioInfo
from ripstream.models.enums import AudioQuality, CoverSize, StreamingSource
from ripstream.models.playlist import Playlist, PlaylistInfo
from ripstream.models.track import Track, TrackCredits, TrackInfo
from ripstream.ui.metadata_providers.base import MetadataResult
from ripstream.ui.metadata_providers.qobuz import QobuzMetadataProvider


class TestQobuzMetadataProvider:
    """Test cases for QobuzMetadataProvider."""

    @pytest.fixture
    def sample_credentials(self) -> dict[str, Any]:
        """Sample credentials for testing."""
        return {"username": "test_user", "password": "test_pass"}

    @pytest.fixture
    def provider_with_credentials(
        self, sample_credentials: dict[str, Any]
    ) -> QobuzMetadataProvider:
        """Create provider with credentials."""
        return QobuzMetadataProvider(credentials=sample_credentials)

    @pytest.fixture
    def provider_without_credentials(self) -> QobuzMetadataProvider:
        """Create provider without credentials."""
        return QobuzMetadataProvider()

    @pytest.fixture
    def sample_cover_image(self) -> CoverImage:
        """Create sample cover image."""
        return CoverImage(
            url="https://example.com/artwork.jpg",
            size=CoverSize.MEDIUM,
            width=300,
            height=300,
            format="JPEG",
            file_size_bytes=50000,
            local_path=None,
        )

    @pytest.fixture
    def sample_covers(self, sample_cover_image: CoverImage) -> Covers:
        """Create sample covers."""
        covers = Covers(primary_color="#FF0000")
        covers.images = [sample_cover_image]
        return covers

    @pytest.fixture
    def sample_audio_info(self) -> AudioInfo:
        """Create sample audio info."""
        return AudioInfo(
            quality=AudioQuality.LOSSLESS,
            sampling_rate=44100,
            bitrate=1411,
            codec="FLAC",
            container="FLAC",
            duration_seconds=225.0,
            file_size_bytes=50000000,
            is_lossless=True,
            bit_depth=16,
        )

    @pytest.fixture
    def sample_track_info(self) -> TrackInfo:
        """Create sample track info."""
        return TrackInfo(
            id="track_123",
            source=StreamingSource.QOBUZ,
            url="https://qobuz.com/track/123",
            title="Test Track",
            sort_title="Test Track",
            version=None,
            work=None,
            movement=None,
            track_number=1,
            disc_number=1,
            total_tracks=10,
            total_discs=1,
            isrc=None,
            upc=None,
            lyrics=None,
            language=None,
            copyright=None,
        )

    @pytest.fixture
    def sample_track_credits(self) -> TrackCredits:
        """Create sample track credits."""
        return TrackCredits(
            artist="Test Artist",
            album_artist="Test Artist",
            composer=None,
            lyricist=None,
            producer=None,
        )

    @pytest.fixture
    def sample_track(
        self,
        sample_track_info: TrackInfo,
        sample_track_credits: TrackCredits,
        sample_covers: Covers,
        sample_audio_info: AudioInfo,
    ) -> Track:
        """Create sample track."""
        return Track(
            info=sample_track_info,
            credits=sample_track_credits,
            audio=sample_audio_info,
            covers=sample_covers,
            album_id="album_123",
            release_date="2023-01-01",
            search_query="test track",
            search_rank=1,
            relevance_score=0.95,
            download_path=None,
            error_message=None,
            download_started_at=None,
            download_completed_at=None,
            downloadable=None,
            popularity_score=85.0,
        )

    @pytest.fixture
    def sample_album_info(self) -> AlbumInfo:
        """Create sample album info."""
        return AlbumInfo(
            id="album_123",
            source=StreamingSource.QOBUZ,
            url="https://qobuz.com/album/123",
            title="Test Album",
            sort_title="Test Album",
            release_date="2023-01-01",
            release_year=2023,
            original_release_date=None,
            catalog_number=None,
            barcode=None,
            label=None,
            total_tracks=10,
            total_discs=1,
            total_duration_seconds=2700.0,
            description=None,
            copyright=None,
        )

    @pytest.fixture
    def sample_album_credits(self) -> AlbumCredits:
        """Create sample album credits."""
        return AlbumCredits(
            artist="Test Artist",
            album_artist="Test Artist",
            producer=None,
            executive_producer=None,
            engineer=None,
            mixer=None,
            mastered_by=None,
        )

    @pytest.fixture
    def sample_album(
        self,
        sample_album_info: AlbumInfo,
        sample_album_credits: AlbumCredits,
        sample_covers: Covers,
    ) -> Album:
        """Create sample album."""
        return Album(
            info=sample_album_info,
            credits=sample_album_credits,
            covers=sample_covers,
            track_ids=["track_1", "track_2", "track_3"],
            search_query="test album",
            search_rank=1,
            relevance_score=0.95,
            download_path=None,
            error_message=None,
            download_started_at=None,
            download_completed_at=None,
            download_folder=None,
        )

    @pytest.fixture
    def sample_playlist_info(self) -> PlaylistInfo:
        """Create sample playlist info."""
        return PlaylistInfo(
            id="playlist_123",
            source=StreamingSource.QOBUZ,
            url="https://qobuz.com/playlist/123",
            name="Test Playlist",
            description=None,
            owner="Test User",
            owner_id="user_123",
            total_tracks=20,
            total_duration_seconds=7200.0,
        )

    @pytest.fixture
    def sample_playlist(self, sample_playlist_info: PlaylistInfo) -> Playlist:
        """Create sample playlist."""
        return Playlist(
            info=sample_playlist_info,
            search_query="test playlist",
            search_rank=1,
            relevance_score=0.95,
            download_path=None,
            error_message=None,
            download_started_at=None,
            download_completed_at=None,
            download_folder=None,
        )

    # Initialization and Properties Tests

    def test_init_with_credentials(self, sample_credentials: dict[str, Any]):
        """Test initialization with credentials."""
        provider = QobuzMetadataProvider(credentials=sample_credentials)

        assert provider.credentials == sample_credentials
        assert not provider._authenticated
        assert provider.qobuz_downloader is None
        assert isinstance(provider.download_config, DownloaderConfig)
        assert isinstance(provider.session_manager, SessionManager)
        assert isinstance(provider.progress_tracker, ProgressTracker)

    def test_init_without_credentials(self):
        """Test initialization without credentials."""
        provider = QobuzMetadataProvider()

        assert provider.credentials == {}
        assert not provider._authenticated
        assert provider.qobuz_downloader is None

    def test_init_with_none_credentials(self):
        """Test initialization with None credentials."""
        provider = QobuzMetadataProvider(credentials=None)

        assert provider.credentials == {}
        assert not provider._authenticated

    def test_service_name_property(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test service_name property."""
        assert provider_without_credentials.service_name == "Qobuz"

    def test_streaming_source_property(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test streaming_source property."""
        assert provider_without_credentials.streaming_source == StreamingSource.QOBUZ

    def test_is_authenticated_property(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test is_authenticated property."""
        assert not provider_without_credentials.is_authenticated

        provider_without_credentials._authenticated = True
        assert provider_without_credentials.is_authenticated

    # Authentication Tests

    @pytest.mark.asyncio
    @patch("ripstream.ui.metadata_providers.qobuz.QobuzDownloader")
    async def test_authenticate_success_with_credentials(
        self,
        mock_downloader_class: Mock,
        provider_with_credentials: QobuzMetadataProvider,
        sample_credentials: dict[str, Any],
    ):
        """Test successful authentication with credentials."""
        mock_downloader = Mock()
        mock_downloader.authenticate = AsyncMock(return_value=True)
        mock_downloader_class.return_value = mock_downloader

        result = await provider_with_credentials.authenticate()

        assert result is True
        assert provider_with_credentials._authenticated is True
        assert provider_with_credentials.qobuz_downloader is mock_downloader
        mock_downloader_class.assert_called_once_with(
            provider_with_credentials.download_config,
            provider_with_credentials.session_manager,
            provider_with_credentials.progress_tracker,
        )
        mock_downloader.authenticate.assert_called_once_with(sample_credentials)

    @pytest.mark.asyncio
    @patch("ripstream.ui.metadata_providers.qobuz.QobuzDownloader")
    async def test_authenticate_failure_with_credentials(
        self,
        mock_downloader_class: Mock,
        provider_with_credentials: QobuzMetadataProvider,
        sample_credentials: dict[str, Any],
    ):
        """Test failed authentication with credentials."""
        mock_downloader = Mock()
        mock_downloader.authenticate = AsyncMock(return_value=False)
        mock_downloader_class.return_value = mock_downloader

        result = await provider_with_credentials.authenticate()

        assert result is False
        assert provider_with_credentials._authenticated is False
        mock_downloader.authenticate.assert_called_once_with(sample_credentials)

    @pytest.mark.asyncio
    @patch("ripstream.ui.metadata_providers.qobuz.QobuzDownloader")
    async def test_authenticate_without_credentials(
        self,
        mock_downloader_class: Mock,
        provider_without_credentials: QobuzMetadataProvider,
    ):
        """Test authentication without credentials."""
        mock_downloader = Mock()
        mock_downloader_class.return_value = mock_downloader

        result = await provider_without_credentials.authenticate()

        assert result is False
        assert provider_without_credentials._authenticated is False
        assert provider_without_credentials.qobuz_downloader is mock_downloader

    @pytest.mark.asyncio
    @patch("ripstream.ui.metadata_providers.qobuz.QobuzDownloader")
    async def test_authenticate_exception_handling(
        self,
        mock_downloader_class: Mock,
        provider_with_credentials: QobuzMetadataProvider,
    ):
        """Test authentication exception handling."""
        mock_downloader = Mock()
        mock_downloader.authenticate = AsyncMock(side_effect=Exception("Auth error"))
        mock_downloader_class.return_value = mock_downloader

        result = await provider_with_credentials.authenticate()

        assert result is False
        assert provider_with_credentials._authenticated is False

    @pytest.mark.asyncio
    @patch("ripstream.ui.metadata_providers.qobuz.QobuzDownloader")
    async def test_authenticate_reuses_existing_downloader(
        self,
        mock_downloader_class: Mock,
        provider_with_credentials: QobuzMetadataProvider,
    ):
        """Test that authenticate reuses existing downloader."""
        existing_downloader = Mock()
        existing_downloader.authenticate = AsyncMock(return_value=True)
        provider_with_credentials.qobuz_downloader = existing_downloader

        result = await provider_with_credentials.authenticate()

        assert result is True
        assert provider_with_credentials.qobuz_downloader is existing_downloader
        mock_downloader_class.assert_not_called()

    # Album Metadata Tests

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_not_authenticated(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test fetch_album_metadata when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await provider_without_credentials.fetch_album_metadata("album_123")

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_no_downloader(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test fetch_album_metadata when no downloader is set."""
        provider_without_credentials._authenticated = True

        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await provider_without_credentials.fetch_album_metadata("album_123")

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_success(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_album: Album,
        sample_track: Track,
    ):
        """Test successful album metadata fetching."""
        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_album_metadata = AsyncMock(return_value=sample_album)
        mock_downloader.get_track_metadata = AsyncMock(return_value=sample_track)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_album_metadata("album_123")

        assert isinstance(result, MetadataResult)
        assert result.content_type == "album"
        assert result.service == "Qobuz"
        assert "album_info" in result.data
        assert "items" in result.data
        assert len(result.data["items"]) == 3  # 3 tracks from sample_album.track_ids

        album_info = result.data["album_info"]
        assert album_info["id"] == "album_123"
        assert album_info["title"] == "Test Album"
        assert album_info["artist"] == "Test Artist"
        assert album_info["year"] == 2023
        assert album_info["total_tracks"] == 10
        assert album_info["total_duration"] == "45:00"
        assert album_info["quality"] == "FLAC"
        assert album_info["artwork_thumbnail"] == "https://example.com/artwork.jpg"

        # Verify track items
        for _i, track_item in enumerate(result.data["items"], 1):
            assert track_item["id"] == "track_123"
            assert track_item["title"] == "Test Track"
            assert track_item["artist"] == "Test Artist"
            assert (
                track_item["track_number"] == 1
            )  # Uses track.info.track_number, not enumerated index
            assert track_item["container"] == "FLAC"

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_track_fetch_error(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_album: Album,
        sample_track: Track,
    ):
        """Test album metadata fetching with track fetch errors."""
        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_album_metadata = AsyncMock(return_value=sample_album)
        # First track succeeds, second fails, third succeeds
        mock_downloader.get_track_metadata = AsyncMock(
            side_effect=[sample_track, Exception("Track error"), sample_track]
        )
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_album_metadata("album_123")

        assert len(result.data["items"]) == 2  # Only successful tracks

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_no_artwork(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_album: Album,
        sample_track: Track,
    ):
        """Test album metadata fetching with no artwork."""
        # Remove artwork from album
        sample_album.covers = Covers(primary_color="#000000")
        sample_album.covers.images = []

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_album_metadata = AsyncMock(return_value=sample_album)
        mock_downloader.get_track_metadata = AsyncMock(return_value=sample_track)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_album_metadata("album_123")

        assert result.data["album_info"]["artwork_thumbnail"] is None

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_no_tracks(
        self, provider_with_credentials: QobuzMetadataProvider, sample_album: Album
    ):
        """Test album metadata fetching with no tracks."""
        sample_album.track_ids = []

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_album_metadata = AsyncMock(return_value=sample_album)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_album_metadata("album_123")

        assert len(result.data["items"]) == 0
        assert result.data["album_info"]["quality"] == "FLAC"  # Default when no tracks

    # Track Metadata Tests

    @pytest.mark.asyncio
    async def test_fetch_track_metadata_not_authenticated(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test fetch_track_metadata when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await provider_without_credentials.fetch_track_metadata("track_123")

    @pytest.mark.asyncio
    async def test_fetch_track_metadata_success(
        self, provider_with_credentials: QobuzMetadataProvider, sample_track: Track
    ):
        """Test successful track metadata fetching."""
        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_track_metadata = AsyncMock(return_value=sample_track)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_track_metadata("track_123")

        assert isinstance(result, MetadataResult)
        assert result.content_type == "track"
        assert result.service == "Qobuz"
        assert len(result.data["items"]) == 1

        track_item = result.data["items"][0]
        assert track_item["id"] == "track_123"
        assert track_item["title"] == "Test Track"
        assert track_item["artist"] == "Test Artist"
        assert track_item["type"] == "Track"
        assert track_item["year"] == 2024
        assert track_item["duration_formatted"] == "03:45"
        assert track_item["track_count"] == 1
        assert track_item["track_number"] == 1
        assert track_item["album"] == "album_123"
        assert track_item["quality"] == "FLAC"
        assert track_item["artwork_url"] == "https://example.com/artwork.jpg"

    @pytest.mark.asyncio
    async def test_fetch_track_metadata_no_artwork(
        self, provider_with_credentials: QobuzMetadataProvider, sample_track: Track
    ):
        """Test track metadata fetching with no artwork."""
        # Create new covers without images
        sample_track.covers = Covers(primary_color="#000000")
        sample_track.covers.images = []

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_track_metadata = AsyncMock(return_value=sample_track)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_track_metadata("track_123")

        track_item = result.data["items"][0]
        assert track_item["artwork_url"] is None

    @pytest.mark.asyncio
    async def test_fetch_track_metadata_no_audio_container(
        self, provider_with_credentials: QobuzMetadataProvider, sample_track: Track
    ):
        """Test track metadata fetching with no audio container."""
        sample_track.audio.container = None

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_track_metadata = AsyncMock(return_value=sample_track)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_track_metadata("track_123")

        track_item = result.data["items"][0]
        assert track_item["quality"] == "FLAC"  # Default value

    # Playlist Metadata Tests

    @pytest.mark.asyncio
    async def test_fetch_playlist_metadata_not_authenticated(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test fetch_playlist_metadata when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await provider_without_credentials.fetch_playlist_metadata("playlist_123")

    @pytest.mark.asyncio
    async def test_fetch_playlist_metadata_success(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_playlist: Playlist,
    ):
        """Test successful playlist metadata fetching."""
        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_playlist_metadata = AsyncMock(return_value=sample_playlist)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_playlist_metadata("playlist_123")

        assert isinstance(result, MetadataResult)
        assert result.content_type == "playlist"
        assert result.service == "Qobuz"
        assert len(result.data["items"]) == 1

        playlist_item = result.data["items"][0]
        assert playlist_item["id"] == "playlist_123"
        assert playlist_item["title"] == "Test Playlist"
        assert playlist_item["artist"] == "Test User"
        assert playlist_item["type"] == "Playlist"
        assert playlist_item["year"] == 2024
        assert playlist_item["duration_formatted"] == "0:00"
        assert playlist_item["track_count"] == 20
        assert playlist_item["quality"] == "Mixed"
        assert playlist_item["artwork_url"] is None

    @pytest.mark.asyncio
    async def test_fetch_playlist_metadata_no_owner(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_playlist: Playlist,
    ):
        """Test playlist metadata fetching with no owner."""
        sample_playlist.info.owner = None

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_playlist_metadata = AsyncMock(return_value=sample_playlist)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_playlist_metadata("playlist_123")

        playlist_item = result.data["items"][0]
        assert playlist_item["artist"] == "Unknown"

    # Artist Metadata Tests

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_success(
        self, provider_with_credentials: QobuzMetadataProvider
    ):
        """Test successful artist metadata fetching."""
        provider_with_credentials._authenticated = True

        # Mock the downloader
        mock_downloader = AsyncMock()
        provider_with_credentials.qobuz_downloader = mock_downloader

        # Mock artist data
        mock_artist = Mock()
        mock_artist.name = "Test Artist"
        mock_artist.info.biography = "Test biography"
        mock_artist.album_ids = ["album1", "album2"]
        mock_artist.covers.get_best_image.return_value = Mock(
            url="http://example.com/artist.jpg"
        )

        mock_downloader.get_artist_metadata.return_value = mock_artist

        # Mock album metadata responses
        mock_album_metadata = MetadataResult(
            content_type="album",
            service="Qobuz",
            data={"album_info": {"total_tracks": 10}, "items": []},
        )

        # Mock the fetch_album_metadata method
        provider_with_credentials.fetch_album_metadata = AsyncMock(  # type: ignore[invalid-assignment]
            return_value=mock_album_metadata
        )

        result = await provider_with_credentials.fetch_artist_metadata("artist_123")

        assert result.content_type == "artist"
        assert result.service == "Qobuz"
        assert result.data["content_type"] == "artist"
        assert result.data["id"] == "artist_123"
        assert result.data["artist_info"]["name"] == "Test Artist"
        assert result.data["artist_info"]["biography"] == "Test biography"
        assert (
            result.data["artist_info"]["artwork_thumbnail"]
            == "http://example.com/artist.jpg"
        )
        assert "items" in result.data

        # Verify the downloader was called
        mock_downloader.get_artist_metadata.assert_called_once_with("artist_123")

    @pytest.mark.asyncio
    async def test_fetch_artist_metadata_not_authenticated(
        self, provider_without_credentials: QobuzMetadataProvider
    ):
        """Test fetch_artist_metadata when not authenticated."""
        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await provider_without_credentials.fetch_artist_metadata("artist_123")

    # Cleanup Tests

    @pytest.mark.asyncio
    async def test_cleanup_success(
        self, provider_with_credentials: QobuzMetadataProvider
    ):
        """Test successful cleanup."""
        mock_session_manager = Mock()
        mock_session_manager.close_all_sessions = AsyncMock()
        provider_with_credentials.session_manager = mock_session_manager

        await provider_with_credentials.cleanup()

        mock_session_manager.close_all_sessions.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_session_manager(
        self, provider_with_credentials: QobuzMetadataProvider
    ):
        """Test cleanup when session_manager doesn't exist."""
        delattr(provider_with_credentials, "session_manager")

        # Should not raise an exception
        await provider_with_credentials.cleanup()

    # Parametrized Tests for Error Scenarios

    @pytest.mark.parametrize(
        ("method_name", "args"),
        [
            ("fetch_album_metadata", ("album_123",)),
            ("fetch_track_metadata", ("track_123",)),
            ("fetch_playlist_metadata", ("playlist_123",)),
            ("fetch_artist_metadata", ("artist_123",)),
        ],
    )
    @pytest.mark.asyncio
    async def test_metadata_methods_require_authentication(
        self,
        provider_without_credentials: QobuzMetadataProvider,
        method_name: str,
        args: tuple[str, ...],
    ):
        """Test that all metadata methods require authentication."""
        method = getattr(provider_without_credentials, method_name)

        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await method(*args)

    @pytest.mark.parametrize(
        ("method_name", "args"),
        [
            ("fetch_album_metadata", ("album_123",)),
            ("fetch_track_metadata", ("track_123",)),
            ("fetch_playlist_metadata", ("playlist_123",)),
        ],
    )
    @pytest.mark.asyncio
    async def test_metadata_methods_require_downloader(
        self,
        provider_without_credentials: QobuzMetadataProvider,
        method_name: str,
        args: tuple[str, ...],
    ):
        """Test that metadata methods require downloader to be set."""
        provider_without_credentials._authenticated = True
        method = getattr(provider_without_credentials, method_name)

        with pytest.raises(RuntimeError, match="Not authenticated with Qobuz"):
            await method(*args)

    # Edge Cases and Error Handling

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_missing_release_year(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_album: Album,
        sample_track: Track,
    ):
        """Test album metadata fetching when album has no release_year."""
        sample_album.info.release_year = None

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_album_metadata = AsyncMock(return_value=sample_album)
        mock_downloader.get_track_metadata = AsyncMock(return_value=sample_track)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_album_metadata("album_123")

        assert result.data["album_info"]["year"] == 2024  # Default value

    @pytest.mark.asyncio
    async def test_fetch_album_metadata_missing_total_tracks(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_album: Album,
        sample_track: Track,
    ):
        """Test album metadata fetching when album has no total_tracks."""
        sample_album.info.total_tracks = 0  # Set to 0 instead of None

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_album_metadata = AsyncMock(return_value=sample_album)
        mock_downloader.get_track_metadata = AsyncMock(return_value=sample_track)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_album_metadata("album_123")

        # Should use length of fetched tracks when total_tracks is 0
        assert result.data["album_info"]["total_tracks"] == 3

    @pytest.mark.asyncio
    async def test_fetch_playlist_metadata_missing_total_tracks(
        self,
        provider_with_credentials: QobuzMetadataProvider,
        sample_playlist: Playlist,
    ):
        """Test playlist metadata fetching when playlist has no total_tracks."""
        sample_playlist.info.total_tracks = 0  # Set to 0 instead of None

        provider_with_credentials._authenticated = True
        mock_downloader = Mock()
        mock_downloader.get_playlist_metadata = AsyncMock(return_value=sample_playlist)
        provider_with_credentials.qobuz_downloader = mock_downloader

        result = await provider_with_credentials.fetch_playlist_metadata("playlist_123")

        playlist_item = result.data["items"][0]
        assert playlist_item["track_count"] == 0  # Should use the 0 value
