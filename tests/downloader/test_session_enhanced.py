# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enhanced tests for download session management with comprehensive coverage."""

import asyncio
import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.exceptions import (
    AuthenticationError,
    ContentNotFoundError,
    DownloadPermissionError,
    NetworkError,
    RateLimitError,
)
from ripstream.downloader.session import DownloadSession, SessionManager


@pytest.fixture
def download_config():
    """Create a download configuration."""
    return DownloaderConfig(
        max_concurrent_downloads=5,
        verify_ssl=True,
        user_agent="test-agent/1.0",
        enable_compression=True,
        custom_headers={"X-Custom": "test"},
        source_settings={
            "test_source": {
                "timeout_seconds": 60,
                "headers": {"X-Source": "test"},
            }
        },
    )


@pytest.fixture
def session_manager(download_config):
    """Create a session manager."""
    return SessionManager(download_config)


@pytest.fixture
def download_session(session_manager):
    """Create a download session."""
    return DownloadSession(session_manager, source="test_source")


class TestSessionManager:
    """Test SessionManager class."""

    def test_session_manager_initialization(self, download_config):
        """Test session manager initialization."""
        manager = SessionManager(download_config)
        assert manager.config == download_config
        assert manager._sessions == {}
        assert isinstance(manager._session_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self, session_manager):
        """Test that get_session creates a new session."""
        with patch.object(session_manager, "_create_session") as mock_create:
            mock_session = AsyncMock(spec=aiohttp.ClientSession)
            mock_session.closed = False
            mock_create.return_value = mock_session

            session = await session_manager.get_session("test")

            assert session == mock_session
            mock_create.assert_called_once_with("test")
            assert session_manager._sessions["test"] == mock_session

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing_session(self, session_manager):
        """Test that get_session reuses existing open sessions."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        session_manager._sessions["test"] = mock_session

        session = await session_manager.get_session("test")

        assert session == mock_session

    @pytest.mark.asyncio
    async def test_get_session_recreates_closed_session(self, session_manager):
        """Test that get_session recreates closed sessions."""
        old_session = AsyncMock(spec=aiohttp.ClientSession)
        old_session.closed = True
        session_manager._sessions["test"] = old_session

        with patch.object(session_manager, "_create_session") as mock_create:
            new_session = AsyncMock(spec=aiohttp.ClientSession)
            new_session.closed = False
            mock_create.return_value = new_session

            session = await session_manager.get_session("test")

            assert session == new_session
            mock_create.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_get_session_default_source(self, session_manager):
        """Test get_session with default source."""
        with patch.object(session_manager, "_create_session") as mock_create:
            mock_session = AsyncMock(spec=aiohttp.ClientSession)
            mock_session.closed = False
            mock_create.return_value = mock_session

            session = await session_manager.get_session()

            assert session == mock_session
            mock_create.assert_called_once_with(None)
            assert session_manager._sessions["default"] == mock_session

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    @patch("aiohttp.TCPConnector")
    async def test_create_session_with_ssl_verification(
        self, mock_connector, mock_client_session, session_manager
    ):
        """Test session creation with SSL verification enabled."""
        mock_connector_instance = MagicMock()
        mock_connector.return_value = mock_connector_instance
        mock_session_instance = AsyncMock()
        mock_client_session.return_value = mock_session_instance

        await session_manager._create_session("test")

        # Verify connector configuration
        mock_connector.assert_called_once_with(
            limit=10,  # max_concurrent_downloads * 2
            limit_per_host=5,  # max_concurrent_downloads
            ssl=True,
        )

        # Verify session creation
        mock_client_session.assert_called_once()
        call_kwargs = mock_client_session.call_args[1]
        assert call_kwargs["connector"] == mock_connector_instance
        assert call_kwargs["raise_for_status"] is False

        # Check headers
        headers = call_kwargs["headers"]
        assert headers["User-Agent"] == "test-agent/1.0"
        assert headers["Accept-Encoding"] == "gzip, deflate, br"
        assert headers["X-Custom"] == "test"

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    @patch("aiohttp.TCPConnector")
    @patch("ssl.create_default_context")
    async def test_create_session_without_ssl_verification(
        self, mock_ssl_context, mock_connector, mock_client_session
    ):
        """Test session creation with SSL verification disabled."""
        config = DownloaderConfig(verify_ssl=False)
        manager = SessionManager(config)

        mock_ssl_ctx = MagicMock()
        mock_ssl_context.return_value = mock_ssl_ctx
        mock_connector_instance = MagicMock()
        mock_connector.return_value = mock_connector_instance
        mock_session_instance = AsyncMock()
        mock_client_session.return_value = mock_session_instance

        await manager._create_session()

        # Verify SSL context configuration
        mock_ssl_context.assert_called_once()
        assert mock_ssl_ctx.check_hostname is False
        assert mock_ssl_ctx.verify_mode == ssl.CERT_NONE

        # Verify connector uses custom SSL context
        mock_connector.assert_called_once()
        call_kwargs = mock_connector.call_args[1]
        assert call_kwargs["ssl"] == mock_ssl_ctx

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession")
    @patch("aiohttp.TCPConnector")
    async def test_create_session_with_source_settings(
        self, mock_connector, mock_client_session, session_manager
    ):
        """Test session creation with source-specific settings."""
        mock_connector_instance = MagicMock()
        mock_connector.return_value = mock_connector_instance
        mock_session_instance = AsyncMock()
        mock_client_session.return_value = mock_session_instance

        await session_manager._create_session("test_source")

        # Verify session creation with source-specific headers
        call_kwargs = mock_client_session.call_args[1]
        headers = call_kwargs["headers"]
        assert headers["X-Source"] == "test"
        assert (
            headers["X-Custom"] == "test"
        )  # Should include both custom and source headers

    @pytest.mark.asyncio
    async def test_close_session(self, session_manager):
        """Test closing a specific session."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        mock_session.close = AsyncMock()  # close() IS async in aiohttp
        session_manager._sessions["test"] = mock_session

        await session_manager.close_session("test")

        mock_session.close.assert_called_once()
        assert "test" not in session_manager._sessions

    @pytest.mark.asyncio
    async def test_close_session_already_closed(self, session_manager):
        """Test closing an already closed session."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = True
        mock_session.close = AsyncMock()  # close() IS async in aiohttp
        session_manager._sessions["test"] = mock_session

        await session_manager.close_session("test")

        mock_session.close.assert_not_called()
        assert "test" not in session_manager._sessions

    @pytest.mark.asyncio
    async def test_close_session_nonexistent(self, session_manager):
        """Test closing a non-existent session."""
        # Should not raise an exception
        await session_manager.close_session("nonexistent")

    @pytest.mark.asyncio
    async def test_close_session_default_source(self, session_manager):
        """Test closing session with default source."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        session_manager._sessions["default"] = mock_session

        await session_manager.close_session()

        mock_session.close.assert_called_once()
        assert "default" not in session_manager._sessions

    @pytest.mark.asyncio
    async def test_close_all_sessions(self, session_manager):
        """Test closing all sessions."""
        mock_session1 = AsyncMock(spec=aiohttp.ClientSession)
        mock_session1.closed = False
        mock_session2 = AsyncMock(spec=aiohttp.ClientSession)
        mock_session2.closed = False
        mock_session3 = AsyncMock(spec=aiohttp.ClientSession)
        mock_session3.closed = True  # Already closed

        session_manager._sessions = {
            "test1": mock_session1,
            "test2": mock_session2,
            "test3": mock_session3,
        }

        await session_manager.close_all_sessions()

        mock_session1.close.assert_called_once()
        mock_session2.close.assert_called_once()
        mock_session3.close.assert_not_called()
        assert session_manager._sessions == {}

    @pytest.mark.asyncio
    async def test_context_manager(self, download_config):
        """Test SessionManager as async context manager."""
        manager = SessionManager(download_config)

        with patch.object(manager, "close_all_sessions") as mock_close:
            async with manager as ctx_manager:
                assert ctx_manager == manager

            mock_close.assert_called_once()


class TestDownloadSession:
    """Test DownloadSession class."""

    def test_download_session_initialization(self, session_manager):
        """Test download session initialization."""
        session = DownloadSession(session_manager, "test_source")
        assert session.session_manager == session_manager
        assert session.source == "test_source"
        assert session._session is None

    @pytest.mark.asyncio
    async def test_get_session_first_call(self, download_session):
        """Test getting session on first call."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)

        with patch.object(download_session.session_manager, "get_session") as mock_get:
            mock_get.return_value = mock_session

            session = await download_session.get_session()

            assert session == mock_session
            assert download_session._session == mock_session
            mock_get.assert_called_once_with("test_source")

    @pytest.mark.asyncio
    async def test_get_session_reuse_existing(self, download_session):
        """Test reusing existing session."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        download_session._session = mock_session

        session = await download_session.get_session()

        assert session == mock_session

    @pytest.mark.asyncio
    async def test_get_session_recreate_closed(self, download_session):
        """Test recreating closed session."""
        old_session = AsyncMock(spec=aiohttp.ClientSession)
        old_session.closed = True
        download_session._session = old_session

        new_session = AsyncMock(spec=aiohttp.ClientSession)

        with patch.object(download_session.session_manager, "get_session") as mock_get:
            mock_get.return_value = new_session

            session = await download_session.get_session()

            assert session == new_session
            assert download_session._session == new_session

    @pytest.mark.asyncio
    async def test_head_request_success(self, download_session):
        """Test successful HEAD request."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_session.head = AsyncMock(return_value=mock_response)

        with (
            patch.object(download_session, "get_session", return_value=mock_session),
            patch.object(download_session, "_check_response_status") as mock_check,
        ):
            response = await download_session.head("https://example.com")

            assert response == mock_response
            mock_session.head.assert_called_once_with("https://example.com")
            mock_check.assert_called_once_with(mock_response)

    @pytest.mark.asyncio
    async def test_head_request_client_error(self, download_session):
        """Test HEAD request with client error."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.head.side_effect = aiohttp.ClientError("Connection failed")

        with (
            patch.object(download_session, "get_session", return_value=mock_session),
            pytest.raises(NetworkError, match="HEAD request failed"),
        ):
            await download_session.head("https://example.com")

    @pytest.mark.asyncio
    async def test_get_request_success(self, download_session):
        """Test successful GET request."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_session.get = AsyncMock(return_value=mock_response)

        with (
            patch.object(download_session, "get_session", return_value=mock_session),
            patch.object(download_session, "_check_response_status") as mock_check,
        ):
            response = await download_session.get("https://example.com")

            assert response == mock_response
            mock_session.get.assert_called_once_with("https://example.com")
            mock_check.assert_called_once_with(mock_response)

    @pytest.mark.asyncio
    async def test_get_request_with_stream(self, download_session):
        """Test GET request with streaming."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_session.get = AsyncMock(return_value=mock_response)

        with (
            patch.object(download_session, "get_session", return_value=mock_session),
            patch.object(download_session, "_check_response_status") as mock_check,
        ):
            response = await download_session.get("https://example.com", stream=True)

            assert response == mock_response
            mock_session.get.assert_called_once_with("https://example.com")
            mock_check.assert_called_once_with(mock_response)

    @pytest.mark.asyncio
    async def test_get_request_client_error(self, download_session):
        """Test GET request with client error."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")

        with (
            patch.object(download_session, "get_session", return_value=mock_session),
            pytest.raises(NetworkError, match="GET request failed"),
        ):
            await download_session.get("https://example.com")

    @pytest.mark.asyncio
    async def test_download_stream_success(self, download_session):
        """Test successful stream download."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_session.get = AsyncMock(return_value=mock_response)

        with (
            patch.object(download_session, "get_session", return_value=mock_session),
            patch.object(download_session, "_check_response_status") as mock_check,
        ):
            response = await download_session.download_stream("https://example.com")

            assert response == mock_response
            mock_session.get.assert_called_once_with("https://example.com")
            mock_check.assert_called_once_with(mock_response)

    @pytest.mark.asyncio
    async def test_download_stream_client_error(self, download_session):
        """Test stream download with client error."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")

        with (
            patch.object(download_session, "get_session", return_value=mock_session),
            pytest.raises(NetworkError, match="Stream download failed"),
        ):
            await download_session.download_stream("https://example.com")

    @pytest.mark.asyncio
    async def test_get_content_info_success(self, download_session):
        """Test successful content info retrieval."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_response.headers = {
            "content-length": "1024",
            "content-type": "audio/mpeg",
            "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
            "etag": '"abc123"',
            "accept-ranges": "bytes",
        }

        with patch.object(download_session, "head", return_value=mock_response):
            content_info = await download_session.get_content_info(
                "https://example.com"
            )

            expected_info = {
                "url": "https://example.com",
                "status_code": 200,
                "headers": {
                    "content-length": "1024",
                    "content-type": "audio/mpeg",
                    "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                    "etag": '"abc123"',
                    "accept-ranges": "bytes",
                },
                "size": 1024,
                "content_type": "audio/mpeg",
                "last_modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                "etag": '"abc123"',
                "supports_ranges": True,
            }

            assert content_info == expected_info
            mock_response.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_content_info_minimal_headers(self, download_session):
        """Test content info with minimal headers."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_response.headers = {}

        with patch.object(download_session, "head", return_value=mock_response):
            content_info = await download_session.get_content_info(
                "https://example.com"
            )

            expected_info = {
                "url": "https://example.com",
                "status_code": 200,
                "headers": {},
                "supports_ranges": False,
            }

            assert content_info == expected_info

    @pytest.mark.asyncio
    async def test_download_chunk_success(self, download_session):
        """Test successful chunk download."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 206  # Partial Content
        mock_response.read.return_value = b"chunk_data"

        with patch.object(download_session, "get", return_value=mock_response):
            chunk_data = await download_session.download_chunk(
                "https://example.com", 0, 1023
            )

            assert chunk_data == b"chunk_data"
            mock_response.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_chunk_with_existing_headers(self, download_session):
        """Test chunk download with existing headers."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 206
        mock_response.read.return_value = b"chunk_data"

        with patch.object(
            download_session, "get", return_value=mock_response
        ) as mock_get:
            await download_session.download_chunk(
                "https://example.com",
                0,
                1023,
                headers={"Authorization": "Bearer token"},
            )

            # Verify headers were merged correctly
            call_kwargs = mock_get.call_args[1]
            headers = call_kwargs["headers"]
            assert headers["Range"] == "bytes=0-1023"
            assert headers["Authorization"] == "Bearer token"

    @pytest.mark.asyncio
    async def test_download_chunk_invalid_status(self, download_session):
        """Test chunk download with invalid status code."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 416  # Range Not Satisfiable

        with patch.object(download_session, "get", return_value=mock_response):
            with pytest.raises(
                NetworkError, match="Range request failed with status 416"
            ):
                await download_session.download_chunk("https://example.com", 0, 1023)

            mock_response.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_response_status_success(self, download_session):
        """Test response status check for successful responses."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200

        # Should not raise any exception
        await download_session._check_response_status(mock_response)

    @pytest.mark.asyncio
    async def test_check_response_status_error(self, download_session):
        """Test response status check for error responses."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 404

        with (
            patch.object(download_session, "_build_error_details") as mock_build,
            patch.object(
                download_session, "_raise_status_specific_exception"
            ) as mock_raise,
        ):
            mock_build.return_value = {"status_code": 404}

            await download_session._check_response_status(mock_response)

            mock_build.assert_called_once_with(mock_response)
            mock_raise.assert_called_once_with(404, {"status_code": 404})

    @pytest.mark.asyncio
    async def test_build_error_details_json_response(self, download_session):
        """Test building error details from JSON response."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.url = "https://example.com"
        mock_response.status = 400
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content_type = "application/json"
        mock_response.json.return_value = {"error": "Bad request"}

        error_details = await download_session._build_error_details(mock_response)

        expected_details = {
            "url": "https://example.com",
            "status_code": 400,
            "headers": {"Content-Type": "application/json"},
            "response_data": {"error": "Bad request"},
        }

        assert error_details == expected_details

    @pytest.mark.asyncio
    async def test_build_error_details_text_response(self, download_session):
        """Test building error details from text response."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.url = "https://example.com"
        mock_response.status = 500
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.content_type = "text/plain"
        mock_response.text.return_value = "Internal server error"

        error_details = await download_session._build_error_details(mock_response)

        expected_details = {
            "url": "https://example.com",
            "status_code": 500,
            "headers": {"Content-Type": "text/plain"},
            "response_text": "Internal server error",
        }

        assert error_details == expected_details

    @pytest.mark.asyncio
    async def test_build_error_details_parse_error(self, download_session):
        """Test building error details when parsing fails."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.url = "https://example.com"
        mock_response.status = 400
        mock_response.headers = {}
        mock_response.content_type = "application/json"
        mock_response.json.side_effect = aiohttp.ContentTypeError(
            request_info=MagicMock(), history=()
        )

        error_details = await download_session._build_error_details(mock_response)

        expected_details = {
            "url": "https://example.com",
            "status_code": 400,
            "headers": {},
        }

        assert error_details == expected_details

    @pytest.mark.parametrize(
        ("status_code", "expected_exception"),
        [
            (401, AuthenticationError),
            (403, DownloadPermissionError),
            (404, ContentNotFoundError),
            (429, RateLimitError),
            (500, NetworkError),
            (502, NetworkError),
            (400, NetworkError),  # Generic HTTP error
        ],
    )
    def test_raise_status_specific_exception(
        self, download_session, status_code, expected_exception
    ):
        """Test raising status-specific exceptions."""
        error_details = {"status_code": status_code, "headers": {}}

        with pytest.raises(expected_exception):
            download_session._raise_status_specific_exception(
                status_code, error_details
            )

    def test_extract_retry_after_valid_number(self, download_session):
        """Test extracting valid retry-after header."""
        headers = {"retry-after": "60"}
        retry_after = download_session._extract_retry_after(headers)
        assert retry_after == 60.0

    def test_extract_retry_after_invalid_value(self, download_session):
        """Test extracting invalid retry-after header."""
        headers = {"retry-after": "invalid"}
        retry_after = download_session._extract_retry_after(headers)
        assert retry_after is None

    def test_extract_retry_after_missing_header(self, download_session):
        """Test extracting missing retry-after header."""
        headers = {}
        retry_after = download_session._extract_retry_after(headers)
        assert retry_after is None

    @pytest.mark.asyncio
    async def test_close_session(self, download_session):
        """Test closing download session."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = False
        download_session._session = mock_session

        await download_session.close()

        mock_session.close.assert_called_once()
        assert download_session._session is None

    @pytest.mark.asyncio
    async def test_close_session_already_closed(self, download_session):
        """Test closing already closed session."""
        mock_session = AsyncMock(spec=aiohttp.ClientSession)
        mock_session.closed = True
        download_session._session = mock_session

        await download_session.close()

        mock_session.close.assert_not_called()
        # Session is NOT set to None if already closed (per implementation)
        assert download_session._session == mock_session

    @pytest.mark.asyncio
    async def test_close_session_none(self, download_session):
        """Test closing when session is None."""
        download_session._session = None

        # Should not raise any exception
        await download_session.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, session_manager):
        """Test DownloadSession as async context manager."""
        session = DownloadSession(session_manager)

        with patch.object(session, "close") as mock_close:
            async with session as ctx_session:
                assert ctx_session == session

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_error_with_retry_after(self, download_session):
        """Test rate limit error with retry-after header."""
        error_details = {
            "status_code": 429,
            "headers": {"retry-after": "120"},
        }

        with pytest.raises(RateLimitError) as exc_info:
            download_session._raise_status_specific_exception(429, error_details)

        # The exception should have retry_after information
        assert "Rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_chunk_with_200_status(self, download_session):
        """Test chunk download with 200 OK status (full content)."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200  # OK instead of 206 Partial Content
        mock_response.read.return_value = b"full_content"

        with patch.object(download_session, "get", return_value=mock_response):
            chunk_data = await download_session.download_chunk(
                "https://example.com", 0, 1023
            )

            assert chunk_data == b"full_content"
            mock_response.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_error_details_long_text_truncation(self, download_session):
        """Test that long error text is truncated."""
        mock_response = AsyncMock(spec=aiohttp.ClientResponse)
        mock_response.url = "https://example.com"
        mock_response.status = 500
        mock_response.headers = {}
        mock_response.content_type = "text/plain"
        mock_response.text.return_value = "x" * 1000  # Long text

        error_details = await download_session._build_error_details(mock_response)

        # Should be truncated to 500 characters
        assert len(error_details["response_text"]) == 500
        assert error_details["response_text"] == "x" * 500
