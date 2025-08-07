# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for Qobuz downloader."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.qobuz import QobuzCredentials, QobuzDownloader
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource


@pytest.fixture
def config():
    """Create test configuration."""
    return DownloaderConfig(
        download_directory=Path("./test_downloads"),
        max_concurrent_downloads=1,
    )


@pytest.fixture
def session_manager(config):
    """Create test session manager."""
    return SessionManager(config)


@pytest.fixture
def progress_tracker():
    """Create test progress tracker."""
    return ProgressTracker()


@pytest.fixture
def qobuz_downloader(config, session_manager, progress_tracker):
    """Create Qobuz downloader instance."""
    return QobuzDownloader(config, session_manager, progress_tracker)


@pytest.fixture
def mock_credentials():
    """Create mock credentials."""
    return {
        "email_or_userid": "test@example.com",
        "password_or_token": "test_password",
        "app_id": "123456789",
        "secrets": ["test_secret"],
        "use_auth_token": False,
    }


class TestQobuzDownloader:
    """Test cases for QobuzDownloader."""

    def test_source_name(self, qobuz_downloader):
        """Test source name property."""
        assert qobuz_downloader.source_name == "qobuz"

    def test_supported_content_types(self, qobuz_downloader):
        """Test supported content types."""
        expected_types = [
            ContentType.TRACK,
            ContentType.ALBUM,
            ContentType.PLAYLIST,
        ]
        assert qobuz_downloader.supported_content_types == expected_types

    @pytest.mark.asyncio
    async def test_authenticate_success(self, qobuz_downloader, mock_credentials):
        """Test successful authentication."""
        with patch.object(
            qobuz_downloader.client, "authenticate", return_value=True
        ) as mock_auth:
            result = await qobuz_downloader.authenticate(mock_credentials)

            assert result is True
            assert qobuz_downloader._authenticated is True
            mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, qobuz_downloader, mock_credentials):
        """Test authentication failure."""
        with patch.object(
            qobuz_downloader.client, "authenticate", return_value=False
        ) as mock_auth:
            result = await qobuz_downloader.authenticate(mock_credentials)

            assert result is False
            assert qobuz_downloader._authenticated is False
            mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_track_metadata(self, qobuz_downloader):
        """Test getting track metadata."""
        # Mock the client response
        mock_track_response = MagicMock()
        mock_track_response.title = "Test Track"
        mock_track_response.artist_name = "Test Artist"
        mock_track_response.album_title = "Test Album"
        mock_track_response.album_artist = "Test Album Artist"
        mock_track_response.track_number = 1
        mock_track_response.disc_number = 1
        mock_track_response.duration = 180
        mock_track_response.isrc = "TEST123456789"
        mock_track_response.copyright = "Test Copyright"
        mock_track_response.parental_warning = False
        mock_track_response.maximum_bit_depth = 16
        mock_track_response.maximum_sampling_rate = 44100.0
        mock_track_response.version = None
        mock_track_response.composer = None

        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client, "get_track_info", return_value=mock_track_response
        ):
            track = await qobuz_downloader.get_track_metadata("123456")

            assert track.title == "Test Track"
            assert track.artist == "Test Artist"
            assert track.info.source == StreamingSource.QOBUZ

    @pytest.mark.asyncio
    async def test_get_album_metadata(self, qobuz_downloader):
        """Test getting album metadata."""
        # Mock the client response
        mock_album_response = MagicMock()
        mock_album_response.title = "Test Album"
        mock_album_response.artist_name = "Test Artist"
        mock_album_response.release_date_original = "2023-01-01"
        mock_album_response.label_name = "Test Label"
        mock_album_response.tracks_count = 10
        mock_album_response.duration = 1800
        mock_album_response.genres_list = ["Rock", "Pop"]
        mock_album_response.genre_name = "Rock"
        mock_album_response.description = "Test Description"
        mock_album_response.copyright = "Test Copyright"
        mock_album_response.upc = "123456789012"
        mock_album_response.version = None
        mock_album_response.tracks = {"items": [{"id": "123"}, {"id": "456"}]}

        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client, "get_album_info", return_value=mock_album_response
        ):
            album = await qobuz_downloader.get_album_metadata("789")

            assert album.title == "Test Album"
            assert album.artist == "Test Artist"
            assert album.info.source == StreamingSource.QOBUZ
            assert len(album.track_ids) == 2

    @pytest.mark.asyncio
    async def test_search_tracks(self, qobuz_downloader):
        """Test searching for tracks."""
        # Mock search result
        mock_search_result = MagicMock()
        mock_search_result.tracks = {
            "items": [
                {"id": "123", "title": "Track 1"},
                {"id": "456", "title": "Track 2"},
            ]
        }

        # Mock track metadata calls
        mock_track = MagicMock()
        mock_track.title = "Test Track"
        mock_track.artist = "Test Artist"
        mock_track.info.source = StreamingSource.QOBUZ

        qobuz_downloader._authenticated = True

        with (
            patch.object(
                qobuz_downloader.client, "search", return_value=mock_search_result
            ),
            patch.object(
                qobuz_downloader, "get_track_metadata", return_value=mock_track
            ),
        ):
            results = await qobuz_downloader.search(
                "test query", ContentType.TRACK, limit=2
            )

            assert len(results) == 2
            assert all(track.title == "Test Track" for track in results)

    def test_determine_content_type(self, qobuz_downloader):
        """Test content type determination."""
        # Short numeric ID should be track
        assert qobuz_downloader._determine_content_type("123456") == ContentType.TRACK

        # Longer ID should be album (simplified heuristic)
        assert (
            qobuz_downloader._determine_content_type("abcdef123456789")
            == ContentType.ALBUM
        )

    def test_sanitize_filename(self, qobuz_downloader):
        """Test filename sanitization."""
        # Test with invalid characters
        dirty_name = 'Test<>:"/\\|?*Song'
        clean_name = qobuz_downloader._sanitize_filename(dirty_name)
        assert clean_name == "Test_________Song"

        # Test with long filename
        long_name = "A" * 150
        clean_name = qobuz_downloader._sanitize_filename(long_name)
        assert len(clean_name) == 100

    def test_extract_year_from_date(self, qobuz_downloader):
        """Test year extraction from date string."""
        assert qobuz_downloader._extract_year_from_date("2023-01-01") == 2023
        assert qobuz_downloader._extract_year_from_date("2023") == 2023
        assert qobuz_downloader._extract_year_from_date(None) is None
        assert qobuz_downloader._extract_year_from_date("invalid") is None

    def test_get_bitrate_for_quality(self, qobuz_downloader):
        """Test bitrate mapping for quality."""
        assert qobuz_downloader._get_bitrate_for_quality(5) == 320  # MP3 320
        assert qobuz_downloader._get_bitrate_for_quality(6) == 1411  # FLAC 16/44.1
        assert qobuz_downloader._get_bitrate_for_quality(7) == 2304  # FLAC 24/96
        assert qobuz_downloader._get_bitrate_for_quality(27) == 4608  # FLAC 24/192
        assert qobuz_downloader._get_bitrate_for_quality(999) is None  # Unknown

    @pytest.mark.asyncio
    async def test_cleanup(self, qobuz_downloader):
        """Test cleanup method."""
        qobuz_downloader._authenticated = True

        with (
            patch.object(qobuz_downloader.client, "close") as mock_close,
            patch(
                "ripstream.downloader.qobuz.downloader.BaseDownloader.cleanup"
            ) as mock_super_cleanup,
        ):
            await qobuz_downloader.cleanup()

            assert qobuz_downloader._authenticated is False
            mock_close.assert_called_once()
            mock_super_cleanup.assert_called_once()


class TestQobuzCredentials:
    """Test cases for QobuzCredentials model."""

    def test_credentials_creation(self):
        """Test creating credentials."""
        creds = QobuzCredentials(
            email_or_userid="test@example.com",
            password_or_token="password123",
            app_id="123456789",
            secrets=["secret1", "secret2"],
            use_auth_token=False,
        )

        assert creds.email_or_userid == "test@example.com"
        assert creds.password_or_token == "password123"
        assert creds.app_id == "123456789"
        assert creds.secrets == ["secret1", "secret2"]
        assert creds.use_auth_token is False

    def test_credentials_defaults(self):
        """Test credential defaults."""
        creds = QobuzCredentials(
            email_or_userid="test@example.com",
            password_or_token="password123",
            app_id=None,
        )

        assert creds.app_id is None
        assert creds.secrets == []
        assert creds.use_auth_token is False

    @pytest.mark.asyncio
    async def test_download_album(self, qobuz_downloader):
        """Test downloading an entire album."""
        # Mock album metadata
        mock_album = MagicMock()
        mock_album.track_ids = ["123", "456", "789"]
        mock_album.get_download_folder_name.return_value = "Test Artist - Test Album"

        # Mock download results
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.file_path = "/path/to/track.flac"

        qobuz_downloader._authenticated = True

        with (
            patch.object(
                qobuz_downloader, "get_album_metadata", return_value=mock_album
            ),
            patch.object(
                qobuz_downloader, "download_multiple", return_value=[mock_result] * 3
            ),
            patch.object(
                qobuz_downloader, "_get_track_download_info"
            ) as mock_get_track_info,
            patch("pathlib.Path.mkdir"),
        ):
            results = await qobuz_downloader.download_album("album_123")

            assert len(results) == 3
            assert all(r.is_success for r in results)
            assert mock_get_track_info.call_count == 3

    @pytest.mark.asyncio
    async def test_download_playlist(self, qobuz_downloader):
        """Test downloading an entire playlist."""
        # Mock playlist metadata
        mock_playlist = MagicMock()
        mock_playlist.get_track_ids.return_value = ["123", "456"]
        mock_playlist.get_download_folder_name.return_value = "Owner - Playlist Name"

        # Mock download results
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.file_path = "/path/to/track.flac"

        qobuz_downloader._authenticated = True

        with (
            patch.object(
                qobuz_downloader, "get_playlist_metadata", return_value=mock_playlist
            ),
            patch.object(
                qobuz_downloader, "download_multiple", return_value=[mock_result] * 2
            ),
            patch.object(
                qobuz_downloader, "_get_track_download_info"
            ) as mock_get_track_info,
            patch("pathlib.Path.mkdir"),
        ):
            results = await qobuz_downloader.download_playlist("playlist_123")

            assert len(results) == 2
            assert all(r.is_success for r in results)
            assert mock_get_track_info.call_count == 2

    @pytest.mark.asyncio
    async def test_download_artist_discography(self, qobuz_downloader):
        """Test downloading an artist's discography."""
        # Mock album search results
        mock_album1 = MagicMock()
        mock_album1.artist = "Test Artist"
        mock_album1.info.id = "album_1"

        mock_album2 = MagicMock()
        mock_album2.artist = "Test Artist"
        mock_album2.info.id = "album_2"

        # Mock download results
        mock_result = MagicMock()
        mock_result.is_success = True

        qobuz_downloader._authenticated = True

        with (
            patch.object(
                qobuz_downloader, "search", return_value=[mock_album1, mock_album2]
            ),
            patch.object(
                qobuz_downloader, "download_album", return_value=[mock_result] * 5
            ),
            patch("pathlib.Path.mkdir"),
        ):
            results = await qobuz_downloader.download_artist_discography("artist_123")

            assert len(results) == 10  # 2 albums * 5 tracks each
            assert all(r.is_success for r in results)

    @pytest.mark.asyncio
    async def test_get_album_download_info(self, qobuz_downloader):
        """Test getting album download info."""
        # Mock album response
        mock_album_response = MagicMock()
        mock_album_response.title = "Test Album"
        mock_album_response.artist_name = "Test Artist"
        mock_album_response.tracks_count = 10
        mock_album_response.duration = 3600
        mock_album_response.release_date_original = "2023-01-01"
        mock_album_response.tracks = {"items": [{"id": "123"}, {"id": "456"}]}

        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client, "get_album_info", return_value=mock_album_response
        ):
            download_info = await qobuz_downloader._get_album_download_info("album_123")

            assert download_info.content_type == ContentType.ALBUM
            assert download_info.title == "Test Album"
            assert download_info.artist == "Test Artist"
            assert download_info.metadata["track_count"] == 10
            assert len(download_info.metadata["track_ids"]) == 2

    @pytest.mark.asyncio
    async def test_get_playlist_download_info(self, qobuz_downloader):
        """Test getting playlist download info."""
        # Mock playlist response
        mock_playlist_response = MagicMock()
        mock_playlist_response.name = "Test Playlist"
        mock_playlist_response.owner_name = "Test Owner"
        mock_playlist_response.tracks_count = 5
        mock_playlist_response.duration = 1800
        mock_playlist_response.tracks = {"items": [{"id": "123"}, {"id": "456"}]}

        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client,
            "get_playlist_info",
            return_value=mock_playlist_response,
        ):
            download_info = await qobuz_downloader._get_playlist_download_info(
                "playlist_123"
            )

            assert download_info.content_type == ContentType.PLAYLIST
            assert download_info.title == "Test Playlist"
            assert download_info.artist == "Test Owner"
            assert download_info.metadata["track_count"] == 5
            assert len(download_info.metadata["track_ids"]) == 2

    @pytest.mark.asyncio
    async def test_download_artwork(self, qobuz_downloader):
        """Test downloading album artwork."""
        from ripstream.models.artwork import Covers, CoverSize

        # Create mock covers
        covers = Covers()
        covers.add_image("https://example.com/cover_large.jpg", CoverSize.LARGE)
        covers.add_image("https://example.com/cover_small.jpg", CoverSize.SMALL)

        qobuz_downloader._authenticated = True

        with (
            patch.object(qobuz_downloader, "download") as mock_download,
            patch("pathlib.Path.mkdir"),
        ):
            # Mock successful download results
            mock_download.return_value = MagicMock(
                success=True, file_path="/path/to/cover.jpg"
            )

            results = await qobuz_downloader.download_artwork(
                "album_123", "/download/path", covers
            )

            assert len(results) == 2  # Two cover sizes
            assert mock_download.call_count == 2

    @pytest.mark.asyncio
    async def test_download_booklets(self, qobuz_downloader):
        """Test downloading album booklets."""
        # Mock album response with booklets
        mock_album_response = MagicMock()
        mock_album_response.get_booklets.return_value = [
            {
                "url": "https://example.com/booklet.pdf",
                "name": "Album Booklet",
                "description": "Digital booklet",
            }
        ]

        qobuz_downloader._authenticated = True

        with (
            patch.object(
                qobuz_downloader.client,
                "get_album_info",
                return_value=mock_album_response,
            ),
            patch.object(qobuz_downloader, "download") as mock_download,
            patch("pathlib.Path.mkdir"),
        ):
            # Mock successful download result
            mock_download.return_value = MagicMock(
                success=True, file_path="/path/to/booklet.pdf"
            )

            results = await qobuz_downloader.download_booklets(
                "album_123", "/download/path"
            )

            assert len(results) == 1
            assert mock_download.call_count == 1

    @pytest.mark.asyncio
    async def test_get_album_metadata_with_artwork(self, qobuz_downloader):
        """Test getting album metadata with artwork information."""
        # Mock album response with image data
        mock_album_response = MagicMock()
        mock_album_response.title = "Test Album"
        mock_album_response.artist_name = "Test Artist"
        mock_album_response.release_date_original = "2023-01-01"
        mock_album_response.label_name = "Test Label"
        mock_album_response.tracks_count = 10
        mock_album_response.duration = 1800
        mock_album_response.genres_list = ["Rock"]
        mock_album_response.genre_name = "Rock"
        mock_album_response.description = "Test Description"
        mock_album_response.copyright = "Test Copyright"
        mock_album_response.upc = "123456789012"
        mock_album_response.version = None
        mock_album_response.tracks = {"items": [{"id": "123"}, {"id": "456"}]}

        # Mock image data
        mock_album_response.image = {
            "large": "https://example.com/cover_600.jpg",
            "small": "https://example.com/cover_300.jpg",
            "thumbnail": "https://example.com/cover_150.jpg",
        }
        mock_album_response.get_cover_urls.return_value = {
            "large": "https://example.com/cover_600.jpg",
            "original": "https://example.com/cover_org.jpg",
            "small": "https://example.com/cover_300.jpg",
            "thumbnail": "https://example.com/cover_150.jpg",
        }
        mock_album_response.get_booklets.return_value = []

        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client, "get_album_info", return_value=mock_album_response
        ):
            album = await qobuz_downloader.get_album_metadata("789")

            assert album.title == "Test Album"
            assert album.artist == "Test Artist"
            assert hasattr(album, "covers")
            assert album.covers.has_images
