# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Convenience constructors that pick the right factory for a streaming source."""

from typing import Any, cast

from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.enums import StreamingSource
from ripstream.models.factories import ModelFactory, get_factory_for_source
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track

_SOURCE_SPECIFIC = {
    StreamingSource.QOBUZ,
    StreamingSource.TIDAL,
    StreamingSource.DEEZER,
    StreamingSource.SOUNDCLOUD,
}


def create_artist_from_source(
    source: StreamingSource, artist_id: str, data: dict[str, Any], **kwargs: Any
) -> Artist:
    """Create an Artist from source data."""
    if source not in _SOURCE_SPECIFIC:
        return ModelFactory.create_artist(source, artist_id, data, **kwargs)
    factory_class = cast("Any", get_factory_for_source(source))
    return cast("Artist", factory_class.create_artist(artist_id, data, **kwargs))


def create_album_from_source(
    source: StreamingSource, album_id: str, data: dict[str, Any], **kwargs: Any
) -> Album:
    """Create an Album from source data."""
    if source not in _SOURCE_SPECIFIC:
        return ModelFactory.create_album(source, album_id, data, **kwargs)
    factory_class = cast("Any", get_factory_for_source(source))
    return cast("Album", factory_class.create_album(album_id, data, **kwargs))


def create_track_from_source(
    source: StreamingSource,
    track_id: str,
    data: dict[str, Any],
    album_data: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Track:
    """Create a Track from source data."""
    if source not in _SOURCE_SPECIFIC:
        return ModelFactory.create_track(source, track_id, data, album_data, **kwargs)
    factory_class = cast("Any", get_factory_for_source(source))
    return cast(
        "Track", factory_class.create_track(track_id, data, album_data, **kwargs)
    )


def create_playlist_from_source(
    source: StreamingSource, playlist_id: str, data: dict[str, Any], **kwargs: Any
) -> Playlist:
    """Create a Playlist from source data."""
    if source not in _SOURCE_SPECIFIC:
        return ModelFactory.create_playlist(source, playlist_id, data, **kwargs)
    factory_class = cast("Any", get_factory_for_source(source))
    return cast(
        "Playlist", factory_class.create_playlist(playlist_id, data, **kwargs)
    )
