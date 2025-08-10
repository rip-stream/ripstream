# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Deezer metadata provider implementation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import deezer

from ripstream.models.enums import ArtistItemFilter, StreamingSource
from ripstream.ui.metadata_providers.base import BaseMetadataProvider, MetadataResult

logger = logging.getLogger(__name__)


class DeezerMetadataProvider(BaseMetadataProvider):
    """Deezer-specific metadata provider backed by deezer-python API."""

    def __init__(self, credentials: dict[str, Any] | None = None):
        super().__init__(credentials)
        self.client: Any | None = None
        self._arl: str = (credentials or {}).get("arl", "")

    @property
    def service_name(self) -> str:
        """Get the name of the streaming service."""
        return "Deezer"

    @property
    def streaming_source(self) -> StreamingSource:
        """Get the StreamingSource enum value."""
        return StreamingSource.DEEZER

    async def authenticate(self) -> bool:
        """Authenticate with Deezer using deezer.Client and optional ARL cookie.

        If `credentials` contains an `arl`, set it on the client's cookie jar to
        enable account-scoped endpoints where applicable.
        """
        try:
            if self.client is None:
                self.client = deezer.Client()
            # Apply ARL cookie if provided
            arl = (self.credentials or {}).get("arl")
            if isinstance(arl, str) and arl:
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

    async def fetch_artist_metadata(self, artist_id: str) -> MetadataResult:
        """Fetch artist metadata including albums, playlists, and tracks."""
        self._ensure_ready()

        # Fetch artist and album listing using resources
        artist_res = await asyncio.to_thread(self.client.get_artist, artist_id)
        albums_page = await asyncio.to_thread(artist_res.get_albums)
        album_items = list(albums_page)

        albums: list[dict] = []
        singles: list[dict] = []
        for item in album_items:
            try:
                album_id = str(item.id)
                album_metadata = await self.fetch_album_metadata(album_id)
                ui_album = album_metadata.data

                track_count = (
                    ui_album.get("album_info", {}).get("total_tracks", 0)  # type: ignore[assignment]
                )
                if int(track_count or 0) <= 3:
                    singles.append(ui_album)
                else:
                    albums.append(ui_album)
            except Exception:
                logger.exception(
                    "Failed to fetch album %s for artist %s", item, artist_id
                )
                continue

        # Apply filtering
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

        thumbnail = _get_artist_picture_url(artist_res.as_dict())

        return MetadataResult(
            content_type="artist",
            service=self.service_name,
            data={
                "content_type": "artist",
                "id": str(artist_id),
                "artist_info": {
                    "id": str(artist_id),
                    "name": getattr(artist_res, "name", None)
                    or artist_res.as_dict().get("name"),
                    "biography": None,
                    "total_albums": total_albums,
                    "total_singles": total_singles,
                    "total_items": len(items),
                    "artwork_thumbnail": thumbnail,
                },
                "items": items,
                "album_ids": [
                    str(a.id)
                    for a in album_items
                    if hasattr(a, "id") and a.id is not None
                ],
            },
            raw_models={
                "artist": artist_res,
                "albums": albums,
                "singles": singles,
            },
        )

    async def fetch_album_metadata(self, album_id: str) -> MetadataResult:
        """Fetch album metadata including all tracks."""
        self._ensure_ready()

        album_res = await asyncio.to_thread(self.client.get_album, album_id)
        tracks_page = await asyncio.to_thread(album_res.get_tracks)
        track_resources = list(tracks_page)
        tracks_raw: list[dict] = [t.as_dict() for t in track_resources]
        total_duration_seconds = sum(int(t.get("duration", 0) or 0) for t in tracks_raw)
        duration_formatted = _format_duration(total_duration_seconds)

        # Build UI track items
        tracks: list[dict[str, Any]] = []
        for i, t in enumerate(tracks_raw, 1):
            tracks.append(
                _build_ui_track_from_deezer_track(
                    t,
                    album_res.as_dict(),
                    fallback_track_number=i,
                )
            )

        # Album thumbnail
        thumbnail = _get_album_cover_url(album_res.as_dict())

        year = None
        try:
            album_dict = album_res.as_dict()
            date_str = album_dict.get("release_date")
            if isinstance(date_str, str) and len(date_str) >= 4:
                year = int(date_str[:4])
        except Exception:  # noqa: BLE001
            year = None

        album_dict = album_res.as_dict()
        track_total = int(album_dict.get("nb_tracks", 0) or len(tracks))

        album_info = {
            "id": str(album_id),
            "title": album_dict.get("title") or "Unknown Album",
            "artist": _get_album_artist(album_dict) or "Unknown Artist",
            "year": year,
            "total_tracks": track_total,
            "total_duration": duration_formatted,
            "hires": False,
            "is_explicit": bool(
                album_dict.get("parental_warning") or album_dict.get("explicit_lyrics")
            ),
            "quality": "Mixed",
            "artwork_thumbnail": thumbnail,
            "track_count": track_total,
        }

        return MetadataResult(
            content_type="album",
            service=self.service_name,
            data={
                "content_type": "album",
                "id": str(album_id),
                "album_info": album_info,
                "items": tracks,
                "service": self.streaming_source.value,
            },
            raw_models={
                "album": album_res,
                "tracks": track_resources,
            },
        )

    async def fetch_track_metadata(self, track_id: str) -> MetadataResult:
        """Fetch individual track metadata."""
        self._ensure_ready()

        track_res = await asyncio.to_thread(self.client.get_track, track_id)
        track_dict = track_res.as_dict()
        item = _build_ui_track_from_deezer_track(
            track_dict, track_dict.get("album", {}) or {}, fallback_track_number=1
        )

        return MetadataResult(
            content_type="track",
            service=self.service_name,
            data={
                "items": [item],
            },
            raw_models={
                "track": track_res,
            },
        )

    async def fetch_playlist_metadata(self, playlist_id: str) -> MetadataResult:
        """Fetch playlist metadata including all tracks."""
        self._ensure_ready()

        playlist_res = await asyncio.to_thread(self.client.get_playlist, playlist_id)
        tracks_page = await asyncio.to_thread(playlist_res.get_tracks)
        track_resources = list(tracks_page)
        track_data = [t.as_dict() for t in track_resources]

        playlist_item = {
            "id": str(playlist_id),
            "title": getattr(playlist_res, "title", None)
            or playlist_res.as_dict().get("title"),
            "artist": (playlist_res.as_dict().get("creator") or {}).get("name")
            or "Unknown",
            "type": "Playlist",
            "year": None,
            "duration_formatted": None,
            "track_count": int(
                playlist_res.as_dict().get("nb_tracks", 0) or len(track_data)
            ),
            "quality": "Mixed",
            "artwork_url": playlist_res.as_dict().get("picture_medium")
            or playlist_res.as_dict().get("picture_big")
            or None,
        }

        return MetadataResult(
            content_type="playlist",
            service=self.service_name,
            data={
                "items": [playlist_item],
            },
            raw_models={
                "playlist": playlist_res,
                "tracks": track_resources,
            },
        )

    async def cleanup(self) -> None:
        """Clean up resources."""
        # No network sessions to close; `deezer.Client` uses requests internally
        return

    # --------------------
    # Internal helpers
    # --------------------
    def _ensure_ready(self) -> None:
        if not self._authenticated or self.client is None:
            msg = "Not authenticated with Deezer or client not initialized"
            raise RuntimeError(msg)


def _format_duration(total_seconds: float | None) -> str | None:
    if total_seconds is None:
        return None
    # Clamp negative durations and coerce to int seconds
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _get_album_cover_url(album_resp: dict) -> str | None:
    return (
        album_resp.get("cover_medium")
        or album_resp.get("cover_big")
        or album_resp.get("cover_xl")
        or album_resp.get("cover_small")
        or None
    )


def _get_artist_picture_url(artist_resp: dict) -> str | None:
    return (
        artist_resp.get("picture_medium")
        or artist_resp.get("picture_big")
        or artist_resp.get("picture_xl")
        or artist_resp.get("picture_small")
        or None
    )


def _get_album_artist(album_resp: dict) -> str | None:
    artist = album_resp.get("artist")
    if isinstance(artist, dict):
        return artist.get("name")
    return None


def _build_ui_track_from_deezer_track(
    track_resp: dict,
    album_resp: dict | None,
    *,
    fallback_track_number: int,
) -> dict[str, Any]:
    album_cover = _get_album_cover_url(album_resp or {})
    duration_seconds = int(track_resp.get("duration", 0) or 0)

    title = track_resp.get("title") or "Unknown Track"
    artist_name = None
    if isinstance(track_resp.get("artist"), dict):
        artist_name = track_resp["artist"].get("name")

    return {
        "id": str(track_resp.get("id")),
        "title": title,
        "artist": artist_name or "Unknown Artist",
        "type": "Track",
        "year": None,
        "duration_formatted": _format_duration(duration_seconds),
        "track_count": 1,
        "track_number": int(track_resp.get("track_position") or fallback_track_number),
        "album": (album_resp or {}).get("title") or None,
        "quality": "FLAC",  # UI hint only; actual download quality resolved elsewhere
        "container": "FLAC",
        "artwork_url": album_cover,
    }
