# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Ripstream models package with music entities and utilities."""

# Core models
from ripstream.models.album import Album, AlbumCredits, AlbumInfo, AlbumStats
from ripstream.models.artist import Artist, ArtistInfo, ArtistStats
from ripstream.models.artwork import CoverImage, Covers
from ripstream.models.audio import AudioInfo, DownloadableAudio
from ripstream.models.base import (
    DownloadableMedia,
    MediaInfo,
    MetadataContainer,
    RipStreamBaseModel,
    SearchableMedia,
)

# Database models
from ripstream.models.database import (
    DownloadHistory,
    DownloadRecord,
    DownloadSession,
)
from ripstream.models.db_manager import (
    DatabaseManager,
    close_databases,
    get_downloads_db,
    initialize_databases,
)
from ripstream.models.download_integration import (
    DownloadIntegration,
    get_download_integration,
)
from ripstream.models.download_service import (
    DownloadService,
    FailedDownloadsRepository,
    get_download_service,
)
from ripstream.models.enums import (
    AlbumType,
    AudioQuality,
    CoverSize,
    DownloadStatus,
    MediaType,
    StreamingSource,
)

# Factories and utilities
from ripstream.models.factories import (
    DeezerModelFactory,
    ModelFactory,
    QobuzModelFactory,
    SoundCloudModelFactory,
    TidalModelFactory,
    get_factory_for_source,
)
from ripstream.models.playlist import (
    Playlist,
    PlaylistInfo,
    PlaylistStats,
    PlaylistTrack,
)
from ripstream.models.track import Track, TrackCredits, TrackInfo
from ripstream.models.utils import (
    calculate_album_stats,
    calculate_playlist_stats,
    create_download_path,
    extract_year_from_date,
    format_duration,
    format_file_size,
    get_quality_description,
    group_albums_by_artist,
    group_tracks_by_album,
    merge_artist_names,
    normalize_genre,
    parse_duration,
    sanitize_filename,
    search_models,
    validate_model_relationships,
)

__all__ = [
    "Album",
    "AlbumCredits",
    "AlbumInfo",
    "AlbumStats",
    "AlbumType",
    "Artist",
    "ArtistInfo",
    "ArtistStats",
    "AudioInfo",
    "AudioQuality",
    "CoverImage",
    "CoverSize",
    "Covers",
    "DatabaseManager",
    "DeezerModelFactory",
    "DownloadHistory",
    "DownloadIntegration",
    "DownloadRecord",
    "DownloadService",
    "DownloadSession",
    "DownloadStatus",
    "DownloadableAudio",
    "DownloadableMedia",
    "FailedDownloadsRepository",
    "MediaInfo",
    "MediaType",
    "MetadataContainer",
    "ModelFactory",
    "Playlist",
    "PlaylistInfo",
    "PlaylistStats",
    "PlaylistTrack",
    "QobuzModelFactory",
    "RipStreamBaseModel",
    "SearchableMedia",
    "SoundCloudModelFactory",
    "StreamingSource",
    "TidalModelFactory",
    "Track",
    "TrackCredits",
    "TrackInfo",
    "calculate_album_stats",
    "calculate_playlist_stats",
    "close_databases",
    "create_download_path",
    "extract_year_from_date",
    "format_duration",
    "format_file_size",
    "get_download_integration",
    "get_download_service",
    "get_downloads_db",
    "get_factory_for_source",
    "get_quality_description",
    "group_albums_by_artist",
    "group_tracks_by_album",
    "initialize_databases",
    "merge_artist_names",
    "normalize_genre",
    "parse_duration",
    "sanitize_filename",
    "search_models",
    "validate_model_relationships",
]


def create_artist_from_source(
    source: StreamingSource, artist_id: str, data: dict, **kwargs: object
) -> Artist:
    """Create an Artist from source data."""
    factory_class = get_factory_for_source(source)
    if hasattr(factory_class, "create_artist"):
        return factory_class.create_artist(artist_id, data, **kwargs)
    return ModelFactory.create_artist(source, artist_id, data, **kwargs)


def create_album_from_source(
    source: StreamingSource, album_id: str, data: dict, **kwargs: object
) -> Album:
    """Create an Album from source data."""
    factory_class = get_factory_for_source(source)
    if hasattr(factory_class, "create_album"):
        return factory_class.create_album(album_id, data, **kwargs)
    return ModelFactory.create_album(source, album_id, data, **kwargs)


def create_track_from_source(
    source: StreamingSource,
    track_id: str,
    data: dict,
    album_data: dict | None = None,
    **kwargs: object,
) -> Track:
    """Create a Track from source data."""
    factory_class = get_factory_for_source(source)
    if hasattr(factory_class, "create_track"):
        return factory_class.create_track(track_id, data, album_data, **kwargs)
    return ModelFactory.create_track(source, track_id, data, album_data, **kwargs)


def create_playlist_from_source(
    source: StreamingSource, playlist_id: str, data: dict, **kwargs: object
) -> Playlist:
    """Create a Playlist from source data."""
    factory_class = get_factory_for_source(source)
    if hasattr(factory_class, "create_playlist"):
        return factory_class.create_playlist(playlist_id, data, **kwargs)
    return ModelFactory.create_playlist(source, playlist_id, data, **kwargs)


# Add convenience functions to __all__
__all__ += [
    "create_album_from_source",
    "create_artist_from_source",
    "create_playlist_from_source",
    "create_track_from_source",
]
