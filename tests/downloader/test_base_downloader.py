# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for base downloader classes."""

import asyncio
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from ripstream.downloader.base import (
    BaseDownloader,
    DownloadableContent,
    DownloadResult,
)
from ripstream.downloader.config import DownloadBehaviorSettings, DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.exceptions import AuthenticationError, DownloadError
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.session import SessionManager


class MockDownloader(BaseDownloader):
    """Mock downloader for testing."""

    def __init__(self, config, session_manager, progress_tracker):
        super().__init__(config, session_manager, progress_tracker)
        self._authenticated = False
        self._should_fail = False
        self._download_delay = 0.0

    @property
    def source_name(self) -> str:
        return "mock"

    @property
    def supported_content_types(self) -> list[ContentType]:
        return [ContentType.TRACK, ContentType.ALBUM]

    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        if credentials.get("fail"):
            msg = "Mock authentication failed"
            raise AuthenticationError(msg)
        self._authenticated = True
        return True

    async def get_download_info(self, content_id: str) -> DownloadableContent:
        if not self._authenticated:
            msg = "Not authenticated"
            raise AuthenticationError(msg)

        return DownloadableContent(
            content_id=content_id,
            content_type=ContentType.TRACK,
            source=self.source_name,
            title="Test Track",
            artist="Test Artist",
            url=f"https://example.com/{content_id}",
            file_name="test_track",
            file_extension="mp3",
            expected_size=1000,
        )

    async def _download_content(
        self,
        content: DownloadableContent,
        file_path: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        if not self._authenticated:
            msg = "Not authenticated"
            raise AuthenticationError(msg)

        if self._should_fail:
            msg = "Mock download failed"
            raise DownloadError(msg)

        # Simulate download
        total_size = content.expected_size or 1000
        chunk_size = 100
        downloaded = 0

        with open(file_path, "wb") as f:
            while downloaded < total_size:
                chunk_size_actual = min(chunk_size, total_size - downloaded)
                f.write(b"x" * chunk_size_actual)
                downloaded += chunk_size_actual

                if progress_callback:
                    progress_callback(downloaded)

                if self._download_delay > 0:
                    await asyncio.sleep(self._download_delay)

    async def _postprocess_downloaded_file(
        self, content: DownloadableContent, file_path: str
    ) -> None:
        """Mock implementation of post-processing."""
        # Mock implementation does nothing

    def set_should_fail(self, should_fail: bool) -> None:
        """Set whether downloads should fail."""
        self._should_fail = should_fail

    def set_download_delay(self, delay: float) -> None:
        """Set download delay for testing."""
        self._download_delay = delay


class TestDownloadableContent:
    """Test DownloadableContent class."""

    def test_create_downloadable_content(self):
        """Test creating downloadable content."""
        content = DownloadableContent(
            content_id="test_123",
            content_type=ContentType.TRACK,
            source="test_source",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            url="https://example.com/test_123",
            file_name="test_song",
            file_extension="mp3",
            expected_size=5000000,
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )

        assert content.content_id == "test_123"
        assert content.content_type == ContentType.TRACK
        assert content.source == "test_source"
        assert content.title == "Test Song"
        assert content.artist == "Test Artist"
        assert content.album == "Test Album"
        assert content.display_name == "Test Artist - Test Song"
        assert content.full_file_name == "test_song.mp3"

    def test_safe_filename(self):
        """Test safe filename generation."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            url="https://example.com/test",
            file_name='test<>:"/\\|?*file',
            file_extension="mp3",
        )

        safe_name = content.get_safe_filename()
        assert "<" not in safe_name
        assert ">" not in safe_name
        assert ":" not in safe_name
        assert '"' not in safe_name
        assert "/" not in safe_name
        assert "\\" not in safe_name
        assert "|" not in safe_name
        assert "?" not in safe_name
        assert "*" not in safe_name

    def test_validate_checksum(self):
        """Test checksum validation."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            url="https://example.com/test",
            file_name="test",
            file_extension="mp3",
            checksum="5d41402abc4b2a76b9719d911017c592",  # MD5 of "hello"
            checksum_algorithm="md5",
        )

        # Create a test file with known content
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("hello")
            temp_path = f.name

        try:
            assert content.validate_checksum(temp_path) is True

            # Test with wrong checksum
            content.checksum = "wrong_checksum"
            assert content.validate_checksum(temp_path) is False

            # Test with non-existent file
            assert content.validate_checksum("/non/existent/file") is False
        finally:
            os.unlink(temp_path)


class TestDownloadResult:
    """Test DownloadResult class."""

    def test_create_download_result(self):
        """Test creating download result."""
        download_id = uuid4()
        result = DownloadResult(
            download_id=download_id,
            success=True,
            file_path="/path/to/file.mp3",
            file_size=5000000,
            duration_seconds=30.5,
            average_speed_bps=163934.4,
        )

        assert result.download_id == download_id
        assert result.is_success is True
        assert result.file_path == "/path/to/file.mp3"
        assert result.file_size == 5000000
        assert "160.1 KB/s" in result.get_formatted_speed()
        assert "4.8 MB" in result.get_formatted_size()

    def test_failed_result(self):
        """Test failed download result."""
        result = DownloadResult(
            download_id=uuid4(),
            success=False,
            error_message="Download failed",
            retry_count=3,
        )

        assert result.is_success is False
        assert result.error_message == "Download failed"
        assert result.retry_count == 3
        assert result.has_file is False


@pytest.mark.asyncio
class TestBaseDownloader:
    """Test BaseDownloader class."""

    async def test_authentication(self):
        """Test downloader authentication."""
        config = DownloaderConfig()
        session_manager = SessionManager(config)
        progress_tracker = ProgressTracker()

        downloader = MockDownloader(config, session_manager, progress_tracker)

        # Test successful authentication
        result = await downloader.authenticate({"api_key": "test"})
        assert result is True

        # Test failed authentication
        with pytest.raises(AuthenticationError):
            await downloader.authenticate({"fail": True})

        await session_manager.close_all_sessions()

    async def test_get_download_info(self):
        """Test getting download info."""
        config = DownloaderConfig()
        session_manager = SessionManager(config)
        progress_tracker = ProgressTracker()

        downloader = MockDownloader(config, session_manager, progress_tracker)
        await downloader.authenticate({"api_key": "test"})

        content = await downloader.get_download_info("test_123")
        assert content.content_id == "test_123"
        assert content.title == "Test Track"
        assert content.artist == "Test Artist"

        await session_manager.close_all_sessions()

    async def test_successful_download(self):
        """Test successful download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DownloaderConfig(download_directory=Path(temp_dir))
            session_manager = SessionManager(config)
            progress_tracker = ProgressTracker()

            downloader = MockDownloader(config, session_manager, progress_tracker)
            await downloader.authenticate({"api_key": "test"})

            content = await downloader.get_download_info("test_123")
            result = await downloader.download(content)

            assert result.is_success is True
            assert result.file_path is not None
            assert os.path.exists(result.file_path)
            assert result.file_size == 1000

            await session_manager.close_all_sessions()

    async def test_failed_download(self):
        """Test failed download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DownloaderConfig(download_directory=Path(temp_dir))
            session_manager = SessionManager(config)
            progress_tracker = ProgressTracker()

            downloader = MockDownloader(config, session_manager, progress_tracker)
            await downloader.authenticate({"api_key": "test"})
            downloader.set_should_fail(True)

            # Use settings with minimal retry delay for faster test execution
            settings = DownloadBehaviorSettings(
                max_retries=2,
                retry_delay=0.01,  # Very short delay
                retry_backoff_factor=1.0,  # No exponential backoff
            )

            content = await downloader.get_download_info("test_123")
            result = await downloader.download(content, settings=settings)

            assert result.is_success is False
            assert result.error_message is not None
            assert "Download failed after" in result.error_message

            await session_manager.close_all_sessions()

    async def test_download_with_existing_file(self):
        """Test download when file already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DownloaderConfig(download_directory=Path(temp_dir))
            session_manager = SessionManager(config)
            progress_tracker = ProgressTracker()

            downloader = MockDownloader(config, session_manager, progress_tracker)
            await downloader.authenticate({"api_key": "test"})

            # Create content without checksum to avoid validation issues
            content = DownloadableContent(
                content_id="test_123",
                content_type=ContentType.TRACK,
                source=downloader.source_name,
                title="Test Track",
                artist="Test Artist",
                url="https://example.com/test_123",
                file_name="test_track",
                file_extension="mp3",
                expected_size=1000,
            )

            # Create existing file
            file_path = os.path.join(temp_dir, content.get_safe_filename())
            with open(file_path, "wb") as f:
                f.write(b"x" * 1000)  # Same size as expected

            # Download should skip existing file
            result = await downloader.download(content)

            assert result.is_success is True
            assert result.metadata.get("skipped") is True
            assert result.metadata.get("reason") == "file_exists"

            await session_manager.close_all_sessions()

    async def test_download_multiple(self):
        """Test downloading multiple contents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = DownloaderConfig(download_directory=Path(temp_dir))
            session_manager = SessionManager(config)
            progress_tracker = ProgressTracker()

            downloader = MockDownloader(config, session_manager, progress_tracker)
            await downloader.authenticate({"api_key": "test"})

            contents = []
            for i in range(3):
                content = await downloader.get_download_info(f"test_{i}")
                contents.append(content)

            results = await downloader.download_multiple(contents, max_concurrent=2)

            assert len(results) == 3
            for result in results:
                assert result.is_success is True
                assert os.path.exists(result.file_path)

            await session_manager.close_all_sessions()

    async def test_content_type_support(self):
        """Test content type support checking."""
        config = DownloaderConfig()
        session_manager = SessionManager(config)
        progress_tracker = ProgressTracker()

        downloader = MockDownloader(config, session_manager, progress_tracker)

        assert downloader.can_download(ContentType.TRACK) is True
        assert downloader.can_download(ContentType.ALBUM) is True
        assert downloader.can_download(ContentType.ARTWORK) is False

        await session_manager.close_all_sessions()
