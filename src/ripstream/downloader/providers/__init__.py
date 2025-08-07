# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Download providers module for ripstream."""

from ripstream.downloader.providers.base import (
    BaseDownloadProvider,
    DownloadProviderResult,
)
from ripstream.downloader.providers.factory import DownloadProviderFactory
from ripstream.downloader.providers.qobuz import QobuzDownloadProvider
from ripstream.downloader.providers.service import DownloadService

__all__ = [
    "BaseDownloadProvider",
    "DownloadProviderFactory",
    "DownloadProviderResult",
    "DownloadService",
    "QobuzDownloadProvider",
]
