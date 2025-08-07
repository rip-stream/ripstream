# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Ripstream downloader package with generic base classes for music downloading."""

# Core downloader classes
from ripstream.downloader.base import (
    BaseDownloader,
    DownloadableContent,
    DownloadResult,
)
from ripstream.downloader.config import DownloadBehaviorSettings, DownloaderConfig
from ripstream.downloader.enums import (
    CompressionType,
    ContentType,
    DownloadPriority,
    DownloadState,
    NetworkProtocol,
    RetryStrategy,
)
from ripstream.downloader.exceptions import (
    DownloadError,
    DownloadTimeoutError,
    InvalidContentError,
    NetworkError,
    RetryExhaustedError,
)
from ripstream.downloader.progress import (
    DownloadProgress,
    ProgressCallback,
    ProgressTracker,
)
from ripstream.downloader.queue import DownloadQueue, DownloadTask
from ripstream.downloader.session import DownloadSession, SessionManager

__all__ = [
    # Core classes
    "BaseDownloader",
    # Enums
    "CompressionType",
    "ContentType",
    "DownloadBehaviorSettings",
    # Exceptions
    "DownloadError",
    "DownloadPriority",
    # Progress tracking
    "DownloadProgress",
    # Queue management
    "DownloadQueue",
    "DownloadResult",
    # Session management
    "DownloadSession",
    "DownloadState",
    "DownloadTask",
    "DownloadTimeoutError",
    "DownloadableContent",
    # Configuration
    "DownloaderConfig",
    "InvalidContentError",
    "NetworkError",
    "NetworkProtocol",
    "ProgressCallback",
    "ProgressTracker",
    "RetryExhaustedError",
    "RetryStrategy",
    "SessionManager",
]
