# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Session management for downloads."""

import asyncio
import contextlib
import logging
import ssl
from types import TracebackType
from typing import Any, cast

import aiohttp
from aiohttp import ClientTimeout

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.exceptions import NetworkError
from ripstream.downloader.utils import raise_error

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages HTTP sessions for downloads."""

    def __init__(self, config: DownloaderConfig) -> None:
        self.config = config
        self._sessions: dict[str, aiohttp.ClientSession] = {}
        self._session_lock = asyncio.Lock()

    async def get_session(self, source: str | None = None) -> aiohttp.ClientSession:
        """Get or create a session for a specific source."""
        session_key = source or "default"

        async with self._session_lock:
            if session_key not in self._sessions or self._sessions[session_key].closed:
                self._sessions[session_key] = await self._create_session(source)

            return self._sessions[session_key]

    async def _create_session(self, source: str | None = None) -> aiohttp.ClientSession:
        """Create a new HTTP session."""
        # Get source-specific settings
        settings = self.config.get_behavior_for_source(source or "default")

        # Configure timeout
        timeout = ClientTimeout(
            total=settings.timeout_seconds,
            connect=settings.timeout_seconds / 2,
            sock_read=settings.timeout_seconds,
        )

        # Configure SSL context
        if not self.config.verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_param = ssl_context
        else:
            # Use default SSL verification (True)
            ssl_param = True

        # Configure connector
        connector = aiohttp.TCPConnector(
            limit=self.config.max_concurrent_downloads * 2,
            limit_per_host=self.config.max_concurrent_downloads,
            ssl=ssl_param,
        )

        # Prepare headers
        headers = {
            "User-Agent": self.config.user_agent,
        }

        # Add compression support
        if self.config.enable_compression:
            headers["Accept-Encoding"] = "gzip, deflate, br"

        # Add custom headers
        headers.update(self.config.custom_headers)

        # Add source-specific headers
        if source and source in self.config.source_settings:
            source_config = self.config.source_settings[source]
            if "headers" in source_config:
                headers.update(source_config["headers"])

        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers,
            raise_for_status=False,  # We'll handle status codes manually
        )

    async def close_session(self, source: str | None = None) -> None:
        """Close a specific session."""
        session_key = source or "default"

        async with self._session_lock:
            if session_key in self._sessions:
                session = self._sessions[session_key]
                if not session.closed:
                    await session.close()
                del self._sessions[session_key]

    async def close_all_sessions(self) -> None:
        """Close all sessions."""
        async with self._session_lock:
            for session in self._sessions.values():
                if not session.closed:
                    await session.close()
            self._sessions.clear()

    async def __aenter__(self) -> "SessionManager":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close_all_sessions()


class DownloadSession:
    """Represents a download session with retry logic and error handling."""

    def __init__(
        self,
        session_manager: SessionManager,
        source: str | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.source = source
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get the HTTP session."""
        if self._session is None or self._session.closed:
            self._session = await self.session_manager.get_session(self.source)
        return self._session

    async def head(self, url: str, **kwargs: object) -> aiohttp.ClientResponse:
        """Perform a HEAD request."""
        session = await self.get_session()
        try:
            response = await session.head(url, **kwargs)
            await self._check_response_status(response)
        except aiohttp.ClientError as e:
            msg = f"HEAD request failed: {e}"
            raise NetworkError(msg) from e
        else:
            return response

    async def get(
        self,
        url: str,
        stream: bool = False,
        **kwargs: object,
    ) -> aiohttp.ClientResponse:
        """Perform a GET request."""
        session = await self.get_session()
        try:
            if stream:
                # For streaming downloads, don't read the response body
                response = await session.get(url, **kwargs)
            else:
                response = await session.get(url, **kwargs)

            await self._check_response_status(response)
        except aiohttp.ClientError as e:
            msg = f"GET request failed: {e}"
            raise NetworkError(msg) from e
        else:
            return response

    async def download_stream(
        self,
        url: str,
        **kwargs: object,
    ) -> aiohttp.ClientResponse:
        """Start a streaming download."""
        session = await self.get_session()
        try:
            response = await session.get(url, **kwargs)
            await self._check_response_status(response)
        except aiohttp.ClientError as e:
            msg = f"Stream download failed: {e}"
            raise NetworkError(msg) from e
        else:
            return response

    async def get_content_info(self, url: str) -> dict[str, Any]:
        """Get content information without downloading."""
        response = await self.head(url)

        content_info = {
            "url": url,
            "status_code": response.status,
            "headers": dict(cast("Any", response.headers).items())
            if response.headers
            else {},
        }

        # Extract useful information
        if "content-length" in response.headers:
            content_info["size"] = int(response.headers["content-length"])

        if "content-type" in response.headers:
            content_info["content_type"] = response.headers["content-type"]

        if "last-modified" in response.headers:
            content_info["last_modified"] = response.headers["last-modified"]

        if "etag" in response.headers:
            content_info["etag"] = response.headers["etag"]

        # Check if server supports range requests
        content_info["supports_ranges"] = (
            response.headers.get("accept-ranges", "").lower() == "bytes"
        )

        response.close()
        return content_info

    async def download_chunk(
        self,
        url: str,
        start_byte: int,
        end_byte: int,
        **kwargs: object,
    ) -> bytes:
        """Download a specific byte range."""
        orig_headers = kwargs.get("headers", {})
        if not isinstance(orig_headers, dict):
            orig_headers = {}
        headers = orig_headers.copy()
        headers["Range"] = f"bytes={start_byte}-{end_byte}"
        kwargs["headers"] = headers

        response = await self.get(url, **kwargs)
        try:
            if response.status not in (206, 200):  # Partial Content or OK
                msg = f"Range request failed with status {response.status}"
                raise NetworkError(
                    msg,
                    status_code=response.status,
                )

            return await response.read()
        finally:
            response.close()

    async def _check_response_status(self, response: aiohttp.ClientResponse) -> None:
        """Check response status and raise appropriate exceptions."""
        if response.status < 400:
            return

        error_details = await self._build_error_details(response)
        self._raise_status_specific_exception(response.status, error_details)

    async def _build_error_details(
        self, response: aiohttp.ClientResponse
    ) -> dict[str, Any]:
        """Build error details dictionary from response."""
        error_details = {
            "url": str(response.url),
            "status_code": response.status,
            "headers": dict(cast("Any", response.headers).items())
            if response.headers
            else {},
        }

        # Try to get error message from response
        try:
            if response.content_type == "application/json":
                error_data = await response.json()
                error_details["response_data"] = error_data
            else:
                error_text = await response.text()
                if error_text:
                    error_details["response_text"] = error_text[:500]  # Limit size
        except (
            TimeoutError,
            aiohttp.ContentTypeError,
            aiohttp.ClientError,
            Exception,
        ) as e:
            logger.debug("Failed to parse error response content: %s", e)

        return error_details

    def _raise_status_specific_exception(
        self, status_code: int, error_details: dict[str, Any]
    ) -> None:
        """Raise appropriate exception based on HTTP status code."""
        if status_code == 401:
            self._raise_authentication_error(error_details)
        elif status_code == 403:
            self._raise_permission_error(error_details)
        elif status_code == 404:
            self._raise_not_found_error(error_details)
        elif status_code == 429:
            self._raise_rate_limit_error(error_details)
        elif 500 <= status_code < 600:
            self._raise_server_error(status_code, error_details)
        else:
            self._raise_generic_http_error(status_code, error_details)

    def _raise_authentication_error(self, error_details: dict[str, Any]) -> None:
        """Raise authentication error."""
        from ripstream.downloader.exceptions import AuthenticationError
        from ripstream.downloader.utils import raise_error

        msg = f"Authentication failed: {error_details['status_code']}"
        raise_error(AuthenticationError, msg, details=error_details)

    def _raise_permission_error(self, error_details: dict[str, Any]) -> None:
        """Raise permission error."""
        from ripstream.downloader.exceptions import DownloadPermissionError
        from ripstream.downloader.utils import raise_error

        msg = f"Access forbidden: {error_details['status_code']}"
        raise_error(DownloadPermissionError, msg, details=error_details)

    def _raise_not_found_error(self, error_details: dict[str, Any]) -> None:
        """Raise content not found error."""
        from ripstream.downloader.exceptions import ContentNotFoundError
        from ripstream.downloader.utils import raise_error

        msg = f"Content not found: {error_details['status_code']}"
        raise_error(ContentNotFoundError, msg, details=error_details)

    def _raise_rate_limit_error(self, error_details: dict[str, Any]) -> None:
        """Raise rate limit error."""
        from ripstream.downloader.exceptions import RateLimitError
        from ripstream.downloader.utils import raise_error

        retry_after = self._extract_retry_after(error_details["headers"])
        msg = f"Rate limit exceeded: {error_details['status_code']}"
        raise_error(RateLimitError, msg, retry_after=retry_after, details=error_details)

    def _raise_server_error(
        self, status_code: int, error_details: dict[str, Any]
    ) -> None:
        """Raise server error."""
        from ripstream.downloader.utils import raise_error

        msg = f"Server error: {status_code}"
        raise_error(NetworkError, msg, status_code=status_code, details=error_details)

    def _raise_generic_http_error(
        self, status_code: int, error_details: dict[str, Any]
    ) -> None:
        """Raise generic HTTP error."""
        msg = f"HTTP error: {status_code}"
        raise_error(NetworkError, msg, status_code=status_code, details=error_details)

    def _extract_retry_after(self, headers: dict[str, str]) -> float | None:
        """Extract retry-after value from headers."""
        retry_after_header = headers.get("retry-after")
        if retry_after_header is None:
            return None

        with contextlib.suppress(ValueError):
            return float(retry_after_header)
        return None

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def __aenter__(self) -> "DownloadSession":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()
