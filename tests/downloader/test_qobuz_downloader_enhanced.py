# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enhanced tests for Qobuz downloader with comprehensive coverage."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import aiohttp
import pytest

from ripstream.downloader.base import DownloadableContent, DownloadResult
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.exceptions import (
    AuthenticationError,
    ContentNotFoundError,
    DownloadError,
)
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.qobuz import QobuzCredentials, QobuzDownloader
from ripstream.downloader.qobuz.models import (
    QobuzAlbumResponse,
    QobuzDownloadInfo,
    QobuzPlaylistResponse,
    QobuzSearchResult,
    QobuzTrackResponse,
)
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import AudioQuality, StreamingSource


@pytest.fixture
def download_config():
    """Create test download configuration."""
    return DownloaderConfig(
        download_directory=Path("./test_downloads"),
        max_concurrent_downloads=2,
    )


@pytest.fixture
def session_manager(download_config):
    """Create test session manager."""
    return SessionManager(download_config)


@pytest.fixture
def progress_tracker():
    """Create test progress tracker."""
    return ProgressTracker()


@pytest.fixture
def qobuz_downloader(download_config, session_manager, progress_tracker):
    """Create Qobuz downloader instance."""
    return QobuzDownloader(download_config, session_manager, progress_tracker)


@pytest.fixture
def mock_qobuz_credentials():
    """Create mock Qobuz credentials."""
    return {
        "email_or_userid": "test@example.com",
        "password_or_token": "test_password",
        "app_id": "123456789",
        "secrets": ["test_secret_1", "test_secret_2"],
        "use_auth_token": False,
    }


@pytest.fixture
def mock_track_response():
    """Create mock QobuzTrackResponse."""
    return QobuzTrackResponse(
        title="Test Track",
        version="Remastered",
        duration=240,
        track_number=1,
        disc_number=1,
        performer={"name": "Test Artist", "id": 12345},
        composer={"name": "Test Composer", "id": 67890},
        album={"title": "Test Album", "artist": {"name": "Test Album Artist"}},
        maximum_bit_depth=24,
        maximum_sampling_rate=96000.0,
        isrc="TEST123456789",
        copyright="2023 Test Records",
        parental_warning=False,
        image={"large": "https://example.com/cover_600.jpg"},
        raw_data={"id": "123456"},
    )


@pytest.fixture
def mock_album_response():
    """Create mock QobuzAlbumResponse."""
    return QobuzAlbumResponse(
        title="Test Album",
        version="Deluxe Edition",
        duration=3600,
        tracks_count=12,
        artist={"name": "Test Artist", "id": 12345},
        release_date_original="2023-01-15",
        release_date_download="2023-01-15",
        release_date_stream="2023-01-15",
        maximum_bit_depth=24,
        maximum_sampling_rate=96000.0,
        label={"name": "Test Records"},
        upc="123456789012",
        genre={"name": "Rock"},
        genres_list=["Rock", "Alternative"],
        copyright="2023 Test Records",
        description="A fantastic test album",
        image={"large": "https://example.com/album_600.jpg"},
        tracks={"items": [{"id": "123"}, {"id": "456"}, {"id": "789"}]},
        goodies=[
            {
                "url": "https://example.com/booklet.pdf",
                "name": "Digital Booklet",
                "file_format_id": 21,
                "description": "Album booklet",
            }
        ],
        raw_data={"id": "album123"},
    )


@pytest.fixture
def mock_playlist_response():
    """Create mock QobuzPlaylistResponse."""
    return QobuzPlaylistResponse(
        name="Test Playlist",
        description="A great test playlist",
        duration=1800,
        tracks_count=8,
        owner={"name": "Test User", "id": 54321},
        is_public=True,
        is_collaborative=False,
        created_at=1640995200,
        updated_at=1672531200,
        tracks={"items": [{"id": "111"}, {"id": "222"}]},
        raw_data={"id": "playlist123"},
    )


@pytest.fixture
def mock_download_info():
    """Create mock QobuzDownloadInfo."""
    return QobuzDownloadInfo(
        url="https://example.com/download/track.flac",
        format_id=6,
        mime_type="audio/flac",
        restrictions=[],
    )


class TestQobuzDownloaderProperties:
    """Test QobuzDownloader properties and basic functionality."""

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

    def test_initial_authentication_state(self, qobuz_downloader):
        """Test initial authentication state."""
        assert qobuz_downloader._authenticated is False


class TestQobuzDownloaderAuthentication:
    """Test authentication functionality."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, qobuz_downloader, mock_qobuz_credentials):
        """Test successful authentication."""
        with patch.object(
            qobuz_downloader.client, "authenticate", return_value=True
        ) as mock_auth:
            result = await qobuz_downloader.authenticate(mock_qobuz_credentials)

            assert result is True
            assert qobuz_downloader._authenticated is True
            mock_auth.assert_called_once()

            # Verify credentials were properly constructed
            call_args = mock_auth.call_args[0][0]
            assert isinstance(call_args, QobuzCredentials)
            assert call_args.email_or_userid == "test@example.com"
            assert call_args.password_or_token == "test_password"

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, qobuz_downloader, mock_qobuz_credentials):
        """Test authentication failure."""
        with patch.object(
            qobuz_downloader.client, "authenticate", return_value=False
        ) as mock_auth:
            result = await qobuz_downloader.authenticate(mock_qobuz_credentials)

            assert result is False
            assert qobuz_downloader._authenticated is False
            mock_auth.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_exception(
        self, qobuz_downloader, mock_qobuz_credentials
    ):
        """Test authentication with exception."""
        with patch.object(
            qobuz_downloader.client, "authenticate", side_effect=Exception("Auth error")
        ):
            result = await qobuz_downloader.authenticate(mock_qobuz_credentials)

            assert result is False
            assert qobuz_downloader._authenticated is False

    @pytest.mark.parametrize(
        ("credentials", "expected_use_token"),
        [
            ({"email_or_userid": "test", "password_or_token": "pass"}, False),
            (
                {
                    "email_or_userid": "test",
                    "password_or_token": "token",
                    "use_auth_token": True,
                },
                True,
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_authenticate_credential_variations(
        self, qobuz_downloader, credentials, expected_use_token
    ):
        """Test authentication with different credential configurations."""
        with patch.object(
            qobuz_downloader.client, "authenticate", return_value=True
        ) as mock_auth:
            await qobuz_downloader.authenticate(credentials)

            call_args = mock_auth.call_args[0][0]
            assert call_args.use_auth_token == expected_use_token


class TestQobuzDownloaderMetadata:
    """Test metadata retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_track_metadata_success(
        self, qobuz_downloader, mock_track_response
    ):
        """Test successful track metadata retrieval."""
        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client, "get_track_info", return_value=mock_track_response
        ):
            track = await qobuz_downloader.get_track_metadata("123456")

            assert track.info.title == "Test Track"
            assert track.credits.artist == "Test Artist"
            assert track.info.source == StreamingSource.QOBUZ
            assert track.info.track_number == 1
            assert track.info.disc_number == 1
            assert track.audio.duration_seconds == 240
            assert track.info.isrc == "TEST123456789"

    @pytest.mark.asyncio
    async def test_get_track_metadata_not_authenticated(self, qobuz_downloader):
        """Test track metadata retrieval without authentication."""
        with pytest.raises(AuthenticationError, match="Not authenticated with Qobuz"):
            await qobuz_downloader.get_track_metadata("123456")

    @pytest.mark.asyncio
    async def test_get_album_metadata_success(
        self, qobuz_downloader, mock_album_response
    ):
        """Test successful album metadata retrieval."""
        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client, "get_album_info", return_value=mock_album_response
        ):
            album = await qobuz_downloader.get_album_metadata("album123")

            assert album.info.title == "Test Album"
            assert album.credits.artist == "Test Artist"
            assert album.info.source == StreamingSource.QOBUZ
            assert album.info.total_tracks == 12
            assert album.info.total_duration_seconds == 3600
            assert len(album.track_ids) == 3
            assert album.track_ids == ["123", "456", "789"]

    @pytest.mark.asyncio
    async def test_get_playlist_metadata_success(
        self, qobuz_downloader, mock_playlist_response
    ):
        """Test successful playlist metadata retrieval."""
        qobuz_downloader._authenticated = True

        with patch.object(
            qobuz_downloader.client,
            "get_playlist_info",
            return_value=mock_playlist_response,
        ):
            playlist = await qobuz_downloader.get_playlist_metadata("playlist123")

            assert playlist.info.name == "Test Playlist"
            assert playlist.info.owner == "Test User"
            assert playlist.info.source == StreamingSource.QOBUZ
            assert playlist.info.total_tracks == 8
            assert playlist.info.total_duration_seconds == 1800
            assert playlist.info.is_public is True


class TestQobuzDownloaderSearch:
    """Test search functionality."""

    @pytest.mark.asyncio
    async def test_search_tracks_success(self, qobuz_downloader, mock_track_response):
        """Test successful track search."""
        qobuz_downloader._authenticated = True

        mock_search_result = QobuzSearchResult(
            query="test query",
            tracks={"items": [{"id": "123"}, {"id": "456"}]},
            albums=None,
            artists=None,
            playlists=None,
        )

        with (
            patch.object(
                qobuz_downloader.client, "search", return_value=mock_search_result
            ),
            patch.object(
                qobuz_downloader, "get_track_metadata", return_value=mock_track_response
            ) as mock_get_track,
        ):
            results = await qobuz_downloader.search("test query", ContentType.TRACK, 10)

            assert len(results) == 2
            assert mock_get_track.call_count == 2
            assert all(track.title == "Test Track" for track in results)

    @pytest.mark.asyncio
    async def test_search_albums_success(self, qobuz_downloader, mock_album_response):
        """Test successful album search."""
        qobuz_downloader._authenticated = True

        mock_search_result = QobuzSearchResult(
            query="test query",
            albums={"items": [{"id": "album1"}, {"id": "album2"}]},
            tracks=None,
            artists=None,
            playlists=None,
        )

        with (
            patch.object(
                qobuz_downloader.client, "search", return_value=mock_search_result
            ),
            patch.object(
                qobuz_downloader, "get_album_metadata", return_value=mock_album_response
            ) as mock_get_album,
        ):
            results = await qobuz_downloader.search("test query", ContentType.ALBUM, 10)

            assert len(results) == 2
            assert mock_get_album.call_count == 2
            assert all(album.title == "Test Album" for album in results)

    @pytest.mark.asyncio
    async def test_search_not_authenticated(self, qobuz_downloader):
        """Test search without authentication."""
        with pytest.raises(AuthenticationError, match="Not authenticated with Qobuz"):
            await qobuz_downloader.search("test", ContentType.TRACK)

    @pytest.mark.parametrize(
        ("content_type", "expected_search_type"),
        [
            (ContentType.TRACK, "track"),
            (ContentType.ALBUM, "album"),
            (ContentType.PLAYLIST, "playlist"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_content_type_mapping(
        self, qobuz_downloader, content_type, expected_search_type
    ):
        """Test content type to search type mapping."""
        qobuz_downloader._authenticated = True

        mock_search_result = QobuzSearchResult(
            query="test",
            albums=None,
            tracks=None,
            artists=None,
            playlists=None,
        )

        with patch.object(
            qobuz_downloader.client, "search", return_value=mock_search_result
        ) as mock_search:
            await qobuz_downloader.search("test", content_type)

            mock_search.assert_called_once_with("test", expected_search_type, 50)


class TestQobuzDownloaderDownloadInfo:
    """Test download info retrieval."""

    @pytest.mark.asyncio
    async def test_get_download_info_track(
        self, qobuz_downloader, mock_track_response, mock_download_info
    ):
        """Test getting download info for a track."""
        qobuz_downloader._authenticated = True

        with (
            patch.object(
                qobuz_downloader.client,
                "get_track_info",
                return_value=mock_track_response,
            ),
            patch.object(
                qobuz_downloader.client,
                "get_download_info",
                return_value=mock_download_info,
            ),
            patch.object(
                qobuz_downloader,
                "_determine_content_type",
                return_value=ContentType.TRACK,
            ),
        ):
            download_info = await qobuz_downloader.get_download_info("123456")

            assert download_info.content_type == ContentType.TRACK
            assert download_info.title == "Test Track"
            assert download_info.artist == "Test Artist"
            assert download_info.file_extension == "flac"

    @pytest.mark.asyncio
    async def test_get_download_info_album(self, qobuz_downloader, mock_album_response):
        """Test getting download info for an album."""
        qobuz_downloader._authenticated = True

        with (
            patch.object(
                qobuz_downloader.client,
                "get_album_info",
                return_value=mock_album_response,
            ),
            patch.object(
                qobuz_downloader,
                "_determine_content_type",
                return_value=ContentType.ALBUM,
            ),
        ):
            download_info = await qobuz_downloader.get_download_info("album123")

            assert download_info.content_type == ContentType.ALBUM
            assert download_info.title == "Test Album"
            assert download_info.artist == "Test Artist"
            assert download_info.format == "ALBUM"

    @pytest.mark.asyncio
    async def test_get_download_info_not_authenticated(self, qobuz_downloader):
        """Test getting download info without authentication."""
        with pytest.raises(AuthenticationError, match="Not authenticated with Qobuz"):
            await qobuz_downloader.get_download_info("123456")


class TestQobuzDownloaderUtilityMethods:
    """Test utility methods."""

    @pytest.mark.parametrize(
        ("content_id", "expected_type"),
        [
            ("123456", ContentType.TRACK),  # Short numeric ID
            ("1234567890", ContentType.TRACK),  # 10-digit numeric ID
            ("12345678901", ContentType.ALBUM),  # Longer ID
            ("abcdef123456", ContentType.ALBUM),  # Non-numeric ID
        ],
    )
    def test_determine_content_type(self, qobuz_downloader, content_id, expected_type):
        """Test content type determination from ID format."""
        result = qobuz_downloader._determine_content_type(content_id)
        assert result == expected_type

    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("Normal Filename", "Normal Filename"),
            ('Test<>:"/\\|?*Song', "Test_________Song"),
            ("A" * 150, "A" * 100),  # Long filename truncation
            ("  Filename with spaces  ", "Filename with spaces"),
        ],
    )
    def test_sanitize_filename(self, qobuz_downloader, filename, expected):
        """Test filename sanitization."""
        result = qobuz_downloader._sanitize_filename(filename)
        assert result == expected

    @pytest.mark.parametrize(
        ("date_string", "expected_year"),
        [
            ("2023-01-15", 2023),
            ("2023", 2023),
            ("2023-12-31T23:59:59", 2023),
            (None, None),
            ("invalid-date", None),
            ("", None),
        ],
    )
    def test_extract_year_from_date(self, qobuz_downloader, date_string, expected_year):
        """Test year extraction from date strings."""
        result = qobuz_downloader._extract_year_from_date(date_string)
        assert result == expected_year

    @pytest.mark.parametrize(
        ("format_id", "expected_bitrate"),
        [
            (5, 320),  # MP3 320
            (6, 1411),  # FLAC 16/44.1
            (7, 2304),  # FLAC 24/96
            (27, 4608),  # FLAC 24/192
            (999, None),  # Unknown format
        ],
    )
    def test_get_bitrate_for_quality(
        self, qobuz_downloader, format_id, expected_bitrate
    ):
        """Test bitrate mapping for quality formats."""
        result = qobuz_downloader._get_bitrate_for_quality(format_id)
        assert result == expected_bitrate

    @pytest.mark.parametrize(
        ("bit_depth", "sampling_rate", "expected_quality"),
        [
            (24, 96000.0, AudioQuality.HI_RES),
            (16, 44100.0, AudioQuality.LOSSLESS),
            (None, None, AudioQuality.HIGH),
            (8, 22050.0, AudioQuality.HIGH),
        ],
    )
    def test_map_qobuz_quality(
        self, qobuz_downloader, bit_depth, sampling_rate, expected_quality
    ):
        """Test quality mapping from Qobuz track info."""
        mock_track = MagicMock()
        mock_track.maximum_bit_depth = bit_depth
        mock_track.maximum_sampling_rate = sampling_rate

        result = qobuz_downloader._map_qobuz_quality(mock_track)
        assert result == expected_quality


class TestQobuzDownloaderDownloadOperations:
    """Test download operations."""

    @pytest.mark.asyncio
    async def test_download_content_success(self, qobuz_downloader):
        """Test successful content download."""
        qobuz_downloader._authenticated = True

        # Mock downloadable content
        content = DownloadableContent(
            content_id="123",
            content_type=ContentType.TRACK,
            source="qobuz",
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            url="https://example.com/track.flac",
            file_name="test_track",
            file_extension="flac",
            expected_size=None,
            checksum=None,
            quality="6",
            format="FLAC",
            bitrate=1411,
        )

        # Mock session and response
        mock_response = AsyncMock()
        mock_response.headers = {"Content-Length": "1000000"}

        # Create async iterator for chunks
        async def async_chunk_iterator():  # noqa: RUF029
            for chunk in [b"chunk1", b"chunk2", b"chunk3"]:
                yield chunk

        mock_response.content.iter_chunked = MagicMock(
            return_value=async_chunk_iterator()
        )
        mock_response.raise_for_status = MagicMock()

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_context_manager)

        progress_callback = MagicMock()

        async def mock_get_session(service_name):  # noqa: RUF029
            return mock_session

        with (
            patch.object(
                qobuz_downloader.session_manager,
                "get_session",
                side_effect=mock_get_session,
            ),
            patch("aiofiles.open", create=True) as mock_open,
        ):
            mock_file = AsyncMock()
            mock_open.return_value.__aenter__.return_value = mock_file

            await qobuz_downloader._download_content(
                content, "/path/to/file.flac", progress_callback
            )

            # Verify file operations
            mock_open.assert_called_once_with("/path/to/file.flac", "wb")
            assert mock_file.write.call_count == 3
            assert progress_callback.call_count == 3

    @pytest.mark.asyncio
    async def test_download_content_not_authenticated(self, qobuz_downloader):
        """Test download content without authentication."""
        content = MagicMock()

        with pytest.raises(AuthenticationError, match="Not authenticated with Qobuz"):
            await qobuz_downloader._download_content(content, "/path/to/file")

    @pytest.mark.asyncio
    async def test_download_album_success(self, qobuz_downloader, mock_album_response):
        """Test successful album download."""
        qobuz_downloader._authenticated = True

        # Mock album metadata
        mock_album = MagicMock()
        mock_album.track_ids = ["123", "456", "789"]
        mock_album.get_download_folder_name.return_value = "Test Artist - Test Album"
        mock_album.covers = MagicMock()
        mock_album.covers.has_images = True

        # Mock download results
        mock_result = DownloadResult(
            download_id=uuid4(),
            success=True,
            file_path="/path/to/track.flac",
            file_size=1000000,
            checksum=None,
            duration_seconds=5.0,
            average_speed_bps=200000,
            error_message=None,
            retry_count=0,
        )

        with (
            patch.object(
                qobuz_downloader, "get_album_metadata", return_value=mock_album
            ),
            patch.object(
                qobuz_downloader, "download_multiple", return_value=[mock_result] * 3
            ),
            patch.object(
                qobuz_downloader, "download_artwork", return_value=[mock_result]
            ),
            patch.object(
                qobuz_downloader, "download_booklets", return_value=[mock_result]
            ),
            patch.object(
                qobuz_downloader, "_get_track_download_info", return_value=MagicMock()
            ),
            patch("pathlib.Path.mkdir"),
        ):
            results = await qobuz_downloader.download_album(
                "album123", download_artwork=True, download_booklets=True
            )

            # Prefetch artwork no longer returns a DownloadResult entry
            assert len(results) == 4  # 3 tracks + 1 booklet
            assert all(r.success for r in results)

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


class TestQobuzDownloaderErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_download_content_http_error(self, qobuz_downloader):
        """Test download content with HTTP error."""
        qobuz_downloader._authenticated = True

        content = MagicMock()
        content.url = "https://example.com/track.flac"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientError("HTTP Error")

        # Create a proper async context manager mock
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_context_manager)

        async def mock_get_session(service_name):  # noqa: RUF029
            return mock_session

        with (
            patch.object(
                qobuz_downloader.session_manager,
                "get_session",
                side_effect=mock_get_session,
            ),
            pytest.raises(DownloadError, match="Failed to download content"),
        ):
            await qobuz_downloader._download_content(content, "/path/to/file")

    @pytest.mark.asyncio
    async def test_download_artist_discography_no_albums(self, qobuz_downloader):
        """Test downloading artist discography with no albums found."""
        qobuz_downloader._authenticated = True

        with (
            patch.object(qobuz_downloader, "search", return_value=[]),
            pytest.raises(ContentNotFoundError, match="No albums found for artist"),
        ):
            await qobuz_downloader.download_artist_discography("artist123")


class TestQobuzCredentialsModel:
    """Test QobuzCredentials model."""

    def test_credentials_creation_with_all_fields(self):
        """Test creating credentials with all fields."""
        creds = QobuzCredentials(
            email_or_userid="test@example.com",
            password_or_token="password123",
            app_id="123456789",
            secrets=["secret1", "secret2"],
            use_auth_token=True,
        )

        assert creds.email_or_userid == "test@example.com"
        assert creds.password_or_token == "password123"
        assert creds.app_id == "123456789"
        assert creds.secrets == ["secret1", "secret2"]
        assert creds.use_auth_token is True

    def test_credentials_creation_with_defaults(self):
        """Test creating credentials with default values."""
        creds = QobuzCredentials(
            email_or_userid="test@example.com",
            password_or_token="password123",
            app_id=None,
        )

        assert creds.app_id is None
        assert creds.secrets == []
        assert creds.use_auth_token is False

    @pytest.mark.parametrize(
        ("field_name", "field_value"),
        [
            ("email_or_userid", "user@test.com"),
            ("password_or_token", "secret_token"),
            ("app_id", "987654321"),
            ("use_auth_token", True),
        ],
    )
    def test_credentials_field_validation(self, field_name, field_value):
        """Test individual field validation."""
        base_data = {
            "email_or_userid": "test@example.com",
            "password_or_token": "password123",
            "app_id": None,
        }
        base_data[field_name] = field_value

        creds = QobuzCredentials(**base_data)
        assert getattr(creds, field_name) == field_value
