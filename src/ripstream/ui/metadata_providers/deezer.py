# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Deezer metadata provider implementation."""

import logging

from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_providers.base import BaseMetadataProvider, MetadataResult

logger = logging.getLogger(__name__)


class DeezerMetadataProvider(BaseMetadataProvider):
    """Deezer-specific metadata provider."""

    @property
    def service_name(self) -> str:
        """Get the name of the streaming service."""
        return "Deezer"

    @property
    def streaming_source(self) -> StreamingSource:
        """Get the StreamingSource enum value."""
        return StreamingSource.DEEZER

    async def authenticate(self) -> bool:
        """Authenticate with Deezer."""
        # TODO: Implement Deezer authentication
        logger.warning("Deezer authentication not yet implemented")
        self._authenticated = False
        return False

    async def fetch_artist_metadata(self, artist_id: str) -> MetadataResult:
        """Fetch artist metadata including albums, playlists, and tracks."""
        msg = "Deezer metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def fetch_album_metadata(self, album_id: str) -> MetadataResult:
        """Fetch album metadata including all tracks."""
        msg = "Deezer metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def fetch_track_metadata(self, track_id: str) -> MetadataResult:
        """Fetch individual track metadata."""
        msg = "Deezer metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def fetch_playlist_metadata(self, playlist_id: str) -> MetadataResult:
        """Fetch playlist metadata including all tracks."""
        msg = "Deezer metadata fetching not yet implemented"
        raise NotImplementedError(msg)

    async def cleanup(self) -> None:
        """Clean up resources."""
        # No resources to clean up for Deezer provider yet
