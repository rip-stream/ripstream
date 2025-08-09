# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for lightweight-first album streaming behavior in Qobuz provider."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ripstream.models.enums import ArtistItemFilter
from ripstream.ui.metadata_providers.base import MetadataResult
from ripstream.ui.metadata_providers.qobuz import QobuzMetadataProvider


def _make_mock_artist(album_ids: list[str], raw_items: list[dict]) -> Mock:
    """Create a minimal mock artist model with required attributes."""
    artist = Mock()
    artist.album_ids = album_ids
    artist.name = "Test Artist"
    artist.info.biography = "Bio"

    # Covers
    covers = Mock()
    thumbnail = Mock()
    thumbnail.url = "https://example.com/thumb.jpg"
    covers.get_best_image.return_value = thumbnail
    artist.covers = covers

    # Stats raw metadata with albums_items
    stats = Mock()
    stats.get_metadata.return_value = {"albums_items": raw_items}
    artist.stats = stats
    return artist


def _metadata_result_for_album(album_id: str, num_tracks: int) -> MetadataResult:
    """Build a full album MetadataResult with the given number of tracks."""
    tracks = [
        {
            "id": f"{album_id}_track_{i + 1}",
            "title": f"Track {i + 1}",
            "artist": "Test Artist",
            "type": "Track",
            "year": 2024,
            "duration_formatted": "3:30",
            "track_count": 1,
            "track_number": i + 1,
            "album": album_id,
            "quality": "FLAC",
            "artwork_url": None,
        }
        for i in range(num_tracks)
    ]

    return MetadataResult(
        content_type="album",
        service="Qobuz",
        data={
            "content_type": "album",
            "id": album_id,
            "album_info": {
                "id": album_id,
                "title": f"Album {album_id}",
                "artist": "Test Artist",
                "year": 2024,
                "total_tracks": num_tracks,
                "total_duration": "10:00",
                "hires": False,
                "is_explicit": False,
                "quality": "FLAC",
                "artwork_thumbnail": None,
                "track_count": num_tracks,
            },
            "items": tracks,
            "service": "qobuz",
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filter_mode", "expected_ids"),
    [
        (ArtistItemFilter.BOTH, ["a1", "a2"]),
        (ArtistItemFilter.ALBUMS_ONLY, ["a2"]),  # a2 has tracks_count 5 (>3)
        (ArtistItemFilter.SINGLES_ONLY, ["a1"]),  # a1 has tracks_count 2 (<=3)
    ],
)
async def test_lightweight_then_full_emission(
    filter_mode: ArtistItemFilter, expected_ids: list[str]
):
    """Provider should emit lightweight album first, then full album with tracks."""
    provider = QobuzMetadataProvider(credentials=None)
    provider._authenticated = True

    # Mock downloader and artist
    provider.qobuz_downloader = Mock()
    raw_items = [
        {
            "id": "a1",
            "title": "A1",
            "artist": {"name": "Test Artist"},
            "tracks_count": 2,
            "duration": 200,
            "image": {},
        },
        {
            "id": "a2",
            "title": "A2",
            "artist": {"name": "Test Artist"},
            "tracks_count": 5,
            "duration": 500,
            "image": {},
        },
    ]
    artist = _make_mock_artist(["a1", "a2"], raw_items)
    provider.qobuz_downloader.get_artist_metadata = AsyncMock(return_value=artist)

    # Mock full album fetches
    async def _fetch_album(album_id: str) -> MetadataResult:  # type: ignore[override]
        # Yield control to satisfy async usage requirement
        await asyncio.sleep(0)
        return _metadata_result_for_album(album_id, 3)

    with patch.object(provider, "fetch_album_metadata", side_effect=_fetch_album):
        provider.artist_item_filter = filter_mode

        emitted: list[dict] = []

        def _album_cb(data: dict) -> None:
            emitted.append(data)

        # Run streaming
        await provider.fetch_artist_metadata_streaming(
            "artist_123", album_callback=_album_cb, counter_init_callback=None
        )

        # We expect for each expected id: two emissions: lightweight then full
        # Keep order assertions by grouping below
        # Group by id
        from collections import defaultdict

        grouped: dict[str, list[dict]] = defaultdict(list)
        for d in emitted:
            album_id_key = d.get("album_info", {}).get("id") or d.get("id")
            grouped[str(album_id_key)].append(d)

        assert set(grouped.keys()) == set(expected_ids)
        for pair in grouped.values():
            # First should be lightweight (no tracks), second full (with tracks)
            assert pair[0].get("items") == []
            assert len(pair[1].get("items", [])) > 0
