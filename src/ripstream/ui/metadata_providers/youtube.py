# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""YouTube metadata provider implementation."""

import logging

from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_providers.base import BaseMetadataProvider, MetadataResult

logger = logging.getLogger(__name__)


class YouTubeMetadataProvider(BaseMetadataProvider):
    """YouTube-specific metadata provider."""

    @property
    def service_name(self) -> str:
        """Get the name of the streaming service."""
        return "YouTube"

    @property
    def streaming_source(self) -> StreamingSource:
        """Get the StreamingSource enum value."""
        return StreamingSource.YOUTUBE

    async def authenticate(self) -> bool:
        """Authenticate with YouTube."""
        # YouTube typically doesn't require authentication for metadata
        logger.info("YouTube metadata access doesn't require authentication")
        self._authenticated = True
        return True

    async def fetch_artist_metadata(self, artist_id: str) -> MetadataResult:
        """Fetch artist metadata including albums, playlists, and tracks."""
        msg = "YouTube metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def fetch_album_metadata(self, album_id: str) -> MetadataResult:
        """Fetch album metadata including all tracks."""
        msg = "YouTube metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def fetch_track_metadata(self, track_id: str) -> MetadataResult:
        """Fetch individual track metadata."""
        msg = "YouTube metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def fetch_playlist_metadata(self, playlist_id: str) -> MetadataResult:
        """Fetch playlist metadata including all tracks."""
        msg = "YouTube metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def cleanup(self) -> None:
        """Clean up resources."""
        # No resources to clean up for YouTube provider yet
