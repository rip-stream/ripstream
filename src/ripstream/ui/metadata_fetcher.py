# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Service-agnostic metadata fetcher for streaming services."""

import asyncio
import hashlib
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from ripstream.core.url_parser import ParsedURL
from ripstream.downloader.enums import ContentType
from ripstream.ui.metadata_providers.factory import MetadataProviderFactory

if TYPE_CHECKING:
    from ripstream.ui.metadata_providers.base import BaseMetadataProvider

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""


class MetadataFetcher(QThread):
    """Service-agnostic background thread for fetching metadata from streaming services."""

    metadata_fetched = pyqtSignal(dict)  # metadata_dict
    album_fetched = pyqtSignal(dict)  # album_metadata for progressive loading
    artwork_fetched = pyqtSignal(str, QPixmap)  # item_id, pixmap
    error_occurred = pyqtSignal(str)  # error_message
    progress_updated = pyqtSignal(int, str)  # progress_percent, status_message
    artist_progress_updated = pyqtSignal(
        int, int, str
    )  # remaining_items, total_items, service

    def __init__(
        self,
        parsed_url: ParsedURL,
        credentials: dict[str, Any] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.parsed_url = parsed_url
        self.credentials = credentials or {}
        self.cache_dir = Path.home() / ".cache" / "ripstream"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Create service-specific metadata provider
        self.provider: BaseMetadataProvider | None = None

        # Track background artwork tasks to prevent garbage collection
        self._artwork_tasks: set[asyncio.Task] = set()

        # Thread-safe counter for artist album fetching
        self._remaining_items_lock = threading.Lock()
        self._remaining_items = 0
        self._total_items = 0
        self._service_name = ""

    def run(self):
        """Run the metadata fetching process."""
        try:
            asyncio.run(self._fetch_metadata())
        except Exception as e:
            logger.exception("Failed to fetch metadata")
            self.error_occurred.emit(f"Failed to fetch metadata: {e!s}")

    async def _fetch_metadata(self):
        """Fetch metadata asynchronously using the appropriate provider."""
        try:
            self.progress_updated.emit(10, "Initializing metadata provider...")

            # Create provider for the service
            if not MetadataProviderFactory.is_service_supported(
                self.parsed_url.service
            ):
                self.error_occurred.emit(
                    f"Service {self.parsed_url.service.value} is not supported"
                )
                return

            self.provider = MetadataProviderFactory.create_provider(
                self.parsed_url.service, self.credentials
            )

            self.progress_updated.emit(20, "Authenticating with service...")

            # Authenticate with the service
            if not await self.provider.authenticate():
                self.error_occurred.emit(
                    f"Failed to authenticate with {self.provider.service_name}"
                )
                return

            self.progress_updated.emit(50, "Fetching metadata...")

            # Fetch metadata based on content type
            metadata_result = await self._fetch_content_metadata()

            self.progress_updated.emit(80, "Processing metadata...")

            # For artist content with streaming, emit initial metadata but skip artwork
            # since albums are being streamed individually with their own artwork
            content_type = metadata_result.data.get("content_type", "")
            metadata_result.data["service"] = self.parsed_url.service.value
            if content_type == "artist":
                self.progress_updated.emit(100, "Artist metadata fetched successfully")
                # Emit initial artist metadata to set up the UI, then albums stream individually
                self.metadata_fetched.emit(metadata_result.data)
            else:
                await self._fetch_artwork(metadata_result.data)
                self.progress_updated.emit(100, "Metadata fetched successfully")
                self.metadata_fetched.emit(metadata_result.data)

        except Exception as e:
            logger.exception("Failed to fetch metadata")
            self.error_occurred.emit(f"Failed to fetch metadata: {e!s}")
        finally:
            # Ensure all background artwork tasks complete before the loop exits
            try:
                await self._await_outstanding_artwork_tasks()
            except Exception:
                logger.exception("Error while awaiting outstanding artwork tasks")

            # Clean up provider resources
            if self.provider:
                try:
                    await self.provider.cleanup()
                except Exception:
                    logger.exception("Failed to cleanup provider")

    def _initialize_artist_counter(self, total_items: int, service_name: str) -> None:
        """Initialize the artist album counter in a thread-safe manner."""
        with self._remaining_items_lock:
            self._remaining_items = total_items
            self._total_items = total_items
            self._service_name = service_name

    def _decrement_remaining_items(self) -> None:
        """Decrement the remaining items counter and emit progress signal."""
        with self._remaining_items_lock:
            if self._remaining_items > 0:
                self._remaining_items -= 1
                self.artist_progress_updated.emit(
                    self._remaining_items, self._total_items, self._service_name
                )

    async def _fetch_content_metadata(self) -> Any:
        """Fetch metadata based on content type."""
        if not self.provider:
            msg = "Metadata provider not initialized"
            raise RuntimeError(msg)

        content_id = self.parsed_url.content_id

        if self.parsed_url.content_type == ContentType.ALBUM:
            return await self.provider.fetch_album_metadata(content_id)
        if self.parsed_url.content_type == ContentType.TRACK:
            return await self.provider.fetch_track_metadata(content_id)
        if self.parsed_url.content_type == ContentType.PLAYLIST:
            return await self.provider.fetch_playlist_metadata(content_id)
        if self.parsed_url.content_type == ContentType.ARTIST:
            # Use streaming approach for artist metadata to prevent UI blocking
            return await self.provider.fetch_artist_metadata_streaming(
                content_id,
                album_callback=self._on_album_fetched,
                counter_init_callback=self._initialize_artist_counter,
            )
        msg = f"Unsupported content type: {self.parsed_url.content_type}"
        raise ValueError(msg)

    def _on_album_fetched(self, album_metadata: dict[str, Any]):
        """Execute an action when an album is fetched."""
        # Emit the album_fetched signal to update UI progressively
        self.album_fetched.emit(album_metadata)

        # Decrement the remaining items counter only for artist fetching
        if self.parsed_url.content_type == ContentType.ARTIST:
            self._decrement_remaining_items()

        # Also fetch artwork for this individual album
        import asyncio

        try:
            # Check if there's a running event loop
            loop = asyncio.get_running_loop()
            # Store task reference to prevent garbage collection
            task = loop.create_task(self._fetch_album_artwork_async(album_metadata))
            self._artwork_tasks.add(task)

            # Remove task from set when it completes to prevent memory leaks
            task.add_done_callback(self._artwork_tasks.discard)
        except RuntimeError:
            # No event loop running, skip artwork fetching
            # This can happen during testing or when called outside async context
            pass

    async def _fetch_album_artwork_async(self, album_metadata: dict[str, Any]):
        """Fetch artwork for a single album asynchronously."""
        try:
            await self._fetch_album_artwork(album_metadata)
        except Exception:
            logger.exception("Failed to fetch artwork for album")

    async def _await_outstanding_artwork_tasks(self) -> None:
        """Await any outstanding artwork tasks to avoid cancellation on loop close."""
        if not self._artwork_tasks:
            return

        # Take a snapshot to avoid mutation during iteration
        pending_tasks = list(self._artwork_tasks)
        try:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        finally:
            # Remove completed tasks from tracking set
            for task in pending_tasks:
                self._artwork_tasks.discard(task)

    async def _fetch_artwork(self, metadata: dict[str, Any]):
        """Fetch artwork for items in metadata."""
        self.progress_updated.emit(80, "Fetching artwork...")

        content_type = metadata.get("content_type", "")
        logger.info("Fetching artwork for content_type: %s", content_type)

        if content_type == "album":
            await self._fetch_album_artwork(metadata)
        elif content_type == "artist":
            await self._fetch_artist_artwork(metadata)
        else:
            await self._fetch_items_artwork(metadata)

    async def _fetch_album_artwork(self, metadata: dict[str, Any]):
        """Fetch artwork for album content type."""
        album_info = metadata.get("album_info", {})
        items = metadata.get("items", [])

        if not album_info:
            return

        artwork_url = album_info.get("artwork_thumbnail")
        logger.info("Album artwork URL: %s", artwork_url)

        if not artwork_url:
            return

        album_id = album_info.get("id", items[0]["id"] if items else "unknown")
        pixmap = await self._download_artwork(album_id, artwork_url)

        if pixmap:
            logger.info(
                "Emitting artwork for album %s and %d tracks",
                album_id,
                len(items),
            )
            # Emit artwork for the album (using album_info id if available)
            self.artwork_fetched.emit(album_id, pixmap)

            # Also emit for all individual tracks so list view can use it if needed
            for item in items:
                self.artwork_fetched.emit(item["id"], pixmap)

    async def _fetch_artist_artwork(self, metadata: dict[str, Any]):
        """Fetch artwork for artist content type."""
        artist_info = metadata.get("artist_info", {})
        albums = metadata.get("items", [])

        # Fetch artist artwork
        await self._fetch_single_artwork(artist_info, "artwork_thumbnail")

        # Fetch album artworks
        for album in albums:
            await self._fetch_single_artwork(
                album.get("album_info"), "artwork_thumbnail"
            )

    async def _fetch_items_artwork(self, metadata: dict[str, Any]):
        """Fetch artwork for individual items."""
        items = metadata.get("items", [])
        logger.info("Fetching artwork for %d items", len(items))

        for item in items:
            artwork_url = item.get("artwork_url")
            logger.info("Item %s artwork URL: %s", item.get("id"), artwork_url)

            if artwork_url:
                pixmap = await self._download_artwork(item["id"], artwork_url)
                if pixmap:
                    logger.info("Emitting artwork for item %s", item["id"])
                    self.artwork_fetched.emit(item["id"], pixmap)
            else:
                logger.warning("No artwork URL for item %s", item.get("id"))

    async def _fetch_single_artwork(self, item_info: dict[str, Any], artwork_key: str):
        """Fetch artwork for a single item with the specified artwork key."""
        if not item_info or not item_info.get(artwork_key):
            return

        item_id = item_info.get("id", "unknown")
        artwork_url = item_info[artwork_key]

        pixmap = await self._download_artwork(item_id, artwork_url)
        if pixmap:
            self.artwork_fetched.emit(item_id, pixmap)

    async def _download_artwork(self, item_id: str, artwork_url: str) -> QPixmap | None:
        """Download and cache artwork."""
        try:
            # Create cache filename
            url_hash = hashlib.sha256(artwork_url.encode()).hexdigest()
            cache_file = self.cache_dir / f"artwork_{url_hash}.jpg"

            # Check if already cached
            if cache_file.exists():
                pixmap = QPixmap(str(cache_file))
                if not pixmap.isNull():
                    return pixmap

            # Download artwork from URL
            pixmap = await self._fetch_artwork_from_url(artwork_url)

            # If download failed, create placeholder
            if not pixmap or pixmap.isNull():
                pixmap = self._create_placeholder_artwork(item_id)

            # Save to cache
            if pixmap and not pixmap.isNull():
                pixmap.save(str(cache_file), "JPG")
        except Exception:
            logger.exception("Failed to fetch artwork %s", artwork_url)
            return self._create_placeholder_artwork(item_id)
        else:
            return pixmap

    async def _fetch_artwork_from_url(self, artwork_url: str) -> QPixmap | None:
        """Fetch artwork from URL using aiohttp."""
        async with (
            aiohttp.ClientSession() as session,
            session.get(
                artwork_url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response,
        ):
            if response.status == 200:
                image_data = await response.read()

                # Create QPixmap from image data
                pixmap = QPixmap()
                if pixmap.loadFromData(image_data):
                    return pixmap
                logger.warning("Failed to load image data from %s", artwork_url)
                return None
            logger.warning(
                "HTTP %d when fetching artwork from %s",
                response.status,
                artwork_url,
            )
            return None

    def _create_placeholder_artwork(self, item_id: str) -> QPixmap:
        """Create a placeholder artwork image."""
        from PyQt6.QtGui import QBrush, QColor, QFont, QPainter

        pixmap = QPixmap(300, 300)
        pixmap.fill(QColor("#f0f0f0"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle
        painter.setBrush(QBrush(QColor("#2196F3")))
        painter.setPen(QColor("#1976D2"))
        painter.drawEllipse(50, 50, 200, 200)

        # Draw text
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        painter.setFont(font)

        # Get first letter of item_id
        letter = item_id[0].upper() if item_id else "?"
        painter.drawText(50, 50, 200, 200, 0x84, letter)  # AlignCenter

        painter.end()
        return pixmap

    def _format_duration(self, duration_seconds: int | None) -> str:
        """Format duration in seconds to MM:SS format."""
        if not duration_seconds:
            return "0:00"

        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def _raise_authentication_error(self):
        """Raise authentication error."""
        msg = "Failed to authenticate with Qobuz"
        raise AuthenticationError(msg)

    async def cleanup(self):
        """Clean up resources."""
        # Cancel any pending artwork tasks
        for task in self._artwork_tasks.copy():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete or be cancelled
        if self._artwork_tasks:
            await asyncio.gather(*self._artwork_tasks, return_exceptions=True)

        self._artwork_tasks.clear()

        if self.provider:
            await self.provider.cleanup()

    async def _cleanup_resources(self):
        """Clean up resources from the provider."""
        if self.provider:
            await self.provider.cleanup()
