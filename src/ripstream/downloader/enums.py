# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enums for the downloader module."""

from enum import Enum, StrEnum


class DownloadState(StrEnum):
    """Download state enumeration."""

    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class DownloadPriority(int, Enum):
    """Download priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class RetryStrategy(StrEnum):
    """Retry strategy for failed downloads."""

    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIXED_DELAY = "fixed_delay"


class ContentType(StrEnum):
    """Type of downloadable content."""

    TRACK = "track"
    ALBUM = "album"
    PLAYLIST = "playlist"
    ARTWORK = "artwork"
    METADATA = "metadata"
    ARTIST = "artist"
    UNKNOWN = "unknown"


class CompressionType(StrEnum):
    """Audio compression types."""

    LOSSLESS = "lossless"
    LOSSY = "lossy"
    HYBRID = "hybrid"


class NetworkProtocol(StrEnum):
    """Network protocols for downloading."""

    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"
    SFTP = "sftp"
