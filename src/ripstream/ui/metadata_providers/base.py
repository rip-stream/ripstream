# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Base abstract classes for metadata providers."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.enums import ArtistItemFilter, StreamingSource
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track


class MetadataResult(BaseModel):
    """Result container for metadata fetching operations."""

    content_type: str = Field(
        ..., description="Type of content (album, track, playlist, artist)"
    )
    service: str = Field(..., description="Source service name")
    data: dict[str, Any] = Field(
        ..., description="Metadata dictionary for UI consumption"
    )
    raw_models: dict[str, Any] = Field(
        default_factory=dict, description="Raw model objects"
    )


class BaseMetadataProvider(ABC):
    """Abstract base class for all metadata providers."""

    def __init__(self, credentials: dict[str, Any] | None = None):
        """Initialize the metadata provider with optional credentials."""
        self.credentials = credentials or {}
        self._authenticated = False
        # Preference for which artist items to include when fetching artist content
        self.artist_item_filter: ArtistItemFilter = ArtistItemFilter.BOTH

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Get the name of the streaming service."""
        ...

    @property
    @abstractmethod
    def streaming_source(self) -> StreamingSource:
        """Get the StreamingSource enum value."""
        ...

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the streaming service."""
        ...

    @abstractmethod
    async def fetch_artist_metadata(self, artist_id: str) -> MetadataResult:
        """
        Fetch artist metadata.

        Including:
        - Artist info
        - List of albums
        - List of playlists (if applicable)
        - List of tracks under each album.
        """
        ...

    async def fetch_artist_metadata_streaming(
        self,
        artist_id: str,
        album_callback: Callable | None = None,  # noqa: ARG002
        counter_init_callback: Callable | None = None,  # noqa: ARG002
    ) -> MetadataResult:
        """
        Fetch artist metadata with streaming album results.

        This method returns basic artist info immediately and streams album data
        via the callback as each album is fetched.

        Args:
            artist_id: The artist ID to fetch
            album_callback: Optional callback function called for each album fetched
            counter_init_callback: Optional callback to initialize progress counter
                          Signature: callback(album_metadata: dict)

        Returns
        -------
            MetadataResult with artist info and empty items list initially
        """
        # Default implementation falls back to regular fetch_artist_metadata
        return await self.fetch_artist_metadata(artist_id)

    @abstractmethod
    async def fetch_album_metadata(self, album_id: str) -> MetadataResult:
        """
        Fetch album metadata.

        Including:
        - Album info
        - All tracks in the album.
        """
        ...

    @abstractmethod
    async def fetch_track_metadata(self, track_id: str) -> MetadataResult:
        """Fetch individual track metadata."""
        ...

    @abstractmethod
    async def fetch_playlist_metadata(self, playlist_id: str) -> MetadataResult:
        """
        Fetch playlist metadata.

        Including:
        - Playlist info
        - List of tracks and/or albums for each track.
        """
        ...

    async def fetch_playlist_metadata_streaming(
        self,
        playlist_id: str,
        album_callback: Callable | None = None,  # noqa: ARG002
        counter_init_callback: Callable | None = None,  # noqa: ARG002
    ) -> MetadataResult:
        """
        Fetch playlist metadata with streaming of albums referenced by the playlist.

        This default implementation falls back to the non-streaming
        fetch_playlist_metadata and returns a basic playlist item without
        streaming any albums. Providers should override to implement efficient
        album streaming for playlists.

        Args:
            playlist_id: The playlist ID to fetch
            album_callback: Optional callback invoked for each album fetched
            counter_init_callback: Optional callback to initialize progress counter

        Returns
        -------
            MetadataResult describing the playlist (items may be empty).
        """
        return await self.fetch_playlist_metadata(playlist_id)

    @property
    def is_authenticated(self) -> bool:
        """Check if the provider is authenticated."""
        return self._authenticated

    def _create_ui_track_item(
        self, track: Track, album: Album | None = None
    ) -> dict[str, Any]:
        """Create a standardized track item for UI consumption."""
        return {
            "id": track.info.id,
            "title": track.title,
            "artist": track.artist,
            "type": "Track",
            "year": album.info.release_year if album else None,
            "duration_formatted": track.duration_formatted or "0:00",
            "track_count": 1,
            "track_number": track.info.track_number,
            "album": album.title if album else track.album_id,
            "quality": str(track.audio.container) if track.audio.container else "FLAC",
            "container": str(track.audio.container)
            if track.audio.container
            else "FLAC",
            "audio_info": {
                "quality": int(track.audio.quality)
                if hasattr(track.audio, "quality") and track.audio.quality is not None
                else None,
                "bit_depth": track.audio.bit_depth,
                "sampling_rate": track.audio.sampling_rate,
                "bitrate": track.audio.bitrate,
                "codec": track.audio.codec,
                "container": track.audio.container,
                "duration_seconds": track.audio.duration_seconds,
                "file_size_bytes": track.audio.file_size_bytes,
                "is_lossless": track.audio.is_lossless,
                "is_explicit": bool(getattr(track.audio, "is_explicit", False)),
            },
            "artwork_url": (
                best_image.url
                if track.covers
                and (best_image := track.covers.get_best_image())
                and best_image
                else None
            ),
        }

    def _create_ui_album_item(self, album: Album) -> dict[str, Any]:
        """Create a standardized album item for UI consumption."""
        thumbnail = album.covers.get_best_image()
        return {
            "id": album.info.id,
            "title": album.title,
            "artist": album.artist,
            "type": "Album",
            "year": album.info.release_year,
            "duration_formatted": album.duration_formatted or "0:00",
            "track_count": album.info.total_tracks,
            "quality": "Mixed",  # Albums can have mixed quality
            "artwork_url": thumbnail.url if thumbnail else None,
        }

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources. Override in subclasses if needed."""

    def _create_ui_artist_item(self, artist: Artist) -> dict[str, Any]:
        """Create a standardized artist item for UI consumption."""
        thumbnail = artist.covers.get_best_image()
        return {
            "id": artist.info.id,
            "title": artist.name,
            "artist": artist.name,
            "type": "Artist",
            "year": artist.info.formed_year,
            "duration_formatted": "0:00",
            "track_count": artist.stats.total_albums,
            "quality": "Mixed",
            "artwork_url": thumbnail.url if thumbnail else None,
        }

    def _create_ui_playlist_item(self, playlist: Playlist) -> dict[str, Any]:
        """Create a standardized playlist item for UI consumption."""
        thumbnail = playlist.covers.get_best_image()
        return {
            "id": playlist.info.id,
            "title": playlist.name,
            "artist": playlist.info.owner or "Unknown",
            "type": "Playlist",
            "year": None,
            "duration_formatted": playlist.duration_formatted or "0:00",
            "track_count": playlist.info.total_tracks,
            "quality": "Mixed",
            "artwork_url": thumbnail.url if thumbnail else None,
        }
