# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Qobuz API client implementation."""

import asyncio
import base64
import hashlib
import logging
import re
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

import aiohttp

from ripstream.downloader.exceptions import (
    AuthenticationError,
    ContentNotFoundError,
    DownloadError,
    NetworkError,
)
from ripstream.downloader.qobuz.models import (
    QobuzAlbumResponse,
    QobuzArtistResponse,
    QobuzCredentials,
    QobuzDownloadInfo,
    QobuzPlaylistResponse,
    QobuzSearchResult,
    QobuzTrackResponse,
)
from ripstream.downloader.session import SessionManager
from ripstream.downloader.utils import raise_error

logger = logging.getLogger(__name__)

QOBUZ_BASE_URL = "https://www.qobuz.com/api.json/0.2"

# Quality mapping: internal quality -> Qobuz format_id
QOBUZ_QUALITY_MAP = {
    1: 5,  # MP3 320
    2: 6,  # FLAC 16/44.1
    3: 7,  # FLAC 24/96
    4: 27,  # FLAC 24/192
}

QOBUZ_FEATURED_KEYS = {
    "most-streamed",
    "recent-releases",
    "best-sellers",
    "press-awards",
    "ideal-discography",
    "editor-picks",
    "most-featured",
    "qobuzissims",
    "new-releases",
    "new-releases-full",
    "harmonia-mundi",
    "universal-classic",
    "universal-jazz",
    "universal-jeunesse",
    "universal-chanson",
}


class QobuzSpoofer:
    """Spoofs the information required to stream tracks from Qobuz."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Create a Spoofer."""
        self.session = session
        self.seed_timezone_regex = (
            r'[a-z]\.initialSeed\("(?P<seed>[\w=]+)",window\.ut'
            r"imezone\.(?P<timezone>[a-z]+)\)"
        )
        self.info_extras_regex = (
            r'name:"\w+/(?P<timezone>{timezones})",info:"'
            r'(?P<info>[\w=]+)",extras:"(?P<extras>[\w=]+)"'
        )
        self.app_id_regex = (
            r'production:{api:{appId:"(?P<app_id>\d{9})",appSecret:"(\w{32})'
        )

    async def get_app_id_and_secrets(self) -> tuple[str, list[str]]:
        """Get app ID and secrets from Qobuz web player."""
        async with self.session.get("https://play.qobuz.com/login") as req:
            req.raise_for_status()
            login_page = await req.text()

        bundle_url_match = re.search(
            r'<script src="(/resources/\d+\.\d+\.\d+-[a-z]\d{3}/bundle\.js)"></script>',
            login_page,
        )
        if bundle_url_match is None:
            msg = "Could not find bundle URL in login page"
            raise DownloadError(msg)

        bundle_url = bundle_url_match.group(1)

        async with self.session.get("https://play.qobuz.com" + bundle_url) as req:
            req.raise_for_status()
            bundle = await req.text()

        match = re.search(self.app_id_regex, bundle)
        if match is None:
            msg = "Could not find app ID in bundle"
            raise DownloadError(msg)

        app_id = str(match.group("app_id"))

        # Get secrets
        seed_matches = re.finditer(self.seed_timezone_regex, bundle)
        secrets = OrderedDict()
        for match in seed_matches:
            seed, timezone = match.group("seed", "timezone")
            secrets[timezone] = [seed]

        # Switch around the first and second timezone per ripstream logic
        keypairs = list(secrets.items())
        if len(keypairs) >= 2:
            secrets.move_to_end(keypairs[1][0], last=False)

        info_extras_regex = self.info_extras_regex.format(
            timezones="|".join(timezone.capitalize() for timezone in secrets),
        )
        info_extras_matches = re.finditer(info_extras_regex, bundle)
        for match in info_extras_matches:
            timezone, info, extras = match.group("timezone", "info", "extras")
            secrets[timezone.lower()] += [info, extras]

        for secret_pair in secrets:
            secrets[secret_pair] = base64.standard_b64decode(
                "".join(secrets[secret_pair])[:-44],
            ).decode("utf-8")

        vals: list[str] = list(secrets.values())
        if "" in vals:
            vals.remove("")

        return app_id, vals


class QobuzClient:
    """Qobuz API client."""

    def __init__(
        self,
        session_manager: SessionManager,
        config_update_callback: Callable[[str, list[str]], None] | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.config_update_callback = config_update_callback
        self.credentials: QobuzCredentials | None = None
        self.user_auth_token: str | None = None
        self.secret: str | None = None
        self.logged_in = False

    async def authenticate(self, credentials: QobuzCredentials) -> bool:
        """Authenticate with Qobuz."""
        self.credentials = credentials

        try:
            # Get app ID and secrets if not provided
            if not credentials.app_id or not credentials.secrets:
                logger.info("App ID/secrets not found, fetching from web player")
                session = await self.session_manager.get_session("qobuz")
                spoofer = QobuzSpoofer(session)
                (
                    credentials.app_id,
                    credentials.secrets,
                ) = await spoofer.get_app_id_and_secrets()

                # Save the retrieved secrets to config if callback is provided
                if self.config_update_callback and credentials.secrets:
                    logger.info("Saving retrieved secrets to config")
                    self.config_update_callback(credentials.app_id, credentials.secrets)

            # Prepare login parameters
            if credentials.use_auth_token:
                params = {
                    "user_id": credentials.email_or_userid,
                    "user_auth_token": credentials.password_or_token,
                    "app_id": str(credentials.app_id),
                }
            else:
                params = {
                    "email": credentials.email_or_userid,
                    "password": credentials.password_or_token,
                    "app_id": str(credentials.app_id),
                }

            # Perform login
            status, resp = await self._api_request("user/login", params)

            if status == 401:
                msg = f"Invalid credentials: {params}"
                raise_error(AuthenticationError, msg)
            if status == 400:
                msg = f"Invalid app ID: {params}"
                raise_error(AuthenticationError, msg)
            if status != 200:
                msg = f"Login failed with status {status}: {resp}"
                raise_error(AuthenticationError, msg)

            # Check if account is eligible
            if not resp["user"]["credential"]["parameters"]:
                msg = "Free accounts are not eligible to download tracks"
                raise_error(AuthenticationError, msg)

            # Store auth token
            self.user_auth_token = resp["user_auth_token"]

            # Get valid secret
            self.secret = await self._get_valid_secret(credentials.secrets)

            self.logged_in = True
            logger.info("Successfully authenticated with Qobuz")
        except Exception:
            logger.exception("Qobuz authentication failed")
            self.logged_in = False
            raise
        else:
            return True

    async def get_track_info(self, track_id: str) -> QobuzTrackResponse:
        """Get track information."""
        if not self.logged_in:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        if not self.credentials or not self.credentials.app_id:
            msg = "Missing app ID in credentials"
            raise AuthenticationError(msg)

        params = {
            "app_id": str(self.credentials.app_id),
            "track_id": track_id,
        }

        status, resp = await self._api_request("track/get", params)

        if status != 200:
            msg = f'Error fetching track metadata: "{resp.get("message", "Unknown error")}"'
            raise ContentNotFoundError(msg)

        return QobuzTrackResponse(**resp, raw_data=resp)

    async def get_album_info(self, album_id: str) -> QobuzAlbumResponse:
        """Get album information."""
        if not self.logged_in:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        if not self.credentials or not self.credentials.app_id:
            msg = "Missing app ID in credentials"
            raise AuthenticationError(msg)

        params = {
            "app_id": str(self.credentials.app_id),
            "album_id": album_id,
            "limit": 500,
            "offset": 0,
        }

        status, resp = await self._api_request("album/get", params)

        if status != 200:
            msg = f'Error fetching album metadata: "{resp.get("message", "Unknown error")}"'
            raise ContentNotFoundError(msg)

        return QobuzAlbumResponse(**resp, raw_data=resp)

    async def get_playlist_info(self, playlist_id: str) -> QobuzPlaylistResponse:
        """Get playlist information."""
        if not self.logged_in:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        if not self.credentials or not self.credentials.app_id:
            msg = "Missing app ID in credentials"
            raise AuthenticationError(msg)

        params = {
            "app_id": str(self.credentials.app_id),
            "playlist_id": playlist_id,
            "extra": "tracks",
            "limit": 500,
            "offset": 0,
        }

        status, resp = await self._api_request("playlist/get", params)

        if status != 200:
            msg = f'Error fetching playlist metadata: "{resp.get("message", "Unknown error")}"'
            raise ContentNotFoundError(msg)

        return QobuzPlaylistResponse(**resp, raw_data=resp)

    async def get_artist_info(self, artist_id: str) -> QobuzArtistResponse:
        """Get artist information."""
        if not self.logged_in:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        if not self.credentials or not self.credentials.app_id:
            msg = "Missing app ID in credentials"
            raise AuthenticationError(msg)

        params = {
            "app_id": str(self.credentials.app_id),
            "artist_id": artist_id,
            "extra": "albums",
            "limit": 500,
            "offset": 0,
        }

        status, resp = await self._api_request("artist/get", params)

        if status != 200:
            msg = f'Error fetching artist metadata: "{resp.get("message", "Unknown error")}"'
            raise ContentNotFoundError(msg)

        return QobuzArtistResponse(**resp, raw_data=resp)

    async def search(
        self, query: str, media_type: str = "track", limit: int = 50
    ) -> QobuzSearchResult:
        """Search for content."""
        if not self.logged_in:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        if media_type not in ("artist", "album", "track", "playlist"):
            msg = f"{media_type} not available for search on Qobuz"
            raise ValueError(msg)

        params = {
            "query": query,
            "limit": limit,
        }

        endpoint = f"{media_type}/search"
        pages = await self._paginate(endpoint, params, limit=limit)

        # Combine results from all pages
        result_data: dict[str, Any] = {"query": query}
        key = f"{media_type}s"

        if pages:
            result_data[key] = pages[0].get(key, {})
            if len(pages) > 1:
                page_data = result_data[key]
                if isinstance(page_data, dict):
                    items = page_data.get("items", [])
                    for page in pages[1:]:
                        page_items = page.get(key, {})
                        if isinstance(page_items, dict):
                            items.extend(page_items.get("items", []))
                    page_data["items"] = items

        return QobuzSearchResult(**result_data)

    async def get_download_info(
        self, track_id: str, quality: int = 4
    ) -> QobuzDownloadInfo:
        """Get download information for a track."""
        if not self.logged_in or not self.secret:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        format_id = QOBUZ_QUALITY_MAP.get(quality, 27)
        status, resp = await self._request_file_url(track_id, format_id, self.secret)

        if status != 200:
            msg = f"Failed to get download URL: {resp}"
            raise DownloadError(msg)

        url = resp.get("url")
        restrictions = resp.get("restrictions", [])

        if url is None:
            if restrictions:
                # Turn CamelCase code into a readable sentence
                words = re.findall(r"([A-Z][a-z]+)", restrictions[0]["code"])
                msg = words[0] + " " + " ".join(map(str.lower, words[1:])) + "."
                raise DownloadError(msg)
            msg = "No download URL available"
            raise DownloadError(msg)

        return QobuzDownloadInfo(
            url=url,
            format_id=format_id,
            mime_type=resp.get(
                "mime_type", "audio/flac" if quality > 1 else "audio/mpeg"
            ),
            restrictions=restrictions,
        )

    async def _api_request(
        self, endpoint: str, params: dict[str, Any]
    ) -> tuple[int, dict[str, Any]]:
        """Make a request to the Qobuz API."""
        url = f"{QOBUZ_BASE_URL}/{endpoint}"

        session = await self.session_manager.get_session("qobuz")

        # Add auth token to headers if available
        headers = {}
        if self.user_auth_token:
            headers["X-User-Auth-Token"] = self.user_auth_token
        if self.credentials and self.credentials.app_id:
            headers["X-App-Id"] = str(self.credentials.app_id)

        try:
            async with session.get(url, params=params, headers=headers) as response:
                return response.status, await response.json()
        except Exception as e:
            msg = f"API request failed: {e}"
            raise NetworkError(msg) from e

    async def _request_file_url(
        self,
        track_id: str,
        format_id: int,
        secret: str,
    ) -> tuple[int, dict[str, Any]]:
        """Request file URL with signature."""
        unix_ts = time.time()
        r_sig = f"trackgetFileUrlformat_id{format_id}intentstreamtrack_id{track_id}{unix_ts}{secret}"
        r_sig_hashed = hashlib.md5(r_sig.encode("utf-8")).hexdigest()  # noqa: S324

        params = {
            "request_ts": unix_ts,
            "request_sig": r_sig_hashed,
            "track_id": track_id,
            "format_id": format_id,
            "intent": "stream",
        }

        return await self._api_request("track/getFileUrl", params)

    async def _test_secret(self, secret: str) -> str | None:
        """Test if a secret is valid."""
        status, _ = await self._request_file_url("19512574", 27, secret)
        if status == 400:
            return None
        if status in (200, 401):
            return secret
        logger.warning("Got status %d when testing secret", status)
        return None

    async def _get_valid_secret(self, secrets: list[str]) -> str:
        """Get a valid secret from the list."""
        results = await asyncio.gather(
            *[self._test_secret(secret) for secret in secrets],
            return_exceptions=True,
        )

        working_secrets = [r for r in results if isinstance(r, str)]
        if not working_secrets:
            msg = f"No valid secrets found from {len(secrets)} candidates"
            raise AuthenticationError(msg)

        return working_secrets[0]

    async def _paginate(
        self,
        endpoint: str,
        params: dict[str, Any],
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Paginate search results."""
        params.update({"limit": limit})
        status, page = await self._api_request(endpoint, params)

        if status != 200:
            msg = f"Pagination request failed with status {status}"
            raise NetworkError(msg)

        # Get the key for items (albums, tracks, etc.)
        key = endpoint.split("/")[0] + "s"
        items = page.get(key, {})
        total = items.get("total", 0)

        if limit is not None and limit < total:
            total = limit

        if total == 0:
            logger.debug("Nothing found from %s endpoint", endpoint)
            return []

        page_limit = int(items.get("limit", 500))
        offset = int(items.get("offset", 0))

        pages = [page]
        requests = []

        while (offset + page_limit) < total:
            offset += page_limit
            new_params = params.copy()
            new_params.update({"offset": offset})
            requests.append(self._api_request(endpoint, new_params))

        for status, resp in await asyncio.gather(*requests):
            if status == 200:
                pages.append(resp)

        return pages

    async def close(self) -> None:
        """Close the client and cleanup resources."""
        self.logged_in = False
        self.user_auth_token = None
        self.secret = None
        self.credentials = None
