# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Qobuz metadata provider implementation."""

import logging
from typing import Any

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.qobuz.downloader import QobuzDownloader
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import ArtistItemFilter, CoverSize, StreamingSource
from ripstream.ui.metadata_providers.base import BaseMetadataProvider, MetadataResult

logger = logging.getLogger(__name__)


class QobuzMetadataProvider(BaseMetadataProvider):
    """Qobuz-specific metadata provider."""

    def __init__(self, credentials: dict[str, Any] | None = None):
        """Initialize Qobuz metadata provider."""
        super().__init__(credentials)

        # Initialize downloader components
        self.download_config = DownloaderConfig()
        self.session_manager = SessionManager(self.download_config)
        self.progress_tracker = ProgressTracker()
        self.qobuz_downloader: QobuzDownloader | None = None
        # Cache for albums prefetched during streaming filtering to avoid refetch
        self._prefetched_albums: dict[str, Any] = {}

    @property
    def service_name(self) -> str:
        """Get the name of the streaming service."""
        return "Qobuz"

    @property
    def streaming_source(self) -> StreamingSource:
        """Get the StreamingSource enum value."""
        return StreamingSource.QOBUZ

    async def authenticate(self) -> bool:
        """Authenticate with Qobuz."""
        try:
            if self.qobuz_downloader is None:
                self.qobuz_downloader = QobuzDownloader(
                    self.download_config, self.session_manager, self.progress_tracker
                )

            if self.credentials:
                self._authenticated = await self.qobuz_downloader.authenticate(
                    self.credentials
                )
            else:
                self._authenticated = False
        except Exception:
            logger.exception("Failed to authenticate with Qobuz")
            self._authenticated = False
            return False
        else:
            return self._authenticated

    async def fetch_artist_metadata(self, artist_id: str) -> MetadataResult:
        """Fetch artist metadata including albums, playlists, and tracks."""
        if not self._authenticated or not self.qobuz_downloader:
            msg = "Not authenticated with Qobuz"
            raise RuntimeError(msg)

        # Get artist metadata
        artist = await self.qobuz_downloader.get_artist_metadata(artist_id)

        # Get artist thumbnail
        thumbnail = artist.covers.get_best_image([CoverSize.SMALL, CoverSize.MEDIUM])

        # Fetch detailed metadata for each album using existing fetch_album_metadata
        albums = []
        singles = []

        for album_id in artist.album_ids:
            try:
                album_metadata = await self.fetch_album_metadata(album_id)
                album_item = album_metadata.data

                # Determine if it's an album or single based on track count
                track_count = album_item.get("album_info", {}).get("total_tracks", 0)
                if track_count <= 3:  # Consider 3 or fewer tracks as singles
                    singles.append(album_item)
                else:
                    albums.append(album_item)

            except Exception:
                logger.exception(
                    "Failed to fetch album metadata for album %s", album_id
                )
                continue

        # Apply filtering based on preference
        if self.artist_item_filter == ArtistItemFilter.ALBUMS_ONLY:
            items = albums
            total_albums = len(albums)
            total_singles = 0
        elif self.artist_item_filter == ArtistItemFilter.SINGLES_ONLY:
            items = singles
            total_albums = 0
            total_singles = len(singles)
        else:
            items = albums + singles
            total_albums = len(albums)
            total_singles = len(singles)

        return MetadataResult(
            content_type="artist",
            service=self.service_name,
            data={
                "content_type": "artist",
                "id": artist_id,
                "artist_info": {
                    "id": artist_id,
                    "name": artist.name,
                    "biography": artist.info.biography,
                    "total_albums": total_albums,
                    "total_singles": total_singles,
                    "total_items": len(items),
                    "artwork_thumbnail": thumbnail.url if thumbnail else None,
                },
                "items": items,
                "album_ids": artist.album_ids,
            },
            raw_models={
                "artist": artist,
                "albums": albums,
                "singles": singles,
            },
        )

    async def fetch_artist_metadata_streaming(
        self, artist_id: str, album_callback=None, counter_init_callback=None
    ) -> MetadataResult:
        """Fetch artist metadata with streaming album results to prevent UI blocking."""
        if not self._authenticated or not self.qobuz_downloader:
            msg = "Not authenticated with Qobuz"
            raise RuntimeError(msg)

        # Get artist metadata
        artist = await self.qobuz_downloader.get_artist_metadata(artist_id)

        # Get artist thumbnail
        thumbnail = artist.covers.get_best_image([CoverSize.SMALL, CoverSize.MEDIUM])

        # Pre-filter album IDs using lightweight album info fetch with caching
        filtered_album_ids = (
            await self._prefilter_album_ids(artist.album_ids)
            if album_callback
            else artist.album_ids
        )

        # Return initial artist info immediately reflecting filtered list
        initial_result = MetadataResult(
            content_type="artist",
            service=self.service_name,
            data={
                "content_type": "artist",
                "id": artist_id,
                "artist_info": {
                    "id": artist_id,
                    "name": artist.name,
                    "biography": artist.info.biography,
                    "total_albums": 0,  # Will be updated as albums are fetched
                    "total_singles": 0,  # Will be updated as albums are fetched
                    "total_items": len(filtered_album_ids),
                    "remaining_items": len(filtered_album_ids),  # For countdown display
                    "artwork_thumbnail": thumbnail.url if thumbnail else None,
                },
                "items": [],  # Empty initially, albums will be streamed via callback
                "album_ids": filtered_album_ids,
            },
            raw_models={
                "artist": artist,
                "albums": [],
                "singles": [],
            },
        )

        # If callback provided, pre-filter and stream results
        if album_callback:
            # Initialize counter with filtered count if callback provided
            if counter_init_callback:
                counter_init_callback(len(filtered_album_ids), self.service_name)

            # Fetch albums in the same async context to ensure proper cleanup
            await self._fetch_albums_async(filtered_album_ids, album_callback)

        return initial_result

    async def _fetch_albums_async(self, album_ids: list[str], album_callback):
        """Fetch albums asynchronously and call callback for each one."""
        for album_id in album_ids:
            try:
                # Build album metadata; this call will reuse and pop any prefetched
                # album model from the cache inside fetch_album_metadata
                album_metadata = await self.fetch_album_metadata(album_id)
                album_item = album_metadata.data

                # Call the callback with the album data
                if album_callback:
                    album_callback(album_item)

            except Exception:
                logger.exception(
                    "Failed to fetch album metadata for album %s", album_id
                )
                continue

    async def _prefilter_album_ids(self, album_ids: list[str]) -> list[str]:
        """Filter album IDs before streaming based on artist_item_filter.

        Caches lightweight album models to avoid re-fetching later.
        """
        # No filtering required
        if (
            self.artist_item_filter == ArtistItemFilter.BOTH
            or not self.qobuz_downloader
        ):
            return album_ids

        filtered: list[str] = []
        for album_id in album_ids:
            try:
                album = await self.qobuz_downloader.get_album_metadata(album_id)
                # Cache prefetched album model for potential reuse
                self._prefetched_albums[album_id] = album
                total_tracks = album.info.total_tracks or 0
                is_single = total_tracks <= 3
                if (
                    self.artist_item_filter == ArtistItemFilter.ALBUMS_ONLY
                    and not is_single
                ) or (
                    self.artist_item_filter == ArtistItemFilter.SINGLES_ONLY
                    and is_single
                ):
                    filtered.append(album_id)
            except Exception:
                logger.exception("Failed to pre-filter album %s", album_id)
                continue
        return filtered

    async def fetch_album_metadata(self, album_id: str) -> MetadataResult:
        """Fetch album metadata including all tracks."""
        if not self._authenticated or not self.qobuz_downloader:
            msg = "Not authenticated with Qobuz"
            raise RuntimeError(msg)

        # Get album metadata, reusing any cached prefetch from streaming filter
        if album_id in self._prefetched_albums:
            album = self._prefetched_albums.pop(album_id)
        else:
            album = await self.qobuz_downloader.get_album_metadata(album_id)

        # Get all tracks in the album
        tracks = []
        for i, track_id in enumerate(album.track_ids, 1):
            try:
                track = await self.qobuz_downloader.get_track_metadata(track_id)
                track_item = self._create_ui_track_item(track, album)
                track_item["track_number"] = track.info.track_number or i
                tracks.append(track_item)
            except Exception:
                logger.exception("Failed to fetch track %s", track_id)
                continue

        # Get album thumbnail
        thumbnail = album.covers.get_best_image([CoverSize.SMALL, CoverSize.MEDIUM])

        # Note: Important: This instantiation affects the `AlbumArtWidget` in the UI
        return MetadataResult(
            content_type="album",
            service=self.service_name,
            data={
                "content_type": "album",
                "id": album_id,
                "album_info": {
                    "id": album_id,
                    "title": album.title,
                    "artist": album.artist,
                    "year": album.info.release_year or 2024,
                    "total_tracks": album.info.total_tracks or len(tracks),
                    "total_duration": album.duration_formatted,
                    "hires": album.info.hires,
                    "is_explicit": album.info.is_explicit
                    or (
                        any(tracks.get("parental_warning", False) for tracks in tracks)
                    ),
                    "quality": tracks[0]["container"] if tracks else "FLAC",
                    "artwork_thumbnail": thumbnail.url if thumbnail else None,
                    "track_count": album.info.total_tracks or len(tracks),
                },
                "items": tracks,
                "service": self.streaming_source.value,
            },
            raw_models={
                "album": album,
                "tracks": tracks,
            },
        )

    async def fetch_track_metadata(self, track_id: str) -> MetadataResult:
        """Fetch individual track metadata."""
        if not self._authenticated or not self.qobuz_downloader:
            msg = "Not authenticated with Qobuz"
            raise RuntimeError(msg)

        # Get track metadata
        track = await self.qobuz_downloader.get_track_metadata(track_id)

        # Get artwork URL from track covers
        artwork_url = None
        if track.covers and (best_image := track.covers.get_best_image()):
            artwork_url = best_image.url

        track_item = {
            "id": track_id,
            "title": track.title,
            "artist": track.artist,
            "type": "Track",
            "year": 2024,  # Could extract from track if available
            "duration_formatted": track.duration_formatted,
            "track_count": 1,
            "track_number": track.info.track_number or 1,
            "album": track.album_id,
            "quality": str(track.audio.container)
            if track.audio and track.audio.container
            else "FLAC",
            "artwork_url": artwork_url,
        }

        return MetadataResult(
            content_type="track",
            service=self.service_name,
            data={
                "items": [track_item],
            },
            raw_models={
                "track": track,
            },
        )

    async def fetch_playlist_metadata(self, playlist_id: str) -> MetadataResult:
        """Fetch playlist metadata including all tracks."""
        if not self._authenticated or not self.qobuz_downloader:
            msg = "Not authenticated with Qobuz"
            raise RuntimeError(msg)

        # Get playlist metadata
        playlist = await self.qobuz_downloader.get_playlist_metadata(playlist_id)

        playlist_item = {
            "id": playlist_id,
            "title": playlist.name,
            "artist": playlist.info.owner or "Unknown",
            "type": "Playlist",
            "year": 2024,
            "duration_formatted": "0:00",  # Would need to calculate from tracks
            "track_count": playlist.info.total_tracks or 0,
            "quality": "Mixed",
            "artwork_url": None,
        }

        return MetadataResult(
            content_type="playlist",
            service=self.service_name,
            data={
                "items": [playlist_item],
            },
            raw_models={
                "playlist": playlist,
            },
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        if hasattr(self, "session_manager"):
            await self.session_manager.close_all_sessions()
