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
        # Map of album_id -> raw album item for lightweight streaming
        self._raw_album_items_map: dict[str, dict] = {}

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

        # Pre-filter album IDs using album list returned with artist response to avoid network calls
        filtered_album_ids = artist.album_ids
        if album_callback and hasattr(artist, "stats"):
            try:
                raw = artist.stats.get_metadata("source_data", {})
                raw_albums: list[dict] = (
                    raw.get("albums_items", []) if isinstance(raw, dict) else []
                )
                if raw_albums:
                    id_to_tracks = {
                        str(item.get("id")): int(item.get("tracks_count", 0) or 0)
                        for item in raw_albums
                        if item.get("id") is not None
                    }
                    if self.artist_item_filter != ArtistItemFilter.BOTH:
                        only_singles = (
                            self.artist_item_filter == ArtistItemFilter.SINGLES_ONLY
                        )
                        filtered_album_ids = [
                            aid
                            for aid in artist.album_ids
                            if (
                                (id_to_tracks.get(aid, 0) <= 3)
                                if only_singles
                                else (id_to_tracks.get(aid, 0) > 3)
                            )
                        ]
            except (AttributeError, KeyError, TypeError):
                # If structure unexpected, fall back to original list
                filtered_album_ids = artist.album_ids

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

            # Build map of album_id -> raw album item for lightweight streaming
            id_to_raw: dict[str, dict] = {}
            try:
                raw = artist.stats.get_metadata("source_data", {})
                raw_albums: list[dict] = (
                    raw.get("albums_items", []) if isinstance(raw, dict) else []
                )
                id_to_raw = {
                    str(item.get("id")): item
                    for item in raw_albums
                    if item.get("id") is not None
                }
            except (AttributeError, KeyError, TypeError):
                id_to_raw = {}
            # Store map on instance so async fetch can use it without changing signature
            self._raw_album_items_map = id_to_raw

            # Fetch albums in the same async context; if raw is available, stream without per-album fetches
            await self._fetch_albums_async(filtered_album_ids, album_callback)

            # Clear map after use
            self._raw_album_items_map = {}

        return initial_result

    async def _fetch_albums_async(self, album_ids: list[str], album_callback):
        """Fetch albums asynchronously and call callback for each one.

        Uses any raw album map set on the instance to avoid refetching.
        """
        for album_id in album_ids:
            try:
                raw_map = getattr(self, "_raw_album_items_map", {}) or {}
                if album_id in raw_map:
                    # Emit lightweight album for immediate grid rendering
                    album_item = self._build_lightweight_album_data(raw_map[album_id])
                    if album_callback:
                        album_callback(album_item)

                    # Immediately fetch full album details (tracks) to populate list view
                    full_album = await self.fetch_album_metadata(album_id)
                    if album_callback:
                        album_callback(full_album.data)
                    # Continue to next album
                    continue
                # Build album metadata; this call will fetch full details
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

    def _build_lightweight_album_data(self, raw: dict) -> dict:
        """Construct minimal album data dict from raw artist albums item."""
        album_id = str(raw.get("id", ""))
        title = raw.get("title") or "Unknown Album"
        artist_name = None
        artist_info = raw.get("artist")
        if isinstance(artist_info, dict):
            artist_name = artist_info.get("name")
        year = None
        try:
            date_str = raw.get("release_date_original")
            if date_str and isinstance(date_str, str):
                year = int(date_str.split("-")[0])
        except (ValueError, AttributeError, TypeError):
            year = None
        tracks_count = int(raw.get("tracks_count", 0) or 0)
        duration_seconds = int(raw.get("duration", 0) or 0)
        image = raw.get("image") or {}
        artwork_url = None
        if isinstance(image, dict):
            artwork_url = (
                image.get("small") or image.get("thumbnail") or image.get("large")
            )

        album_info = {
            "id": album_id,
            "title": title,
            "artist": artist_name or "Unknown Artist",
            "year": year,
            "total_tracks": tracks_count,
            "total_duration": duration_seconds,
            "hires": bool(raw.get("hires")),
            "is_explicit": bool(raw.get("parental_warning")),
            "quality": "Mixed",
            "artwork_thumbnail": artwork_url,
            "track_count": tracks_count,
        }

        return {
            "content_type": "album",
            "service": self.streaming_source.value,
            "id": album_id,
            "album_info": album_info,
            "items": [],
        }

    # Prefiltering now uses artist response's albums list; network-based prefetch removed

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
            "audio_info": {
                "quality": int(track.audio.quality)
                if getattr(track.audio, "quality", None) is not None
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

    async def fetch_playlist_metadata_streaming(
        self,
        playlist_id: str,
        album_callback=None,
        counter_init_callback=None,
    ) -> MetadataResult:
        """Fetch playlist as a collection of albums and stream albums progressively.

        Flow:
        - Resolve playlist metadata once
        - Extract album IDs from the playlist's tracks and deduplicate
        - Immediately emit an initial metadata result for the playlist context
        - Stream albums for the distinct album IDs via album_callback, reusing
          the existing album fetching pipeline
        """
        if not self._authenticated or not self.qobuz_downloader:
            msg = "Not authenticated with Qobuz"
            raise RuntimeError(msg)

        # 1) Resolve playlist
        playlist = await self.qobuz_downloader.get_playlist_metadata(playlist_id)

        # 2) Compute distinct album IDs from playlist track references.
        album_ids = self._extract_album_ids_from_playlist(playlist)

        # Fallback: if we couldn't derive album IDs from source_data, we will
        # stream tracks' albums by fetching albums in the loop and dedup there.

        # 3) Emit initial playlist metadata for UI setup
        initial_result = MetadataResult(
            content_type="playlist",
            service=self.service_name,
            data={
                "content_type": "playlist",
                "id": playlist_id,
                "playlist_info": {
                    "id": playlist_id,
                    "name": playlist.name,
                    "owner": playlist.info.owner,
                    "total_items": len(album_ids)
                    if album_ids
                    else playlist.info.total_tracks,
                    "remaining_items": len(album_ids)
                    if album_ids
                    else playlist.info.total_tracks,
                    "artwork_thumbnail": None,
                },
                "items": [],
                "album_ids": album_ids,
            },
            raw_models={
                "playlist": playlist,
            },
        )

        # 4) Stream albums if a callback is provided
        if album_callback:
            ids_to_fetch = album_ids
            if not ids_to_fetch:
                # No precomputed album ids; derive by resolving track -> album
                # Resolve sequentially but skip duplicates
                id_seen: set[str] = set()
                ids_to_fetch = []
                for pt in playlist.tracks:
                    try:
                        track = await self.qobuz_downloader.get_track_metadata(
                            pt.track_id
                        )
                        if track.album_id and track.album_id not in id_seen:
                            id_seen.add(track.album_id)
                            ids_to_fetch.append(track.album_id)
                    except Exception:
                        logger.exception(
                            "Failed to resolve track %s for album id", pt.track_id
                        )
                        continue

            # Initialize counter if provided
            if counter_init_callback:
                counter_init_callback(len(ids_to_fetch), self.service_name)

            # Reuse album fetcher to stream albums progressively
            await self._fetch_albums_async(ids_to_fetch, album_callback)

        return initial_result

    def _extract_album_ids_from_playlist(self, playlist) -> list[str]:
        """Extract distinct album IDs from a playlist's tracks.

        Tries multiple strategies to remain resilient if upstream structures change:
        - Prefer attribute `album_id` on `PlaylistTrack` (when downloader injected it)
        - Fall back to inspecting any raw metadata present
        Returns a list preserving order, without duplicates.
        """
        seen: set[str] = set()
        album_ids: list[str] = []
        for track in playlist.tracks:
            album_id = getattr(track, "album_id", None)
            if not album_id and hasattr(track, "raw_metadata"):
                raw = track.raw_metadata or {}
                if isinstance(raw, dict):
                    candidate = raw.get("album_id")
                    album_id = str(candidate) if candidate is not None else None
            if album_id and album_id not in seen:
                seen.add(album_id)
                album_ids.append(album_id)
        return album_ids

    async def cleanup(self) -> None:
        """Clean up resources."""
        if hasattr(self, "session_manager"):
            await self.session_manager.close_all_sessions()
