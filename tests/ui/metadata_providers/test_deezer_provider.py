# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for `DeezerMetadataProvider`.

These tests mock the Deezer client to avoid network usage and focus on
data mapping and control flow. Each test has a single responsibility.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import pytest

from ripstream.models.enums import ArtistItemFilter
from ripstream.ui.metadata_providers.deezer import DeezerMetadataProvider

if TYPE_CHECKING:
    from collections.abc import Callable


@runtime_checkable
class _ClientLike(Protocol):  # pragma: no cover - typing helper
    def get_album(self, album_id: str | int) -> Any: ...
    def get_track(self, track_id: str | int) -> Any: ...
    def get_playlist(self, playlist_id: str | int) -> Any: ...
    def get_artist(self, artist_id: str | int) -> Any: ...


def _make_provider_with_api(
    methods: dict[str, Callable[..., Any]],
) -> DeezerMetadataProvider:
    """Create a provider with a dummy client exposing top-level methods.

    Returns a provider with `_authenticated=True` and `client` set to the dummy.
    """
    client: _ClientLike = SimpleNamespace(**methods)  # type: ignore[assignment]
    provider = DeezerMetadataProvider(credentials={})
    provider.client = client  # type: ignore[assignment]
    provider._authenticated = True
    return provider


@pytest.mark.asyncio
async def test_authenticate_success_with_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticate returns True when deezer.Client can be instantiated."""

    class DummyClient:
        pass

    import ripstream.ui.metadata_providers.deezer as provider_module

    monkeypatch.setattr(provider_module.deezer, "Client", DummyClient)

    provider = DeezerMetadataProvider(credentials={"arl": "token"})
    ok = await provider.authenticate()
    assert ok is True
    assert provider.is_authenticated is True


@pytest.mark.asyncio
async def test_authenticate_failure_when_client_init_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticate returns False when deezer.Client raises at construction."""

    class DummyClient:
        def __init__(self) -> None:
            msg = "boom"
            raise RuntimeError(msg)

    import ripstream.ui.metadata_providers.deezer as provider_module

    monkeypatch.setattr(provider_module.deezer, "Client", DummyClient)

    provider = DeezerMetadataProvider(credentials={"arl": "bad"})
    ok = await provider.authenticate()
    assert ok is False
    assert provider.is_authenticated is False


@pytest.mark.asyncio
async def test_authenticate_without_arl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Authenticate returns True without ARL when `deezer.Client` is available."""

    class DummyClient:
        pass

    import ripstream.ui.metadata_providers.deezer as provider_module

    monkeypatch.setattr(provider_module.deezer, "Client", DummyClient)

    provider = DeezerMetadataProvider(credentials={})
    ok = await provider.authenticate()
    assert ok is True
    assert provider.is_authenticated is True


@pytest.mark.asyncio
async def test_fetch_album_metadata_builds_ui_data() -> None:
    """Album metadata includes album_info and mapped track items."""

    album_resp = {
        "id": 123,
        "title": "Test Album",
        "artist": {"name": "The Artist"},
        "release_date": "2020-05-01",
        "nb_tracks": 2,
        "cover_medium": "http://img/med.jpg",
    }
    tracks_resp = {
        "data": [
            {
                "id": 1,
                "title": "Song A",
                "artist": {"name": "The Artist"},
                "duration": 125,
                "track_position": 1,
            },
            {
                "id": 2,
                "title": "Song B",
                "artist": {"name": "The Artist"},
                "duration": 245,
                "track_position": 2,
            },
        ]
    }

    class DummyTrack:
        def __init__(self, data: dict) -> None:
            self._data = data

        def as_dict(self) -> dict:
            return self._data

    class DummyAlbum:
        def __init__(self, data: dict, tracks: list[dict]) -> None:
            self._data = data
            self._tracks = [DummyTrack(t) for t in tracks]

        def get_tracks(self) -> list[DummyTrack]:
            return self._tracks

        def as_dict(self) -> dict:
            return self._data

    provider = _make_provider_with_api({
        "get_album": lambda _album_id: DummyAlbum(album_resp, tracks_resp["data"]),
    })

    result = await provider.fetch_album_metadata("123")
    assert result.content_type == "album"
    assert result.service == "Deezer"
    data = result.data
    assert data["album_info"]["title"] == "Test Album"
    assert data["album_info"]["artist"] == "The Artist"
    assert data["album_info"]["year"] == 2020
    assert data["album_info"]["track_count"] == 2
    assert data["album_info"]["artwork_thumbnail"] == "http://img/med.jpg"
    assert len(data["items"]) == 2
    assert data["items"][0]["duration_formatted"] == "02:05"


@pytest.mark.asyncio
async def test_fetch_track_metadata_builds_ui_item() -> None:
    """Track metadata maps core fields and artwork from album."""

    track_resp = {
        "id": 42,
        "title": "My Track",
        "artist": {"name": "The Artist"},
        "duration": 61,
        "track_position": 7,
        "album": {"title": "An Album", "cover_medium": "http://img/med.jpg"},
    }

    class DummyTrack:
        def __init__(self, data: dict) -> None:
            self._data = data

        def as_dict(self) -> dict:
            return self._data

    provider = _make_provider_with_api({
        "get_track": lambda _tid: DummyTrack(track_resp)
    })

    result = await provider.fetch_track_metadata("42")
    assert result.content_type == "track"
    item = result.data["items"][0]
    assert item["title"] == "My Track"
    assert item["artist"] == "The Artist"
    assert item["track_number"] == 7
    assert item["album"] == "An Album"
    assert item["artwork_url"] == "http://img/med.jpg"


@pytest.mark.asyncio
async def test_fetch_playlist_metadata_builds_ui_item() -> None:
    """Playlist metadata includes basic info and track count."""

    playlist_resp = {
        "id": 9,
        "title": "Chill Mix",
        "creator": {"name": "DJ"},
        "nb_tracks": 2,
        "picture_medium": "http://img/med.jpg",
    }
    playlist_tracks_resp = {"data": [{"id": 1}, {"id": 2}]}

    class DummyTrack:
        def __init__(self, data: dict) -> None:
            self._data = data

        def as_dict(self) -> dict:
            return self._data

    class DummyPlaylist:
        def __init__(self, data: dict, tracks: list[dict]) -> None:
            self._data = data
            self._tracks = [DummyTrack(t) for t in tracks]

        def get_tracks(self) -> list[DummyTrack]:
            return self._tracks

        def as_dict(self) -> dict:
            return self._data

        @property
        def title(self) -> str:
            return self._data["title"]

    provider = _make_provider_with_api({
        "get_playlist": lambda _pid: DummyPlaylist(
            playlist_resp, playlist_tracks_resp["data"]
        ),
    })

    result = await provider.fetch_playlist_metadata("9")
    assert result.content_type == "playlist"
    item = result.data["items"][0]
    assert item["title"] == "Chill Mix"
    assert item["artist"] == "DJ"
    assert item["track_count"] == 2
    assert item["artwork_url"] == "http://img/med.jpg"


@pytest.mark.asyncio
async def test_fetch_artist_metadata_respects_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artist discography is filtered into albums vs singles based on track count."""

    @dataclass(slots=True)
    class DummyAlbumId:
        id: int

    class DummyArtist:
        def __init__(self, data: dict, album_ids: list[int]) -> None:
            self._data = data
            self._albums = [DummyAlbumId(a) for a in album_ids]

        def get_albums(self) -> list[DummyAlbumId]:
            return self._albums

        def as_dict(self) -> dict:
            return self._data

        @property
        def name(self) -> str:
            return self._data["name"]

    provider = _make_provider_with_api({
        "get_artist": lambda _aid: DummyArtist({"name": "Artist"}, [100, 200]),
    })

    # Patch the per-album fetch to avoid deep mapping and control track counts
    async def fake_fetch_album_metadata(album_id: str) -> Any:
        await asyncio.sleep(0)
        count = 2 if str(album_id) == "100" else 5
        return SimpleNamespace(
            data={
                "album_info": {"total_tracks": count},
            }
        )

    monkeypatch.setattr(provider, "fetch_album_metadata", fake_fetch_album_metadata)

    # Singles only
    provider.artist_item_filter = ArtistItemFilter.SINGLES_ONLY
    singles_only = await provider.fetch_artist_metadata("123")
    assert len(singles_only.data["items"]) == 1

    # Albums only
    provider.artist_item_filter = ArtistItemFilter.ALBUMS_ONLY
    albums_only = await provider.fetch_artist_metadata("123")
    assert len(albums_only.data["items"]) == 1
