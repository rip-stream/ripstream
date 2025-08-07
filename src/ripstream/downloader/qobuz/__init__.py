# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Qobuz downloader module."""

from ripstream.downloader.qobuz.client import QobuzClient
from ripstream.downloader.qobuz.downloader import QobuzDownloader
from ripstream.downloader.qobuz.models import (
    QobuzAlbumResponse,
    QobuzCredentials,
    QobuzDownloadInfo,
    QobuzPlaylistResponse,
    QobuzSearchResult,
    QobuzTrackResponse,
)

__all__ = [
    "QobuzAlbumResponse",
    "QobuzClient",
    "QobuzCredentials",
    "QobuzDownloadInfo",
    "QobuzDownloader",
    "QobuzPlaylistResponse",
    "QobuzSearchResult",
    "QobuzTrackResponse",
]
