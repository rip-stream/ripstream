# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enums for music streaming sources, quality levels, and other constants."""

from enum import IntEnum, StrEnum


class StreamingSource(StrEnum):
    """Supported streaming sources."""

    QOBUZ = "qobuz"
    TIDAL = "tidal"
    DEEZER = "deezer"
    SOUNDCLOUD = "soundcloud"
    SPOTIFY = "spotify"
    YOUTUBE_MUSIC = "youtube_music"
    YOUTUBE = "youtube"
    APPLE_MUSIC = "apple_music"
    UNKNOWN = "unknown"


class AudioQuality(IntEnum):
    """Audio quality levels in ascending order."""

    LOW = 0  # ~128 kbps
    HIGH = 1  # ~320 kbps
    LOSSLESS = 2  # CD quality (16-bit/44.1kHz)
    HI_RES = 3  # High resolution (24-bit/96kHz+)


class MediaType(StrEnum):
    """Types of media that can be downloaded."""

    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"


class AlbumType(StrEnum):
    """Album types."""

    ALBUM = "album"
    SINGLE = "single"
    EP = "ep"
    COMPILATION = "compilation"
    LIVE = "live"
    REMIX = "remix"
    SOUNDTRACK = "soundtrack"


class DownloadStatus(StrEnum):
    """Download status for media items."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class CoverSize(StrEnum):
    """Cover art sizes."""

    THUMBNAIL = "thumbnail"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ORIGINAL = "original"


class ArtistItemFilter(StrEnum):
    """Filter for artist discography items shown in the UI/fetcher."""

    ALBUMS_ONLY = "albums_only"
    SINGLES_ONLY = "singles_only"
    BOTH = "both"
