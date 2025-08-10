# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Metadata service for fetching and caching music metadata and artwork."""

import logging
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap

from ripstream.core.url_parser import ParsedURL
from ripstream.models.enums import ArtistItemFilter, StreamingSource
from ripstream.ui.metadata_fetcher import MetadataFetcher

logger = logging.getLogger(__name__)


class MetadataService(QObject):
    """Service for managing metadata fetching and caching."""

    metadata_ready = pyqtSignal(dict)  # metadata_dict
    album_ready = pyqtSignal(dict)  # album_metadata for progressive loading
    artwork_ready = pyqtSignal(str, QPixmap)  # item_id, pixmap
    progress_updated = pyqtSignal(int, str)  # progress_percent, status_message
    artist_progress_updated = pyqtSignal(
        int, int, str
    )  # remaining_items, total_items, service
    error_occurred = pyqtSignal(str)  # error_message

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.current_fetcher = None
        self.config = config

    def update_config(self, new_config):
        """Update the configuration used by this service."""
        self.config = new_config

    def fetch_metadata(
        self, parsed_url: ParsedURL, artist_item_filter: ArtistItemFilter | None = None
    ):
        """Start fetching metadata for a parsed URL."""
        # Stop any existing fetcher
        if self.current_fetcher and self.current_fetcher.isRunning():
            self.current_fetcher.terminate()
            self.current_fetcher.wait()

        # Prepare credentials based on the service
        credentials = self._get_credentials_for_service(parsed_url.service)

        # Create new fetcher with credentials
        self.current_fetcher = MetadataFetcher(
            parsed_url, credentials, artist_item_filter=artist_item_filter
        )
        self.current_fetcher.metadata_fetched.connect(self.metadata_ready.emit)
        self.current_fetcher.album_fetched.connect(self.album_ready.emit)
        self.current_fetcher.artwork_fetched.connect(self.artwork_ready.emit)
        self.current_fetcher.progress_updated.connect(self.progress_updated.emit)
        self.current_fetcher.artist_progress_updated.connect(
            self.artist_progress_updated.emit
        )
        self.current_fetcher.error_occurred.connect(self.error_occurred.emit)

        # Start fetching
        self.current_fetcher.start()

    def get_last_parsed_url(self) -> ParsedURL | None:
        """Return the last fetcher's parsed URL if available."""
        if self.current_fetcher and hasattr(self.current_fetcher, "parsed_url"):
            return self.current_fetcher.parsed_url
        return None

    def _get_credentials_for_service(
        self, service: StreamingSource
    ) -> dict[str, Any] | None:
        """Get credentials for a specific streaming service."""
        if not self.config:
            return None

        # Map service enum to config attribute name
        service_config_map = {
            StreamingSource.QOBUZ: "qobuz",
            StreamingSource.TIDAL: "tidal",
            StreamingSource.DEEZER: "deezer",
            StreamingSource.SOUNDCLOUD: "soundcloud",
            StreamingSource.YOUTUBE: "youtube",
        }

        config_attr = service_config_map.get(service)
        if not config_attr or not hasattr(self.config, config_attr):
            return None

        service_config = getattr(self.config, config_attr)

        # Use the service config's get_decoded_credentials method if available
        if hasattr(service_config, "get_decoded_credentials"):
            return service_config.get_decoded_credentials()

        # Fallback for services without the method
        return None

    def cancel_fetch(self):
        """Cancel the current metadata fetch operation."""
        if self.current_fetcher and self.current_fetcher.isRunning():
            self.current_fetcher.terminate()
            self.current_fetcher.wait()
            self.current_fetcher = None

    def cleanup(self):
        """Clean up resources."""
        self.cancel_fetch()
