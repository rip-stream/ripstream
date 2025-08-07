# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enhanced tests for Qobuz client with comprehensive coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.exceptions import (
    AuthenticationError,
    ContentNotFoundError,
    DownloadError,
    NetworkError,
)
from ripstream.downloader.qobuz.client import (
    QOBUZ_QUALITY_MAP,
    QobuzClient,
    QobuzSpoofer,
)
from ripstream.downloader.qobuz.models import (
    QobuzAlbumResponse,
    QobuzCredentials,
    QobuzDownloadInfo,
    QobuzPlaylistResponse,
    QobuzSearchResult,
    QobuzTrackResponse,
)
from ripstream.downloader.session import SessionManager


@pytest.fixture
def download_config():
    """Create test download configuration."""
    return DownloaderConfig()


@pytest.fixture
def session_manager(download_config):
    """Create test session manager."""
    return SessionManager(download_config)


@pytest.fixture
def qobuz_client(session_manager):
    """Create Qobuz client instance."""
    return QobuzClient(session_manager)


@pytest.fixture
def mock_credentials():
    """Create mock Qobuz credentials."""
    return QobuzCredentials(
        email_or_userid="test@example.com",
        password_or_token="test_password",
        app_id="123456789",
        secrets=["secret1", "secret2"],
        use_auth_token=False,
    )


@pytest.fixture
def mock_session():
    """Create mock aiohttp session."""
    return AsyncMock(spec=aiohttp.ClientSession)


@pytest.fixture
def mock_track_response_data():
    """Create mock track response data."""
    return {
        "id": "123456",
        "title": "Test Track",
        "version": None,
        "duration": 240,
        "track_number": 1,
        "disc_number": 1,
        "performer": {"name": "Test Artist", "id": 12345},
        "composer": {"name": "Test Composer", "id": 67890},
        "album": {"title": "Test Album", "artist": {"name": "Test Album Artist"}},
        "maximum_bit_depth": 24,
        "maximum_sampling_rate": 96000.0,
        "isrc": "TEST123456789",
        "copyright": "2023 Test Records",
        "parental_warning": False,
        "image": {"large": "https://example.com/cover_600.jpg"},
        "purchasable": True,
        "streamable": True,
        "previewable": True,
    }


@pytest.fixture
def mock_album_response_data():
    """Create mock album response data."""
    return {
        "id": "album123",
        "title": "Test Album",
        "version": "Deluxe Edition",
        "duration": 3600,
        "tracks_count": 12,
        "artist": {"name": "Test Artist", "id": 12345},
        "release_date_original": "2023-01-15",
        "maximum_bit_depth": 24,
        "maximum_sampling_rate": 96000.0,
        "label": {"name": "Test Records"},
        "upc": "123456789012",
        "genre": {"name": "Rock"},
        "genres_list": ["Rock", "Alternative"],
        "copyright": "2023 Test Records",
        "description": "A fantastic test album",
        "image": {"large": "https://example.com/album_600.jpg"},
        "tracks": {"items": [{"id": "123"}, {"id": "456"}, {"id": "789"}]},
        "goodies": [
            {
                "url": "https://example.com/booklet.pdf",
                "name": "Digital Booklet",
                "file_format_id": 21,
                "description": "Album booklet",
            }
        ],
        "purchasable": True,
        "streamable": True,
        "previewable": True,
    }


@pytest.fixture
def mock_playlist_response_data():
    """Create mock playlist response data."""
    return {
        "id": "playlist123",
        "name": "Test Playlist",
        "description": "A great test playlist",
        "duration": 1800,
        "tracks_count": 8,
        "owner": {"name": "Test User", "id": 54321},
        "is_public": True,
        "is_collaborative": False,
        "created_at": 1640995200,
        "updated_at": 1672531200,
        "tracks": {"items": [{"id": "111"}, {"id": "222"}]},
    }


class TestQobuzSpoofer:
    """Test QobuzSpoofer class."""

    @pytest.mark.asyncio
    async def test_get_app_id_and_secrets_success(self, mock_session):
        """Test successful app ID and secrets retrieval."""
        # Mock login page response
        login_page_html = """
        <html>
        <script src="/resources/1.0.0-a123/bundle.js"></script>
        </html>
        """

        # Mock bundle.js response
        bundle_js = """
        production:{api:{appId:"123456789",appSecret:"abcdef123456789012345678901234567890"
        a.initialSeed("seed1==",window.utimezone.berlin)
        a.initialSeed("seed2==",window.utimezone.london)
        name:"w+/Berlin",info:"info1==",extras:"extras1=="
        name:"w+/London",info:"info2==",extras:"extras2=="
        """

        # Mock responses
        login_response = AsyncMock()
        login_response.raise_for_status = MagicMock()
        login_response.text = AsyncMock(return_value=login_page_html)

        bundle_response = AsyncMock()
        bundle_response.raise_for_status = MagicMock()
        bundle_response.text = AsyncMock(return_value=bundle_js)

        # Create proper async context managers
        login_context = AsyncMock()
        login_context.__aenter__ = AsyncMock(return_value=login_response)
        login_context.__aexit__ = AsyncMock(return_value=None)

        bundle_context = AsyncMock()
        bundle_context.__aenter__ = AsyncMock(return_value=bundle_response)
        bundle_context.__aexit__ = AsyncMock(return_value=None)

        mock_session.get.side_effect = [login_context, bundle_context]

        spoofer = QobuzSpoofer(mock_session)

        with patch("base64.standard_b64decode", return_value=b"decoded_secret"):
            app_id, secrets = await spoofer.get_app_id_and_secrets()

        assert app_id == "123456789"
        assert isinstance(secrets, list)
        assert len(secrets) > 0

    @pytest.mark.asyncio
    async def test_get_app_id_and_secrets_no_bundle_url(self, mock_session):
        """Test failure when bundle URL is not found."""
        login_page_html = "<html>No bundle script here</html>"

        login_response = AsyncMock()
        login_response.raise_for_status = MagicMock()
        login_response.text = AsyncMock(return_value=login_page_html)

        # Create proper async context manager
        login_context = AsyncMock()
        login_context.__aenter__ = AsyncMock(return_value=login_response)
        login_context.__aexit__ = AsyncMock(return_value=None)

        mock_session.get.return_value = login_context

        spoofer = QobuzSpoofer(mock_session)

        with pytest.raises(DownloadError, match="Could not find bundle URL"):
            await spoofer.get_app_id_and_secrets()

    @pytest.mark.asyncio
    async def test_get_app_id_and_secrets_no_app_id(self, mock_session):
        """Test failure when app ID is not found in bundle."""
        login_page_html = """
        <html>
        <script src="/resources/1.0.0-a123/bundle.js"></script>
        </html>
        """

        bundle_js = 'production:{api:{something:"else"}} No app ID here'

        login_response = AsyncMock()
        login_response.raise_for_status = MagicMock()
        login_response.text = AsyncMock(return_value=login_page_html)

        bundle_response = AsyncMock()
        bundle_response.raise_for_status = MagicMock()
        bundle_response.text = AsyncMock(return_value=bundle_js)

        # Create proper async context managers
        login_context = AsyncMock()
        login_context.__aenter__ = AsyncMock(return_value=login_response)
        login_context.__aexit__ = AsyncMock(return_value=None)

        bundle_context = AsyncMock()
        bundle_context.__aenter__ = AsyncMock(return_value=bundle_response)
        bundle_context.__aexit__ = AsyncMock(return_value=None)

        mock_session.get.side_effect = [login_context, bundle_context]

        spoofer = QobuzSpoofer(mock_session)

        with pytest.raises(DownloadError, match="Could not find app ID"):
            await spoofer.get_app_id_and_secrets()


class TestQobuzClient:
    """Test QobuzClient class."""

    def test_initialization(self, qobuz_client, session_manager):
        """Test client initialization."""
        assert qobuz_client.session_manager == session_manager
        assert qobuz_client.credentials is None
        assert qobuz_client.user_auth_token is None
        assert qobuz_client.secret is None
        assert qobuz_client.logged_in is False

    @pytest.mark.asyncio
    async def test_authenticate_success(self, qobuz_client, mock_credentials):
        """Test successful authentication."""
        mock_response = {
            "user": {
                "credential": {"parameters": {"some": "data"}},
            },
            "user_auth_token": "test_auth_token",
        }

        with (
            patch.object(
                qobuz_client, "_api_request", return_value=(200, mock_response)
            ),
            patch.object(
                qobuz_client, "_get_valid_secret", return_value="valid_secret"
            ),
        ):
            result = await qobuz_client.authenticate(mock_credentials)

            assert result is True
            assert qobuz_client.logged_in is True
            assert qobuz_client.user_auth_token == "test_auth_token"
            assert qobuz_client.secret == "valid_secret"

    @pytest.mark.asyncio
    async def test_authenticate_with_spoofer(self, qobuz_client):
        """Test authentication when app ID/secrets need to be fetched."""
        credentials = QobuzCredentials(
            email_or_userid="test@example.com",
            password_or_token="test_password",
            app_id=None,  # Will trigger spoofer
            secrets=[],
        )

        mock_response = {
            "user": {
                "credential": {"parameters": {"some": "data"}},
            },
            "user_auth_token": "test_auth_token",
        }

        with (
            patch.object(
                qobuz_client, "_api_request", return_value=(200, mock_response)
            ),
            patch.object(
                qobuz_client, "_get_valid_secret", return_value="valid_secret"
            ),
            patch(
                "ripstream.downloader.qobuz.client.QobuzSpoofer"
            ) as mock_spoofer_class,
        ):
            mock_spoofer = AsyncMock()
            mock_spoofer.get_app_id_and_secrets.return_value = (
                "123456789",
                ["secret1"],
            )
            mock_spoofer_class.return_value = mock_spoofer

            result = await qobuz_client.authenticate(credentials)

            assert result is True
            assert credentials.app_id == "123456789"
            assert credentials.secrets == ["secret1"]

    @pytest.mark.parametrize(
        ("status_code", "expected_error"),
        [
            (401, "Invalid credentials"),
            (400, "Invalid app ID"),
            (500, "Login failed with status 500"),
        ],
    )
    @pytest.mark.asyncio
    async def test_authenticate_failure_status_codes(
        self, qobuz_client, mock_credentials, status_code, expected_error
    ):
        """Test authentication failure with different status codes."""
        with (
            patch.object(qobuz_client, "_api_request", return_value=(status_code, {})),
            pytest.raises(AuthenticationError, match=expected_error),
        ):
            await qobuz_client.authenticate(mock_credentials)

    @pytest.mark.asyncio
    async def test_authenticate_free_account(self, qobuz_client, mock_credentials):
        """Test authentication failure with free account."""
        mock_response = {
            "user": {
                "credential": {"parameters": None},  # Free account
            },
            "user_auth_token": "test_auth_token",
        }

        with (
            patch.object(
                qobuz_client, "_api_request", return_value=(200, mock_response)
            ),
            pytest.raises(AuthenticationError, match="Free accounts are not eligible"),
        ):
            await qobuz_client.authenticate(mock_credentials)

    @pytest.mark.asyncio
    async def test_get_track_info_success(
        self, qobuz_client, mock_credentials, mock_track_response_data
    ):
        """Test successful track info retrieval."""
        qobuz_client.logged_in = True
        qobuz_client.credentials = mock_credentials

        with patch.object(
            qobuz_client, "_api_request", return_value=(200, mock_track_response_data)
        ):
            track = await qobuz_client.get_track_info("123456")

            assert isinstance(track, QobuzTrackResponse)
            assert track.title == "Test Track"
            assert track.artist_name == "Test Artist"

    @pytest.mark.asyncio
    async def test_get_track_info_not_authenticated(self, qobuz_client):
        """Test track info retrieval without authentication."""
        with pytest.raises(AuthenticationError, match="Not authenticated with Qobuz"):
            await qobuz_client.get_track_info("123456")

    @pytest.mark.asyncio
    async def test_get_track_info_not_found(self, qobuz_client, mock_credentials):
        """Test track info retrieval for non-existent track."""
        qobuz_client.logged_in = True
        qobuz_client.credentials = mock_credentials

        with (
            patch.object(
                qobuz_client,
                "_api_request",
                return_value=(404, {"message": "Not found"}),
            ),
            pytest.raises(ContentNotFoundError, match="Error fetching track metadata"),
        ):
            await qobuz_client.get_track_info("nonexistent")

    @pytest.mark.asyncio
    async def test_get_album_info_success(
        self, qobuz_client, mock_credentials, mock_album_response_data
    ):
        """Test successful album info retrieval."""
        qobuz_client.logged_in = True
        qobuz_client.credentials = mock_credentials

        with patch.object(
            qobuz_client, "_api_request", return_value=(200, mock_album_response_data)
        ):
            album = await qobuz_client.get_album_info("album123")

            assert isinstance(album, QobuzAlbumResponse)
            assert album.title == "Test Album"
            assert album.artist_name == "Test Artist"

    @pytest.mark.asyncio
    async def test_get_playlist_info_success(
        self, qobuz_client, mock_credentials, mock_playlist_response_data
    ):
        """Test successful playlist info retrieval."""
        qobuz_client.logged_in = True
        qobuz_client.credentials = mock_credentials

        with patch.object(
            qobuz_client,
            "_api_request",
            return_value=(200, mock_playlist_response_data),
        ):
            playlist = await qobuz_client.get_playlist_info("playlist123")

            assert isinstance(playlist, QobuzPlaylistResponse)
            assert playlist.name == "Test Playlist"
            assert playlist.owner_name == "Test User"

    @pytest.mark.parametrize(
        ("media_type", "expected_key"),
        [
            ("track", "tracks"),
            ("album", "albums"),
            ("artist", "artists"),
            ("playlist", "playlists"),
        ],
    )
    @pytest.mark.asyncio
    async def test_search_success(self, qobuz_client, media_type, expected_key):
        """Test successful search for different media types."""
        qobuz_client.logged_in = True

        mock_search_data = {
            expected_key: {
                "items": [{"id": "1", "title": "Result 1"}],
                "total": 1,
                "limit": 50,
                "offset": 0,
            }
        }

        with patch.object(qobuz_client, "_paginate", return_value=[mock_search_data]):
            result = await qobuz_client.search("test query", media_type, 50)

            assert isinstance(result, QobuzSearchResult)
            assert result.query == "test query"
            assert hasattr(result, expected_key)

    @pytest.mark.asyncio
    async def test_search_invalid_media_type(self, qobuz_client):
        """Test search with invalid media type."""
        qobuz_client.logged_in = True

        with pytest.raises(ValueError, match="invalid_type not available for search"):
            await qobuz_client.search("test", "invalid_type")

    @pytest.mark.asyncio
    async def test_search_not_authenticated(self, qobuz_client):
        """Test search without authentication."""
        with pytest.raises(AuthenticationError, match="Not authenticated with Qobuz"):
            await qobuz_client.search("test query")

    @pytest.mark.parametrize(
        ("quality", "expected_format_id"),
        [
            (1, 5),  # MP3 320
            (2, 6),  # FLAC 16/44.1
            (3, 7),  # FLAC 24/96
            (4, 27),  # FLAC 24/192
            (999, 27),  # Unknown quality defaults to highest
        ],
    )
    @pytest.mark.asyncio
    async def test_get_download_info_success(
        self, qobuz_client, quality, expected_format_id
    ):
        """Test successful download info retrieval with different qualities."""
        qobuz_client.logged_in = True
        qobuz_client.secret = "test_secret"

        mock_response = {
            "url": "https://example.com/download/track.flac",
            "mime_type": "audio/flac",
            "restrictions": [],
        }

        with patch.object(
            qobuz_client, "_request_file_url", return_value=(200, mock_response)
        ):
            download_info = await qobuz_client.get_download_info("123456", quality)

            assert isinstance(download_info, QobuzDownloadInfo)
            assert download_info.url == "https://example.com/download/track.flac"
            assert download_info.format_id == expected_format_id

    @pytest.mark.asyncio
    async def test_get_download_info_not_authenticated(self, qobuz_client):
        """Test download info retrieval without authentication."""
        with pytest.raises(AuthenticationError, match="Not authenticated with Qobuz"):
            await qobuz_client.get_download_info("123456")

    @pytest.mark.asyncio
    async def test_get_download_info_with_restrictions(self, qobuz_client):
        """Test download info retrieval with restrictions."""
        qobuz_client.logged_in = True
        qobuz_client.secret = "test_secret"

        mock_response = {
            "url": None,
            "restrictions": [{"code": "TrackNotAvailable"}],
        }

        with (
            patch.object(
                qobuz_client, "_request_file_url", return_value=(200, mock_response)
            ),
            pytest.raises(DownloadError, match="Track not available"),
        ):
            await qobuz_client.get_download_info("123456")

    @pytest.mark.asyncio
    async def test_get_download_info_no_url(self, qobuz_client):
        """Test download info retrieval when no URL is available."""
        qobuz_client.logged_in = True
        qobuz_client.secret = "test_secret"

        mock_response = {"url": None, "restrictions": []}

        with (
            patch.object(
                qobuz_client, "_request_file_url", return_value=(200, mock_response)
            ),
            pytest.raises(DownloadError, match="No download URL available"),
        ):
            await qobuz_client.get_download_info("123456")

    @pytest.mark.asyncio
    async def test_api_request_success(self, qobuz_client):
        """Test successful API request."""
        mock_response_data = {"result": "success"}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)

        # Create proper async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_context)

        with patch.object(
            qobuz_client.session_manager,
            "get_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            status, data = await qobuz_client._api_request(
                "test/endpoint", {"param": "value"}
            )

            assert status == 200
            assert data == mock_response_data

    @pytest.mark.asyncio
    async def test_api_request_with_auth_headers(self, qobuz_client, mock_credentials):
        """Test API request with authentication headers."""
        qobuz_client.user_auth_token = "test_token"
        qobuz_client.credentials = mock_credentials

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})

        # Create proper async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_context)

        with patch.object(
            qobuz_client.session_manager,
            "get_session",
            new_callable=AsyncMock,
            return_value=mock_session,
        ):
            await qobuz_client._api_request("test/endpoint", {})

            # Verify headers were set
            call_args = mock_session.get.call_args
            headers = call_args[1]["headers"]
            assert headers["X-User-Auth-Token"] == "test_token"
            assert headers["X-App-Id"] == "123456789"

    @pytest.mark.asyncio
    async def test_api_request_network_error(self, qobuz_client):
        """Test API request with network error."""
        # Create a mock that raises an exception when used as async context manager
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.side_effect = aiohttp.ClientError(
            "Network error"
        )

        mock_session = MagicMock()
        mock_session.get.return_value = mock_context_manager

        async def mock_get_session(service_name):  # noqa: RUF029
            return mock_session

        with (
            patch.object(
                qobuz_client.session_manager,
                "get_session",
                side_effect=mock_get_session,
            ),
            pytest.raises(NetworkError, match="API request failed"),
        ):
            await qobuz_client._api_request("test/endpoint", {})

    @pytest.mark.asyncio
    async def test_request_file_url(self, qobuz_client):
        """Test file URL request with signature."""
        mock_response = {"url": "https://example.com/file.flac"}

        with (
            patch.object(
                qobuz_client, "_api_request", return_value=(200, mock_response)
            ),
            patch("time.time", return_value=1234567890),
        ):
            status, data = await qobuz_client._request_file_url("123456", 27, "secret")

            assert status == 200
            assert data == mock_response

    @pytest.mark.asyncio
    async def test_test_secret_valid(self, qobuz_client):
        """Test secret validation with valid secret."""
        with patch.object(qobuz_client, "_request_file_url", return_value=(200, {})):
            result = await qobuz_client._test_secret("valid_secret")
            assert result == "valid_secret"

    @pytest.mark.asyncio
    async def test_test_secret_invalid(self, qobuz_client):
        """Test secret validation with invalid secret."""
        with patch.object(qobuz_client, "_request_file_url", return_value=(400, {})):
            result = await qobuz_client._test_secret("invalid_secret")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_valid_secret_success(self, qobuz_client):
        """Test getting valid secret from list."""
        secrets = ["invalid1", "valid_secret", "invalid2"]

        async def mock_test_secret(secret):  # noqa: RUF029
            return secret if secret == "valid_secret" else None

        with patch.object(qobuz_client, "_test_secret", side_effect=mock_test_secret):
            result = await qobuz_client._get_valid_secret(secrets)
            assert result == "valid_secret"

    @pytest.mark.asyncio
    async def test_get_valid_secret_none_valid(self, qobuz_client):
        """Test getting valid secret when none are valid."""
        secrets = ["invalid1", "invalid2"]

        with (
            patch.object(qobuz_client, "_test_secret", return_value=None),
            pytest.raises(AuthenticationError, match="No valid secrets found"),
        ):
            await qobuz_client._get_valid_secret(secrets)

    @pytest.mark.asyncio
    async def test_paginate_single_page(self, qobuz_client):
        """Test pagination with single page of results."""
        mock_response = {
            "tracks": {
                "items": [{"id": "1"}, {"id": "2"}],
                "total": 2,
                "limit": 50,
                "offset": 0,
            }
        }

        with patch.object(
            qobuz_client, "_api_request", return_value=(200, mock_response)
        ):
            pages = await qobuz_client._paginate("track/search", {"query": "test"})

            assert len(pages) == 1
            assert pages[0] == mock_response

    @pytest.mark.asyncio
    async def test_paginate_multiple_pages(self, qobuz_client):
        """Test pagination with multiple pages."""
        page1 = {
            "tracks": {
                "items": [{"id": "1"}],
                "total": 3,
                "limit": 1,
                "offset": 0,
            }
        }
        page2 = {
            "tracks": {
                "items": [{"id": "2"}],
                "total": 3,
                "limit": 1,
                "offset": 1,
            }
        }
        page3 = {
            "tracks": {
                "items": [{"id": "3"}],
                "total": 3,
                "limit": 1,
                "offset": 2,
            }
        }

        # Mock the _api_request to return the first page, then subsequent pages
        async def mock_api_request(endpoint, params):  # noqa: RUF029
            offset = params.get("offset", 0)
            if offset == 0:
                return 200, page1
            if offset == 1:
                return 200, page2
            if offset == 2:
                return 200, page3
            return 404, {}

        with patch.object(qobuz_client, "_api_request", side_effect=mock_api_request):
            pages = await qobuz_client._paginate(
                "track/search", {"query": "test"}, limit=10
            )

            assert len(pages) == 3

    @pytest.mark.asyncio
    async def test_paginate_no_results(self, qobuz_client):
        """Test pagination with no results."""
        mock_response = {
            "tracks": {
                "items": [],
                "total": 0,
                "limit": 50,
                "offset": 0,
            }
        }

        with patch.object(
            qobuz_client, "_api_request", return_value=(200, mock_response)
        ):
            pages = await qobuz_client._paginate("track/search", {"query": "test"})

            assert len(pages) == 0

    @pytest.mark.asyncio
    async def test_paginate_error(self, qobuz_client):
        """Test pagination with API error."""
        with (
            patch.object(qobuz_client, "_api_request", return_value=(500, {})),
            pytest.raises(NetworkError, match="Pagination request failed"),
        ):
            await qobuz_client._paginate("track/search", {"query": "test"})

    @pytest.mark.asyncio
    async def test_close(self, qobuz_client, mock_credentials):
        """Test client cleanup."""
        # Set up client state
        qobuz_client.logged_in = True
        qobuz_client.user_auth_token = "test_token"
        qobuz_client.secret = "test_secret"
        qobuz_client.credentials = mock_credentials

        await qobuz_client.close()

        assert qobuz_client.logged_in is False
        assert qobuz_client.user_auth_token is None
        assert qobuz_client.secret is None
        assert qobuz_client.credentials is None


class TestQobuzQualityMapping:
    """Test Qobuz quality mapping constants."""

    def test_quality_map_values(self):
        """Test that quality map has expected values."""
        assert QOBUZ_QUALITY_MAP[1] == 5  # MP3 320
        assert QOBUZ_QUALITY_MAP[2] == 6  # FLAC 16/44.1
        assert QOBUZ_QUALITY_MAP[3] == 7  # FLAC 24/96
        assert QOBUZ_QUALITY_MAP[4] == 27  # FLAC 24/192

    def test_quality_map_get_with_default(self):
        """Test quality map get with default value."""
        assert (
            QOBUZ_QUALITY_MAP.get(999, 27) == 27
        )  # Unknown quality defaults to highest


class TestQobuzClientIntegration:
    """Integration tests for QobuzClient."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, qobuz_client, mock_credentials):
        """Test complete authentication flow."""
        # Mock successful login response
        login_response = {
            "user": {
                "credential": {"parameters": {"subscription": "premium"}},
            },
            "user_auth_token": "test_auth_token",
        }

        # Mock secret testing
        async def mock_test_secret(secret):  # noqa: RUF029
            return secret if secret == "secret1" else None

        with (
            patch.object(
                qobuz_client, "_api_request", return_value=(200, login_response)
            ),
            patch.object(qobuz_client, "_test_secret", side_effect=mock_test_secret),
        ):
            result = await qobuz_client.authenticate(mock_credentials)

            assert result is True
            assert qobuz_client.logged_in is True
            assert qobuz_client.user_auth_token == "test_auth_token"
            assert qobuz_client.secret == "secret1"

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, qobuz_client):
        """Test search with pagination integration."""
        qobuz_client.logged_in = True

        # Mock paginated search results
        page1 = {
            "tracks": {
                "items": [{"id": "1", "title": "Track 1"}],
                "total": 2,
                "limit": 1,
                "offset": 0,
            }
        }
        page2 = {
            "tracks": {
                "items": [{"id": "2", "title": "Track 2"}],
                "total": 2,
                "limit": 1,
                "offset": 1,
            }
        }

        with patch.object(qobuz_client, "_paginate", return_value=[page1, page2]):
            result = await qobuz_client.search("test query", "track", 2)

            assert isinstance(result, QobuzSearchResult)
            assert result.query == "test query"
            assert result.tracks is not None
            # Should combine results from both pages
            items = result.tracks.get("items", [])
            assert len(items) == 2
