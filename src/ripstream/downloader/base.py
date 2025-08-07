# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Base classes for the downloader module."""

import asyncio
import contextlib
import hashlib
import logging
import shutil
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import aiofiles
from pydantic import Field

from ripstream.downloader.config import DownloadBehaviorSettings, DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.exceptions import (
    DownloadError,
    InsufficientStorageError,
    InvalidContentError,
    RetryExhaustedError,
)
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.session import SessionManager
from ripstream.models.base import RipStreamBaseModel

logger = logging.getLogger(__name__)


class DownloadResult(RipStreamBaseModel):
    """Result of a download operation."""

    download_id: UUID = Field(..., description="Download identifier")
    success: bool = Field(..., description="Whether download was successful")
    file_path: str | None = Field(None, description="Path to downloaded file")
    file_size: int | None = Field(None, description="Size of downloaded file")
    checksum: str | None = Field(None, description="File checksum")
    duration_seconds: float | None = Field(None, description="Download duration")
    average_speed_bps: float | None = Field(None, description="Average download speed")
    error_message: str | None = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional result metadata"
    )

    @property
    def is_success(self) -> bool:
        """Check if download was successful."""
        return self.success

    @property
    def has_file(self) -> bool:
        """Check if result has a valid file path."""
        return self.file_path is not None and Path(self.file_path).exists()

    def get_formatted_speed(self) -> str:
        """Get formatted download speed."""
        if not self.average_speed_bps:
            return "Unknown"

        speed = self.average_speed_bps
        if speed < 1024:
            return f"{speed:.1f} B/s"
        if speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        if speed < 1024 * 1024 * 1024:
            return f"{speed / (1024 * 1024):.1f} MB/s"
        return f"{speed / (1024 * 1024 * 1024):.1f} GB/s"

    def get_formatted_size(self) -> str:
        """Get formatted file size."""
        if not self.file_size:
            return "Unknown"

        size = self.file_size
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


class DownloadableContent(RipStreamBaseModel):
    """Represents content that can be downloaded."""

    content_id: str = Field(..., description="Unique content identifier")
    content_type: ContentType = Field(..., description="Type of content")
    source: str = Field(..., description="Source service")

    # Content metadata
    title: str = Field(..., description="Content title")
    artist: str | None = Field(None, description="Artist name")
    album: str | None = Field(None, description="Album name")

    # Download information
    url: str = Field(..., description="Download URL")
    file_name: str = Field(..., description="Target file name")
    file_extension: str = Field(..., description="File extension")
    expected_size: int | None = Field(None, description="Expected file size")
    checksum: str | None = Field(None, description="Expected checksum")
    checksum_algorithm: str = Field(default="md5", description="Checksum algorithm")

    # Quality and format
    quality: str | None = Field(None, description="Audio quality")
    format: str | None = Field(None, description="Audio format")
    bitrate: int | None = Field(None, description="Audio bitrate")

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional content metadata"
    )

    @property
    def display_name(self) -> str:
        """Get display name for the content."""
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title

    @property
    def full_file_name(self) -> str:
        """Get full file name with extension."""
        if self.file_extension.startswith("."):
            return f"{self.file_name}{self.file_extension}"
        return f"{self.file_name}.{self.file_extension}"

    def get_safe_filename(self) -> str:
        """Get filesystem-safe filename."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        safe_name = self.file_name
        for char in invalid_chars:
            safe_name = safe_name.replace(char, "_")

        # Limit length
        if len(safe_name) > 200:
            safe_name = safe_name[:200]

        return f"{safe_name}.{self.file_extension.lstrip('.')}"

    def validate_checksum(self, file_path: str) -> bool:
        """Validate file checksum."""
        if not self.checksum or not Path(file_path).exists():
            return False

        algorithm = self.checksum_algorithm.lower()
        if algorithm not in hashlib.algorithms_available:
            return False

        hasher = hashlib.new(algorithm)
        with Path(file_path).open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        return hasher.hexdigest().lower() == self.checksum.lower()


class BaseDownloader(ABC):
    """Abstract base class for all downloaders."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
    ) -> None:
        self.config = config
        self.session_manager = session_manager
        self.progress_tracker = progress_tracker
        self._active_downloads: dict[UUID, asyncio.Task[DownloadResult]] = {}

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Get the name of the download source."""
        ...

    @property
    @abstractmethod
    def supported_content_types(self) -> list[ContentType]:
        """Get list of supported content types."""
        ...

    @abstractmethod
    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        """Authenticate with the download source."""
        ...

    @abstractmethod
    async def get_download_info(self, content_id: str) -> DownloadableContent:
        """Get download information for content."""
        ...

    @abstractmethod
    async def _download_content(
        self,
        content: DownloadableContent,
        file_path: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Download content to file. Must be implemented by subclasses."""
        ...

    async def download(
        self,
        content: DownloadableContent,
        download_directory: str | None = None,
        settings: DownloadBehaviorSettings | None = None,
    ) -> DownloadResult:
        """Download content and return result."""
        download_id = uuid4()
        start_time = datetime.now(UTC)

        # Setup download parameters
        settings = settings or self.config.get_behavior_for_source(self.source_name)
        download_directory = download_directory or str(self.config.download_directory)

        # Prepare download environment
        Path(download_directory).mkdir(parents=True, exist_ok=True)
        await self._check_available_space(download_directory, content.expected_size)

        file_path = str(Path(download_directory) / content.get_safe_filename())

        # Check if file already exists and is valid
        if self._should_skip_download(file_path, content, settings):
            return self._create_skip_result(download_id, file_path)

        # Perform the download
        self.progress_tracker.start_tracking(download_id, content.expected_size)

        try:
            return await self._execute_download(
                content, file_path, settings, download_id, start_time
            )
        except (
            DownloadError,
            RetryExhaustedError,
            InvalidContentError,
            InsufficientStorageError,
            OSError,
        ) as e:
            return await self._handle_download_error(
                e, download_id, file_path, start_time
            )

    def _should_skip_download(
        self,
        file_path: str,
        content: DownloadableContent,
        settings: DownloadBehaviorSettings,
    ) -> bool:
        """Check if download should be skipped because file already exists."""
        if not Path(file_path).exists():
            return False

        if settings.overwrite_existing:
            return False

        # Skip if no checksum required or checksum is valid
        return not content.checksum or content.validate_checksum(file_path)

    def _create_skip_result(self, download_id: UUID, file_path: str) -> DownloadResult:
        """Create result for skipped download."""
        return DownloadResult(
            download_id=download_id,
            success=True,
            file_path=file_path,
            file_size=Path(file_path).stat().st_size,
            duration_seconds=0.0,
            checksum=None,
            average_speed_bps=None,
            error_message=None,
            retry_count=0,
            metadata={"skipped": True, "reason": "file_exists"},
        )

    async def _execute_download(
        self,
        content: DownloadableContent,
        file_path: str,
        settings: DownloadBehaviorSettings,
        download_id: UUID,
        start_time: datetime,
    ) -> DownloadResult:
        """Execute the actual download process."""
        await self._download_with_retry(content, file_path, settings, download_id)
        await self._validate_downloaded_file(content, file_path, settings)

        # Post-process the downloaded file (metadata and artwork embedding)
        await self._postprocess_downloaded_file(content, file_path)

        self.progress_tracker.mark_completed(download_id)

        return await self._create_success_result(
            download_id, file_path, start_time, content
        )

    async def _create_success_result(
        self,
        download_id: UUID,
        file_path: str,
        start_time: datetime,
        content: DownloadableContent,
    ) -> DownloadResult:
        """Create result for successful download."""
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()
        file_size = Path(file_path).stat().st_size
        average_speed = file_size / duration if duration > 0 else 0

        return DownloadResult(
            download_id=download_id,
            success=True,
            file_path=file_path,
            file_size=file_size,
            duration_seconds=duration,
            average_speed_bps=average_speed,
            checksum=await self._calculate_checksum(
                file_path, content.checksum_algorithm
            ),
            error_message=None,
            retry_count=0,
            metadata={},
        )

    async def _handle_download_error(
        self, error: Exception, download_id: UUID, file_path: str, start_time: datetime
    ) -> DownloadResult:
        """Handle download errors and cleanup."""
        error_message = str(error)
        self.progress_tracker.mark_error(download_id, error_message)

        # Clean up partial file
        if Path(file_path).exists():
            with contextlib.suppress(OSError):
                Path(file_path).unlink()

        return DownloadResult(
            download_id=download_id,
            success=False,
            file_path=None,
            file_size=None,
            checksum=None,
            duration_seconds=(datetime.now(UTC) - start_time).total_seconds(),
            average_speed_bps=None,
            error_message=error_message,
            retry_count=0,
            metadata={},
        )

    async def download_multiple(
        self,
        contents: list[DownloadableContent],
        download_directory: str | None = None,
        settings: DownloadBehaviorSettings | None = None,
        max_concurrent: int | None = None,
    ) -> list[DownloadResult]:
        """Download multiple contents concurrently."""
        if max_concurrent is None:
            max_concurrent = self.config.max_concurrent_downloads

        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_with_semaphore(
            content: DownloadableContent,
        ) -> DownloadResult:
            async with semaphore:
                return await self.download(content, download_directory, settings)

        tasks = [download_with_semaphore(content) for content in contents]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _download_with_retry(
        self,
        content: DownloadableContent,
        file_path: str,
        settings: DownloadBehaviorSettings,
        download_id: UUID,
    ) -> None:
        """Download with retry logic."""
        last_error = None

        for attempt in range(settings.max_retries + 1):
            try:
                # Create progress callback
                def progress_callback(bytes_downloaded: int) -> None:
                    self.progress_tracker.update_progress(download_id, bytes_downloaded)

                # Attempt download
                await self._download_content(content, file_path, progress_callback)
            except (TimeoutError, DownloadError, OSError, ConnectionError) as e:
                last_error = e

                if attempt < settings.max_retries:
                    # Calculate retry delay
                    delay = self._calculate_retry_delay(attempt, settings)
                    await asyncio.sleep(delay)

                    # Clean up partial file
                    if Path(file_path).exists():
                        with contextlib.suppress(OSError):
                            Path(file_path).unlink()
            else:
                return  # Success

        # All retries exhausted
        msg = f"Download failed after {settings.max_retries} retries"
        raise RetryExhaustedError(
            msg,
            retry_count=settings.max_retries,
            last_error=last_error,
        )

    def _calculate_retry_delay(
        self, attempt: int, settings: DownloadBehaviorSettings
    ) -> float:
        """Calculate delay before retry."""
        from ripstream.downloader.enums import RetryStrategy

        if settings.retry_strategy == RetryStrategy.NONE:
            return 0.0
        if settings.retry_strategy == RetryStrategy.LINEAR:
            return settings.retry_delay * (attempt + 1)
        if settings.retry_strategy == RetryStrategy.EXPONENTIAL:
            return settings.retry_delay * (settings.retry_backoff_factor**attempt)
        if settings.retry_strategy == RetryStrategy.FIXED_DELAY:
            return settings.retry_delay
        return settings.retry_delay

    async def _check_available_space(
        self, directory: str, required_bytes: int | None
    ) -> None:
        """Check if there's enough space for download."""
        if required_bytes is None:
            return

        try:
            # Use shutil.disk_usage() for cross-platform compatibility
            _, _, available_bytes = shutil.disk_usage(directory)

            # Add buffer for minimum free space
            min_free_bytes = self.config.min_free_space_mb * 1024 * 1024

            if available_bytes < (required_bytes + min_free_bytes):
                msg = f"Insufficient storage space. Required: {required_bytes}, Available: {available_bytes}"
                raise InsufficientStorageError(
                    msg,
                    required_bytes=required_bytes,
                    available_bytes=available_bytes,
                )
        except (OSError, AttributeError):
            # Handle cases where disk_usage might fail (permissions, invalid path, etc.)
            # Log the warning but don't fail the download - let it proceed and fail naturally if needed
            logger.warning("Could not check disk space for '%s'", directory)

    async def _validate_downloaded_file(
        self,
        content: DownloadableContent,
        file_path: str,
        settings: DownloadBehaviorSettings,
    ) -> None:
        """Validate downloaded file."""
        if not Path(file_path).exists():
            msg = "Downloaded file does not exist"
            raise InvalidContentError(msg)

        file_size = Path(file_path).stat().st_size

        # Validate file size
        if (
            settings.verify_file_size
            and content.expected_size
            and file_size != content.expected_size
        ):
            msg = f"File size mismatch. Expected: {content.expected_size}, Got: {file_size}"
            raise InvalidContentError(msg)

        # Validate checksum
        if (
            settings.verify_checksums
            and content.checksum
            and not content.validate_checksum(file_path)
        ):
            msg = "Checksum validation failed"
            raise InvalidContentError(msg)

    @abstractmethod
    async def _postprocess_downloaded_file(
        self, content: DownloadableContent, file_path: str
    ) -> None:
        """Post-process downloaded file with metadata and artwork embedding.

        This method should be overridden by subclasses to implement
        source-specific metadata and artwork embedding.
        """
        # Base implementation does nothing - subclasses should override

    async def _calculate_checksum(self, file_path: str, algorithm: str = "md5") -> str:
        """Calculate file checksum."""
        if not Path(file_path).exists():
            return ""

        hasher = hashlib.new(algorithm.lower())

        async with aiofiles.open(file_path, "rb") as f:
            while True:
                chunk = await f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)

        return hasher.hexdigest()

    def can_download(self, content_type: ContentType) -> bool:
        """Check if this downloader can handle the content type."""
        return content_type in self.supported_content_types

    async def get_active_downloads(self) -> dict[UUID, DownloadResult]:
        """Get information about active downloads."""
        results = {}
        for download_id, task in self._active_downloads.items():
            if not task.done():
                progress = self.progress_tracker.get_progress(download_id)
                if progress:
                    results[download_id] = DownloadResult(
                        download_id=download_id,
                        success=False,  # Still in progress
                        file_path=None,
                        file_size=None,
                        checksum=None,
                        duration_seconds=None,
                        average_speed_bps=None,
                        error_message=None,
                        retry_count=0,
                        metadata={"progress": progress.model_dump()},
                    )
        return results

    async def cancel_download(self, download_id: UUID) -> bool:
        """Cancel an active download."""
        if download_id in self._active_downloads:
            task = self._active_downloads[download_id]
            if not task.done():
                task.cancel()
                return True
        return False

    async def cleanup(self) -> None:
        """Cleanup resources."""
        # Cancel all active downloads
        for task in self._active_downloads.values():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._active_downloads:
            await asyncio.gather(
                *self._active_downloads.values(),
                return_exceptions=True,
            )

        self._active_downloads.clear()
