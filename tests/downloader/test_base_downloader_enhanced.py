# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enhanced tests for base downloader classes with comprehensive coverage."""

import asyncio
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from ripstream.downloader.base import (
    BaseDownloader,
    DownloadableContent,
    DownloadResult,
)
from ripstream.downloader.config import DownloadBehaviorSettings, DownloaderConfig
from ripstream.downloader.enums import ContentType, RetryStrategy
from ripstream.downloader.exceptions import (
    AuthenticationError,
    DownloadError,
    InsufficientStorageError,
)
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.session import SessionManager


class TestableDownloader(BaseDownloader):
    """Testable implementation of BaseDownloader for testing."""

    # Prevent pytest from collecting this as a test class
    __test__ = False

    def __init__(self, config, session_manager, progress_tracker):
        super().__init__(config, session_manager, progress_tracker)
        self._authenticated = False
        self._should_fail = False
        self._download_delay = 0.0
        self._fail_on_retry = False
        self._checksum_fail = False

    @property
    def source_name(self) -> str:
        return "testable"

    @property
    def supported_content_types(self) -> list[ContentType]:
        return [ContentType.TRACK, ContentType.ALBUM, ContentType.PLAYLIST]

    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        if credentials.get("fail"):
            msg = "Authentication failed"
            raise AuthenticationError(msg)
        self._authenticated = credentials.get("success", True)
        return self._authenticated

    async def get_download_info(self, content_id: str) -> DownloadableContent:
        if not self._authenticated:
            msg = "Not authenticated"
            raise AuthenticationError(msg)

        return DownloadableContent(
            content_id=content_id,
            content_type=ContentType.TRACK,
            source=self.source_name,
            title=f"Test Track {content_id}",
            artist="Test Artist",
            album="Test Album",
            url=f"https://example.com/{content_id}",
            file_name=f"test_track_{content_id}",
            file_extension="mp3",
            expected_size=5 if not self._checksum_fail else 1000,  # "hello" is 5 bytes
            checksum="5d41402abc4b2a76b9719d911017c592"
            if not self._checksum_fail
            else "wrong_checksum",
            checksum_algorithm="md5",
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )

    async def _download_content(
        self,
        content: DownloadableContent,
        file_path: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        self._validate_download_preconditions()

        test_content = self._prepare_test_content(content)

        with open(file_path, "wb") as f:
            if self._should_use_exact_content(content):
                await self._write_exact_content(f, test_content, progress_callback)
            else:
                await self._write_chunked_content(f, test_content, progress_callback)

    def _validate_download_preconditions(self) -> None:
        """Validate that download can proceed."""
        if not self._authenticated:
            msg = "Not authenticated"
            raise AuthenticationError(msg)

        if self._should_fail:
            msg = "Mock download failed"
            raise DownloadError(msg)

    def _prepare_test_content(self, content: DownloadableContent) -> bytes:
        """Prepare test content based on checksum requirements."""
        if content.checksum and not self._checksum_fail:
            # For checksum validation, write exactly "hello" (matches the MD5)
            return b"hello"
        if self._checksum_fail:
            return b"wrong_content"
        # No checksum, write fixed size content for file size validation tests
        return b"x" * 1000

    def _should_use_exact_content(self, content: DownloadableContent) -> bool:
        """Determine if we should write exact content or chunked content."""
        return bool(content.checksum) and not self._checksum_fail

    async def _write_exact_content(
        self,
        file_handle,
        test_content: bytes,
        progress_callback: Callable[[int], None] | None,
    ) -> None:
        """Write exact content for checksum validation."""
        file_handle.write(test_content)
        downloaded = len(test_content)
        if progress_callback:
            progress_callback(downloaded)

    async def _write_chunked_content(
        self,
        file_handle,
        test_content: bytes,
        progress_callback: Callable[[int], None] | None,
    ) -> None:
        """Write content in chunks for size-based tests."""
        actual_size = 1000
        chunk_size = 100
        downloaded = 0

        while downloaded < actual_size:
            chunk_size_actual = min(chunk_size, actual_size - downloaded)
            chunk_data = self._prepare_chunk_data(
                test_content, downloaded, chunk_size_actual
            )

            file_handle.write(chunk_data)
            downloaded += chunk_size_actual

            if progress_callback:
                progress_callback(downloaded)

            if self._download_delay > 0:
                await asyncio.sleep(self._download_delay)

    def _prepare_chunk_data(
        self, test_content: bytes, downloaded: int, chunk_size_actual: int
    ) -> bytes:
        """Prepare chunk data, padding if necessary."""
        chunk_data = test_content[downloaded : downloaded + chunk_size_actual]
        if len(chunk_data) < chunk_size_actual:
            chunk_data += b"x" * (chunk_size_actual - len(chunk_data))
        return chunk_data

    def set_should_fail(self, should_fail: bool) -> None:
        self._should_fail = should_fail

    def set_download_delay(self, delay: float) -> None:
        self._download_delay = delay

    def set_checksum_fail(self, fail: bool) -> None:
        self._checksum_fail = fail

    async def _postprocess_downloaded_file(
        self, content: DownloadableContent, file_path: str
    ) -> None:
        """Mock implementation of post-processing."""
        # Mock implementation does nothing


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def download_config(temp_dir):
    """Create test download configuration."""
    return DownloaderConfig(
        download_directory=Path(temp_dir),
        max_concurrent_downloads=3,
    )


@pytest.fixture
def session_manager(download_config):
    """Create test session manager."""
    return SessionManager(download_config)


@pytest.fixture
def progress_tracker():
    """Create test progress tracker."""
    return ProgressTracker()


@pytest.fixture
def testable_downloader(download_config, session_manager, progress_tracker):
    """Create testable downloader instance."""
    return TestableDownloader(download_config, session_manager, progress_tracker)


@pytest.fixture
def sample_content():
    """Create sample downloadable content."""
    return DownloadableContent(
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
        checksum="5d41402abc4b2a76b9719d911017c592",
        checksum_algorithm="md5",
    )


class TestDownloadableContentEnhanced:
    """Enhanced tests for DownloadableContent class."""

    @pytest.mark.parametrize(
        ("file_name", "file_extension", "expected"),
        [
            ("test_file", "mp3", "test_file.mp3"),
            ("test_file", ".mp3", "test_file.mp3"),
            ("test_file", ".flac", "test_file.flac"),
            ("complex_name", "wav", "complex_name.wav"),
        ],
    )
    def test_full_file_name(self, file_name, file_extension, expected):
        """Test full file name generation with various extensions."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            artist="Test Artist",
            album="Test Album",
            url="https://example.com/test",
            file_name=file_name,
            file_extension=file_extension,
            expected_size=1000,
            checksum=None,
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )
        assert content.full_file_name == expected

    @pytest.mark.parametrize(
        ("artist", "title", "expected"),
        [
            ("Artist", "Title", "Artist - Title"),
            (None, "Title", "Title"),
            ("", "Title", "Title"),
            ("Artist", "", ""),  # Empty title returns empty string
        ],
    )
    def test_display_name(self, artist, title, expected):
        """Test display name generation with various artist/title combinations."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title=title,
            artist=artist,
            album="Test Album",
            url="https://example.com/test",
            file_name="test",
            file_extension="mp3",
            expected_size=1000,
            checksum=None,
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )
        assert content.display_name == expected

    @pytest.mark.parametrize(
        ("file_name", "expected_safe"),
        [
            ("normal_file", "normal_file.mp3"),
            ('file<>:"/\\|?*name', "file_________name.mp3"),
            ("a" * 250, ("a" * 200) + ".mp3"),
            ("file with spaces", "file with spaces.mp3"),
        ],
    )
    def test_get_safe_filename(self, file_name, expected_safe):
        """Test safe filename generation with various problematic characters."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            artist="Test Artist",
            album="Test Album",
            url="https://example.com/test",
            file_name=file_name,
            file_extension="mp3",
            expected_size=1000,
            checksum=None,
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )
        assert content.get_safe_filename() == expected_safe

    def test_validate_checksum_success(self, temp_dir):
        """Test successful checksum validation."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            artist="Test Artist",
            album="Test Album",
            url="https://example.com/test",
            file_name="test",
            file_extension="mp3",
            expected_size=1000,
            checksum="5d41402abc4b2a76b9719d911017c592",  # MD5 of "hello"
            checksum_algorithm="md5",
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )

        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("hello")

        assert content.validate_checksum(str(test_file)) is True

    def test_validate_checksum_failure(self, temp_dir):
        """Test checksum validation failure."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            artist="Test Artist",
            album="Test Album",
            url="https://example.com/test",
            file_name="test",
            file_extension="mp3",
            expected_size=1000,
            checksum="wrong_checksum",
            checksum_algorithm="md5",
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )

        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("hello")

        assert content.validate_checksum(str(test_file)) is False

    def test_validate_checksum_no_checksum(self, temp_dir):
        """Test checksum validation when no checksum is provided."""
        content = DownloadableContent(
            content_id="test",
            content_type=ContentType.TRACK,
            source="test",
            title="Test",
            artist="Test Artist",
            album="Test Album",
            url="https://example.com/test",
            file_name="test",
            file_extension="mp3",
            expected_size=1000,
            checksum=None,
            quality="320kbps",
            format="MP3",
            bitrate=320,
        )

        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("hello")

        assert content.validate_checksum(str(test_file)) is False

    def test_validate_checksum_nonexistent_file(self, sample_content):
        """Test checksum validation with non-existent file."""
        assert sample_content.validate_checksum("/nonexistent/file") is False


class TestDownloadResultEnhanced:
    """Enhanced tests for DownloadResult class."""

    @pytest.mark.parametrize(
        ("speed_bps", "expected_format"),
        [
            (None, "Unknown"),
            (0, "Unknown"),  # Zero speed is treated as unknown
            (500, "500.0 B/s"),
            (1536, "1.5 KB/s"),
            (1048576, "1.0 MB/s"),
            (1073741824, "1.0 GB/s"),
            (2147483648, "2.0 GB/s"),
        ],
    )
    def test_get_formatted_speed(self, speed_bps, expected_format):
        """Test speed formatting with various values."""
        result = DownloadResult(
            download_id=uuid4(),
            success=True,
            file_path=None,
            file_size=None,
            checksum=None,
            duration_seconds=None,
            average_speed_bps=speed_bps,
            error_message=None,
        )
        assert result.get_formatted_speed() == expected_format

    @pytest.mark.parametrize(
        ("file_size", "expected_format"),
        [
            (None, "Unknown"),
            (0, "Unknown"),  # Zero size is treated as unknown
            (500, "500 B"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
            (2147483648, "2.0 GB"),
        ],
    )
    def test_get_formatted_size(self, file_size, expected_format):
        """Test size formatting with various values."""
        result = DownloadResult(
            download_id=uuid4(),
            success=True,
            file_path=None,
            file_size=file_size,
            checksum=None,
            duration_seconds=None,
            average_speed_bps=None,
            error_message=None,
        )
        assert result.get_formatted_size() == expected_format

    def test_has_file_property(self, temp_dir):
        """Test has_file property with existing and non-existing files."""
        # Test with existing file
        test_file = Path(temp_dir) / "test.mp3"
        test_file.write_text("test content")

        result = DownloadResult(
            download_id=uuid4(),
            success=True,
            file_path=str(test_file),
            file_size=None,
            checksum=None,
            duration_seconds=None,
            average_speed_bps=None,
            error_message=None,
        )
        assert result.has_file is True

        # Test with non-existing file
        result_no_file = DownloadResult(
            download_id=uuid4(),
            success=True,
            file_path="/nonexistent/file.mp3",
            file_size=None,
            checksum=None,
            duration_seconds=None,
            average_speed_bps=None,
            error_message=None,
        )
        assert result_no_file.has_file is False

        # Test with None file path
        result_none = DownloadResult(
            download_id=uuid4(),
            success=False,
            file_path=None,
            file_size=None,
            checksum=None,
            duration_seconds=None,
            average_speed_bps=None,
            error_message=None,
        )
        assert result_none.has_file is False


class TestBaseDownloaderEnhanced:
    """Enhanced tests for BaseDownloader class."""

    @pytest.mark.asyncio
    async def test_authentication_success(self, testable_downloader):
        """Test successful authentication."""
        result = await testable_downloader.authenticate({"success": True})
        assert result is True
        assert testable_downloader._authenticated is True

    @pytest.mark.asyncio
    async def test_authentication_failure(self, testable_downloader):
        """Test authentication failure."""
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await testable_downloader.authenticate({"fail": True})

    @pytest.mark.parametrize(
        ("content_type", "expected"),
        [
            (ContentType.TRACK, True),
            (ContentType.ALBUM, True),
            (ContentType.PLAYLIST, True),
            (ContentType.ARTWORK, False),
        ],
    )
    def test_can_download(self, testable_downloader, content_type, expected):
        """Test content type support checking."""
        assert testable_downloader.can_download(content_type) == expected

    @pytest.mark.asyncio
    async def test_download_success(self, testable_downloader, temp_dir):
        """Test successful download."""
        await testable_downloader.authenticate({"success": True})
        content = await testable_downloader.get_download_info("test_123")

        result = await testable_downloader.download(content, temp_dir)

        assert result.success is True
        assert result.file_path is not None
        assert Path(result.file_path).exists()
        assert result.file_size == 5  # "hello" is 5 bytes

    @pytest.mark.asyncio
    async def test_download_with_existing_file_skip(
        self, testable_downloader, temp_dir
    ):
        """Test download skipping when file already exists."""
        await testable_downloader.authenticate({"success": True})
        content = await testable_downloader.get_download_info("test_123")

        # Create existing file with correct content for checksum validation
        file_path = Path(temp_dir) / content.get_safe_filename()
        file_path.write_text("hello")  # Matches expected checksum

        result = await testable_downloader.download(content, temp_dir)

        assert result.success is True
        assert result.metadata.get("skipped") is True
        assert result.metadata.get("reason") == "file_exists"

    @pytest.mark.asyncio
    async def test_download_with_overwrite_setting(self, testable_downloader, temp_dir):
        """Test download with overwrite setting enabled."""
        await testable_downloader.authenticate({"success": True})
        content = await testable_downloader.get_download_info("test_123")

        # Create existing file
        file_path = Path(temp_dir) / content.get_safe_filename()
        file_path.write_text("existing content")

        settings = DownloadBehaviorSettings(overwrite_existing=True)
        result = await testable_downloader.download(content, temp_dir, settings)

        assert result.success is True
        assert result.metadata.get("skipped") is not True

    @pytest.mark.asyncio
    async def test_download_with_retry_success(self, testable_downloader, temp_dir):
        """Test download with retry logic - eventual success."""
        await testable_downloader.authenticate({"success": True})
        content = await testable_downloader.get_download_info("test_123")

        # Mock to fail first attempt, succeed on second
        call_count = 0
        original_download = testable_downloader._download_content

        async def mock_download_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "First attempt fails"
                raise DownloadError(msg)
            return await original_download(*args, **kwargs)

        testable_downloader._download_content = mock_download_with_retry

        settings = DownloadBehaviorSettings(max_retries=2, retry_delay=0.01)
        result = await testable_downloader.download(content, temp_dir, settings)

        assert result.success is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_download_retry_exhausted(self, testable_downloader, temp_dir):
        """Test download when all retries are exhausted."""
        await testable_downloader.authenticate({"success": True})
        testable_downloader.set_should_fail(True)
        content = await testable_downloader.get_download_info("test_123")

        settings = DownloadBehaviorSettings(max_retries=2, retry_delay=0.01)
        result = await testable_downloader.download(content, temp_dir, settings)

        assert result.success is False
        assert "Download failed after 2 retries" in result.error_message

    @pytest.mark.parametrize(
        ("retry_strategy", "attempt", "expected_delay"),
        [
            (RetryStrategy.FIXED_DELAY, 0, 1.0),
            (RetryStrategy.FIXED_DELAY, 2, 1.0),
            (RetryStrategy.LINEAR, 0, 1.0),
            (RetryStrategy.LINEAR, 2, 3.0),
            (RetryStrategy.EXPONENTIAL, 0, 1.0),
            (RetryStrategy.EXPONENTIAL, 2, 4.0),
            (RetryStrategy.NONE, 0, 0.0),
        ],
    )
    def test_calculate_retry_delay(
        self, testable_downloader, retry_strategy, attempt, expected_delay
    ):
        """Test retry delay calculation with different strategies."""
        settings = DownloadBehaviorSettings(
            retry_strategy=retry_strategy,
            retry_delay=1.0,
            retry_backoff_factor=2.0,
        )

        delay = testable_downloader._calculate_retry_delay(attempt, settings)
        assert delay == expected_delay

    @pytest.mark.asyncio
    async def test_download_multiple_success(self, testable_downloader, temp_dir):
        """Test downloading multiple contents successfully."""
        await testable_downloader.authenticate({"success": True})

        contents = []
        for i in range(3):
            content = await testable_downloader.get_download_info(f"test_{i}")
            contents.append(content)

        results = await testable_downloader.download_multiple(
            contents, temp_dir, max_concurrent=2
        )

        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert Path(result.file_path).exists()

    @pytest.mark.asyncio
    async def test_download_multiple_with_failures(self, testable_downloader, temp_dir):
        """Test downloading multiple contents with some failures."""
        await testable_downloader.authenticate({"success": True})

        contents = []
        for i in range(3):
            content = await testable_downloader.get_download_info(f"test_{i}")
            contents.append(content)

        # Make downloader fail
        testable_downloader.set_should_fail(True)

        settings = DownloadBehaviorSettings(max_retries=1, retry_delay=0.01)
        results = await testable_downloader.download_multiple(
            contents, temp_dir, settings, max_concurrent=2
        )

        assert len(results) == 3
        for result in results:
            assert result.success is False

    @pytest.mark.asyncio
    async def test_insufficient_storage_error(self, testable_downloader, temp_dir):
        """Test insufficient storage error handling."""
        await testable_downloader.authenticate({"success": True})
        content = await testable_downloader.get_download_info("test_123")

        # Mock disk usage to simulate insufficient space
        with (
            patch("shutil.disk_usage", return_value=(1000, 500, 100)),
            patch.object(testable_downloader.config, "min_free_space_mb", 1),
        ):
            with pytest.raises(InsufficientStorageError) as exc_info:
                await testable_downloader.download(content, temp_dir)

            assert "Insufficient storage space" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_checksum_validation_failure(self, testable_downloader, temp_dir):
        """Test download failure due to checksum validation."""
        await testable_downloader.authenticate({"success": True})
        testable_downloader.set_checksum_fail(True)  # This will create wrong content
        content = await testable_downloader.get_download_info("test_123")

        settings = DownloadBehaviorSettings(verify_checksums=True)
        result = await testable_downloader.download(content, temp_dir, settings)

        assert result.success is False
        assert "Checksum validation failed" in result.error_message

    @pytest.mark.asyncio
    async def test_file_size_validation_failure(self, testable_downloader, temp_dir):
        """Test download failure due to file size validation."""
        await testable_downloader.authenticate({"success": True})
        content = await testable_downloader.get_download_info("test_123")
        content.expected_size = 5000  # Different from actual size (1000)
        content.checksum = None  # Remove checksum to test only file size validation

        settings = DownloadBehaviorSettings(
            verify_file_size=True, verify_checksums=False
        )
        result = await testable_downloader.download(content, temp_dir, settings)

        assert result.success is False
        assert "File size mismatch" in result.error_message

    @pytest.mark.asyncio
    async def test_calculate_checksum(self, testable_downloader, temp_dir):
        """Test checksum calculation."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("hello")

        checksum = await testable_downloader._calculate_checksum(str(test_file), "md5")
        expected_checksum = "5d41402abc4b2a76b9719d911017c592"  # MD5 of "hello"

        assert checksum == expected_checksum

    @pytest.mark.asyncio
    async def test_calculate_checksum_nonexistent_file(self, testable_downloader):
        """Test checksum calculation with non-existent file."""
        checksum = await testable_downloader._calculate_checksum("/nonexistent/file")
        assert checksum == ""

    @pytest.mark.asyncio
    async def test_active_downloads_tracking(self, testable_downloader):
        """Test active downloads tracking."""
        # Initially no active downloads
        active = await testable_downloader.get_active_downloads()
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_cancel_download(self, testable_downloader):
        """Test download cancellation."""
        # Test cancelling non-existent download
        result = await testable_downloader.cancel_download(uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup(self, testable_downloader):
        """Test cleanup method."""
        await testable_downloader.cleanup()
        assert len(testable_downloader._active_downloads) == 0

    @pytest.mark.asyncio
    async def test_progress_tracking_during_download(
        self, testable_downloader, temp_dir
    ):
        """Test that progress is tracked during download."""
        await testable_downloader.authenticate({"success": True})
        content = await testable_downloader.get_download_info("test_123")

        # Mock progress tracker to verify calls
        with (
            patch.object(
                testable_downloader.progress_tracker, "start_tracking"
            ) as mock_start,
            patch.object(
                testable_downloader.progress_tracker, "update_progress"
            ) as mock_update,
            patch.object(
                testable_downloader.progress_tracker, "mark_completed"
            ) as mock_complete,
        ):
            result = await testable_downloader.download(content, temp_dir)

            assert result.success is True
            mock_start.assert_called_once()
            assert (
                mock_update.call_count > 0
            )  # Should be called multiple times during download
            mock_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_cleanup_removes_partial_file(
        self, testable_downloader, temp_dir
    ):
        """Test that partial files are cleaned up on error."""
        await testable_downloader.authenticate({"success": True})
        testable_downloader.set_should_fail(True)
        content = await testable_downloader.get_download_info("test_123")

        settings = DownloadBehaviorSettings(max_retries=1, retry_delay=0.01)
        result = await testable_downloader.download(content, temp_dir, settings)

        assert result.success is False
        # File should not exist after cleanup
        expected_path = Path(temp_dir) / content.get_safe_filename()
        assert not expected_path.exists()
