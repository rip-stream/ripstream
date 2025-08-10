# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Deezer download provider.

Initial implementation supports preview downloads for tracks using
`deezer.Client` (public 30s MP3 preview URLs). This is a minimal adapter
that fits ripstream's provider framework and can be extended later to
support full-length downloads via authenticated flows.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import aiofiles
import aiohttp
import deezer

from ripstream.downloader.base import DownloadableContent, DownloadResult
from ripstream.downloader.enums import ContentType
from ripstream.downloader.exceptions import NetworkError
from ripstream.downloader.providers.base import (
    BaseDownloadProvider,
    DownloadProviderResult,
)
from ripstream.models.enums import StreamingSource

if TYPE_CHECKING:
    from ripstream.downloader.config import DownloaderConfig
    from ripstream.downloader.session import SessionManager

logger = logging.getLogger(__name__)


class DeezerDownloadProvider(BaseDownloadProvider):
    """Download provider for Deezer using public preview URLs.

    Notes
    -----
    - This implementation downloads the public 30-second MP3 preview for tracks.
    - Full-length downloads require features that are not provided by `deezer.Client`.
    - Albums/playlists/artists are not yet supported for multi-item downloads here.
    """

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker,
        credentials: dict[str, Any] | None = None,
    ):
        super().__init__(config, session_manager, progress_tracker, credentials)
        self.client: deezer.Client | None = None

    @property
    def service_name(self) -> str:
        """Get the provider name."""
        return "deezer"

    @property
    def streaming_source(self) -> StreamingSource:
        """Get the streaming source enum."""
        return StreamingSource.DEEZER

    @property
    def supported_content_types(self) -> list[ContentType]:
        """Return supported content types (preview track only)."""
        return [ContentType.TRACK]

    async def authenticate(self) -> bool:
        """Initialize `deezer.Client` and apply ARL cookie if provided.

        If `credentials` contains key `arl`, it is set on the underlying
        Deezer client cookies to enable account-scoped endpoints.
        """
        try:
            if self.client is None:
                self.client = deezer.Client()
            arl = (self.credentials or {}).get("arl")
            if isinstance(arl, str) and arl:
                # Set ARL cookie on the client for authenticated requests
                cookies = getattr(self.client, "cookies", None)
                if hasattr(cookies, "update"):
                    cookies.update({"arl": arl})
        except Exception:
            logger.exception("Failed to instantiate deezer.Client")
            self._authenticated = False
            return False
        else:
            self._authenticated = True
            return True

    async def _build_track_preview_content(self, track_id: str) -> DownloadableContent:
        """Build a DownloadableContent object for a track's preview URL."""
        if self.client is None:
            msg = "Client not initialized"
            raise RuntimeError(msg)
        track_res = await asyncio.to_thread(self.client.get_track, track_id)
        track = track_res.as_dict()
        title = track.get("title") or f"Track_{track_id}"
        artist = (track.get("artist") or {}).get("name")
        album = (track.get("album") or {}).get("title")
        preview_url = track.get("preview")
        if not preview_url:
            msg = "Preview URL not available for this track"
            raise RuntimeError(msg)

        # Try to prefetch size/head info via session manager
        expected_size: int | None = None
        try:
            info = await self.session_manager.get_content_info(preview_url)
            expected_size = info.get("size")
        except NetworkError:
            # Non-fatal; proceed without size
            expected_size = None

        file_name = f"{(artist or 'Unknown Artist')} - {title}"

        return DownloadableContent(
            content_id=str(track_id),
            content_type=ContentType.TRACK,
            source=self.service_name,
            title=title,
            artist=artist,
            album=album,
            url=preview_url,
            file_name=file_name,
            file_extension="mp3",
            expected_size=expected_size,
            checksum=None,
            checksum_algorithm="md5",
            quality="LOW",
            format="MP3",
            bitrate=128000,  # Approximate for previews
            metadata={"is_preview": True},
        )

    async def get_download_info(
        self, content_id: str, content_type: ContentType
    ) -> Any:
        """Return download information for the requested content (track only)."""
        if not self._authenticated:
            await self.authenticate()

        if content_type != ContentType.TRACK:
            msg = f"Unsupported content type for Deezer provider: {content_type.value}"
            raise ValueError(msg)

        return await self._build_track_preview_content(content_id)

    async def download_content(
        self,
        content_id: str,
        content_type: ContentType,
        download_directory: str | None = None,
        _progress_callback=None,
    ) -> DownloadProviderResult:
        """Download the specified content (track preview)."""
        if content_type != ContentType.TRACK:
            msg = f"Unsupported content type for Deezer provider: {content_type.value}"
            raise ValueError(msg)

        try:
            if not self._authenticated:
                await self.authenticate()

            content = await self._build_track_preview_content(content_id)

            # Resolve directory and target path
            base_dir = Path(download_directory or self.config.download_directory)
            base_dir.mkdir(parents=True, exist_ok=True)
            file_path = base_dir / content.get_safe_filename()

            # Download preview
            session = await self.session_manager.get_session(self.service_name)
            async with session.get(content.url) as resp:
                data = await resp.read()
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(data)

            # Compute checksum
            # MD5 used for preview integrity display only
            checksum = hashlib.md5(data).hexdigest()  # noqa: S324

            result = DownloadResult(
                download_id=uuid4(),
                success=True,
                file_path=str(file_path),
                file_size=len(data),
                checksum=checksum,
                duration_seconds=None,
                average_speed_bps=None,
                error_message=None,
                retry_count=0,
                metadata={
                    "content_id": content.content_id,
                    "content_type": content_type.value,
                    "source": self.service_name,
                    "is_preview": True,
                },
            )

            return self._create_download_result(
                True,
                [result],
                metadata={
                    "content_type": content_type.value,
                    "content_id": content_id,
                },
            )

        except (aiohttp.ClientError, OSError, RuntimeError) as e:
            logger.exception("Deezer download failed for content %s", content_id)
            return self._create_download_result(
                False,
                [],
                error_message=str(e),
                metadata={"content_type": content_type.value, "content_id": content_id},
            )

    async def cleanup(self) -> None:
        """Cleanup resources for provider."""
        self._authenticated = False
