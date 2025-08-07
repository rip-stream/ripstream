# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Enhanced tests for progress tracking module."""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from ripstream.downloader.enums import DownloadState
from ripstream.downloader.progress import (
    DownloadProgress,
    ProgressCallback,
    ProgressTracker,
)


class TestDownloadProgress:
    """Test the DownloadProgress class."""

    @pytest.fixture
    def progress(self):
        """Create a basic download progress instance."""
        return DownloadProgress(
            download_id=uuid4(),
            state=DownloadState.DOWNLOADING,
            total_bytes=1024,
            eta_seconds=None,
            last_error=None,
        )

    def test_download_progress_creation(self, progress):
        """Test creating a DownloadProgress instance."""
        assert progress.downloaded_bytes == 0
        assert progress.total_bytes == 1024
        assert progress.state == DownloadState.DOWNLOADING
        assert isinstance(progress.start_time, datetime)
        assert isinstance(progress.last_update_time, datetime)
        assert progress.bytes_per_second == 0.0
        assert progress.average_speed == 0.0
        assert progress.percentage == 0.0
        assert progress.eta_seconds is None
        assert progress.error_count == 0
        assert progress.last_error is None

    def test_download_progress_properties(self, progress):
        """Test DownloadProgress properties."""
        assert progress.is_complete is False
        assert progress.is_active is True

        progress.state = DownloadState.COMPLETED
        assert progress.is_complete is True
        assert progress.is_active is False

    def test_download_progress_elapsed_seconds(self, progress):
        """Test elapsed time calculation."""
        # Wait a moment to ensure time difference
        import time

        time.sleep(0.001)

        elapsed = progress.elapsed_seconds
        assert elapsed > 0
        assert isinstance(elapsed, float)

    def test_update_progress_increasing_bytes(self, progress):
        """Test updating progress with increasing byte count."""
        import time

        time.sleep(0.001)  # Small delay to ensure time difference
        progress.update_progress(512)

        assert progress.downloaded_bytes == 512
        assert progress.percentage == 50.0
        assert progress.bytes_per_second > 0
        assert progress.average_speed > 0

    def test_update_progress_decreasing_bytes(self, progress):
        """Test updating progress with decreasing byte count (restart scenario)."""
        progress.update_progress(512)
        progress.update_progress(256)  # Simulate restart

        assert progress.downloaded_bytes == 256
        assert progress.percentage == 25.0

    def test_update_progress_zero_time_diff(self, progress):
        """Test updating progress with zero time difference."""
        # Mock the current time to be the same as last_update_time
        with patch("ripstream.downloader.progress.datetime") as mock_datetime:
            mock_datetime.now.return_value = progress.last_update_time
            progress.update_progress(512)

            assert progress.downloaded_bytes == 512
            assert progress.bytes_per_second == 0.0

    def test_set_total_size(self, progress):
        """Test setting total size."""
        progress.downloaded_bytes = 512
        progress.set_total_size(2048)

        assert progress.total_bytes == 2048
        assert progress.percentage == 25.0

    def test_set_total_size_with_existing_progress(self, progress):
        """Test setting total size when download already has progress."""
        progress.downloaded_bytes = 512
        progress.total_bytes = 1024
        progress.set_total_size(2048)

        assert progress.percentage == 25.0

    def test_mark_error(self, progress):
        """Test marking an error."""
        error_message = "Network timeout"
        progress.mark_error(error_message)

        assert progress.error_count == 1
        assert progress.last_error == error_message
        assert progress.state == DownloadState.FAILED

    def test_mark_completed(self, progress):
        """Test marking as completed."""
        progress.mark_completed()

        assert progress.state == DownloadState.COMPLETED
        assert progress.percentage == 100.0
        assert progress.downloaded_bytes == progress.total_bytes

    def test_mark_completed_no_total_size(self, progress):
        """Test marking as completed without total size."""
        progress.total_bytes = None
        progress.mark_completed()

        assert progress.state == DownloadState.COMPLETED
        assert progress.percentage == 100.0

    @pytest.mark.parametrize(
        ("speed", "expected"),
        [
            (512, "512.0 B/s"),
            (1024, "1.0 KB/s"),
            (1024 * 1024, "1.0 MB/s"),
            (1024 * 1024 * 1024, "1.0 GB/s"),
            (1536, "1.5 KB/s"),
            (2048 * 1024, "2.0 MB/s"),
        ],
    )
    def test_get_formatted_speed(self, progress, speed, expected):
        """Test speed formatting."""
        progress.bytes_per_second = speed
        assert progress.get_formatted_speed() == expected

    @pytest.mark.parametrize(
        ("downloaded", "total", "expected"),
        [
            (512, 1024, "512.0 B / 1.0 KB"),
            (1024, 2048, "1.0 KB / 2.0 KB"),
            (1024 * 1024, None, "1.0 MB / Unknown"),
            (0, 1024, "0 B / 1.0 KB"),
        ],
    )
    def test_get_formatted_size(self, progress, downloaded, total, expected):
        """Test size formatting."""
        progress.downloaded_bytes = downloaded
        progress.total_bytes = total
        assert progress.get_formatted_size() == expected

    @pytest.mark.parametrize(
        ("eta_seconds", "expected"),
        [
            (30, "30s"),
            (90, "1m 30s"),
            (3661, "1h 1m"),
            (7200, "2h 0m"),
            (None, "Unknown"),
        ],
    )
    def test_get_formatted_eta(self, progress, eta_seconds, expected):
        """Test ETA formatting."""
        progress.eta_seconds = eta_seconds
        assert progress.get_formatted_eta() == expected

    @pytest.mark.parametrize(
        ("bytes_count", "expected"),
        [
            (512, "512 B"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB"),
            (1536, "1.5 KB"),
            (0, "0 B"),
        ],
    )
    def test_format_bytes_static(self, progress, bytes_count, expected):
        """Test static byte formatting."""
        assert progress._format_bytes(bytes_count) == expected

    def test_progress_with_no_total_size(self):
        """Test progress tracking without total size."""
        progress = DownloadProgress(
            download_id=uuid4(),
            state=DownloadState.DOWNLOADING,
            total_bytes=None,
            eta_seconds=None,
            last_error=None,
        )

        progress.update_progress(512)
        assert progress.downloaded_bytes == 512
        assert progress.percentage == 0.0  # No total size, so 0%
        assert progress.eta_seconds is None

    def test_progress_eta_calculation(self, progress):
        """Test ETA calculation."""
        progress.update_progress(512)

        if progress.average_speed > 0:
            assert progress.eta_seconds is not None
            assert progress.eta_seconds > 0

    def test_progress_percentage_capping(self, progress):
        """Test that percentage is capped at 100%."""
        progress.update_progress(2048)  # More than total_bytes (1024)

        assert progress.percentage == 100.0

    def test_progress_negative_percentage(self, progress):
        """Test handling negative percentage."""
        progress.update_progress(-100)

        assert progress.percentage == 0.0


class TestProgressTracker:
    """Test the ProgressTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create a progress tracker instance."""
        return ProgressTracker()

    @pytest.fixture
    def download_id(self):
        """Create a test download ID."""
        return uuid4()

    def test_progress_tracker_creation(self, tracker):
        """Test creating a ProgressTracker instance."""
        assert tracker._progress == {}
        assert tracker._callbacks == []

    def test_add_callback(self, tracker):
        """Test adding a progress callback."""
        callback = Mock()
        tracker.add_callback(callback)

        assert callback in tracker._callbacks

    def test_remove_callback(self, tracker):
        """Test removing a progress callback."""
        callback = Mock()
        tracker.add_callback(callback)
        tracker.remove_callback(callback)

        assert callback not in tracker._callbacks

    def test_remove_nonexistent_callback(self, tracker):
        """Test removing a callback that doesn't exist."""
        callback = Mock()
        # Should not raise any errors
        tracker.remove_callback(callback)

    def test_start_tracking(self, tracker, download_id):
        """Test starting progress tracking."""
        progress = tracker.start_tracking(download_id, total_bytes=1024)

        assert progress.download_id == download_id
        assert progress.total_bytes == 1024
        assert progress.state == DownloadState.DOWNLOADING
        assert download_id in tracker._progress

    def test_start_tracking_no_total_size(self, tracker, download_id):
        """Test starting tracking without total size."""
        progress = tracker.start_tracking(download_id)

        assert progress.total_bytes is None
        assert progress.state == DownloadState.DOWNLOADING

    def test_update_progress(self, tracker, download_id):
        """Test updating progress."""
        tracker.start_tracking(download_id, total_bytes=1024)
        tracker.update_progress(download_id, 512)

        progress = tracker._progress[download_id]
        assert progress.downloaded_bytes == 512
        assert progress.percentage == 50.0

    def test_update_progress_nonexistent(self, tracker, download_id):
        """Test updating progress for non-existent download."""
        # Should not raise any errors
        tracker.update_progress(download_id, 512)

    def test_set_total_size(self, tracker, download_id):
        """Test setting total size."""
        tracker.start_tracking(download_id)
        tracker.set_total_size(download_id, 2048)

        progress = tracker._progress[download_id]
        assert progress.total_bytes == 2048

    def test_set_total_size_nonexistent(self, tracker, download_id):
        """Test setting total size for non-existent download."""
        # Should not raise any errors
        tracker.set_total_size(download_id, 2048)

    def test_mark_completed(self, tracker, download_id):
        """Test marking download as completed."""
        tracker.start_tracking(download_id, total_bytes=1024)
        tracker.mark_completed(download_id)

        progress = tracker._progress[download_id]
        assert progress.state == DownloadState.COMPLETED
        assert progress.percentage == 100.0

    def test_mark_completed_nonexistent(self, tracker, download_id):
        """Test marking non-existent download as completed."""
        # Should not raise any errors
        tracker.mark_completed(download_id)

    def test_mark_error(self, tracker, download_id):
        """Test marking download as error."""
        tracker.start_tracking(download_id)
        error_message = "Network error"
        tracker.mark_error(download_id, error_message)

        progress = tracker._progress[download_id]
        assert progress.state == DownloadState.FAILED
        assert progress.last_error == error_message
        assert progress.error_count == 1

    def test_mark_error_nonexistent(self, tracker, download_id):
        """Test marking non-existent download as error."""
        # Should not raise any errors
        tracker.mark_error(download_id, "Error")

    def test_get_progress(self, tracker, download_id):
        """Test getting progress for specific download."""
        tracker.start_tracking(download_id)
        progress = tracker.get_progress(download_id)

        assert progress is not None
        assert progress.download_id == download_id

    def test_get_progress_nonexistent(self, tracker, download_id):
        """Test getting progress for non-existent download."""
        progress = tracker.get_progress(download_id)
        assert progress is None

    def test_get_all_progress(self, tracker):
        """Test getting all progress."""
        download_id1 = uuid4()
        download_id2 = uuid4()

        tracker.start_tracking(download_id1)
        tracker.start_tracking(download_id2)

        all_progress = tracker.get_all_progress()

        assert len(all_progress) == 2
        assert download_id1 in all_progress
        assert download_id2 in all_progress

    def test_remove_progress(self, tracker, download_id):
        """Test removing progress tracking."""
        tracker.start_tracking(download_id)
        tracker.remove_progress(download_id)

        assert download_id not in tracker._progress

    def test_remove_progress_nonexistent(self, tracker, download_id):
        """Test removing non-existent progress."""
        # Should not raise any errors
        tracker.remove_progress(download_id)

    def test_clear_completed(self, tracker):
        """Test clearing completed downloads."""
        download_id1 = uuid4()
        download_id2 = uuid4()

        tracker.start_tracking(download_id1)
        tracker.start_tracking(download_id2)

        # Mark one as completed
        tracker.mark_completed(download_id1)

        tracker.clear_completed()

        assert download_id1 not in tracker._progress
        assert download_id2 in tracker._progress

    def test_callback_execution(self, tracker, download_id):
        """Test that callbacks are executed."""
        callback = Mock()
        tracker.add_callback(callback)

        tracker.start_tracking(download_id)

        # Callback should be called
        assert callback.call_count > 0
        call_args = callback.call_args
        assert call_args[0][0] == download_id
        assert isinstance(call_args[0][1], DownloadProgress)

    def test_callback_exception_handling(self, tracker, download_id):
        """Test that callback exceptions don't break tracking."""

        def failing_callback(download_id, progress):
            msg = "Callback error"
            raise ValueError(msg)

        tracker.add_callback(failing_callback)

        # Should not raise any errors
        tracker.start_tracking(download_id)

    def test_multiple_callbacks(self, tracker, download_id):
        """Test multiple callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        tracker.add_callback(callback1)
        tracker.add_callback(callback2)

        tracker.start_tracking(download_id)

        assert callback1.call_count > 0
        assert callback2.call_count > 0

    def test_callback_removal_during_execution(self, tracker, download_id):
        """Test removing callback during execution."""
        callbacks_called = []

        def callback1(download_id, progress):
            callbacks_called.append("callback1")
            tracker.remove_callback(callback1)

        def callback2(download_id, progress):
            callbacks_called.append("callback2")

        tracker.add_callback(callback1)
        tracker.add_callback(callback2)

        tracker.start_tracking(download_id)

        assert "callback1" in callbacks_called
        assert "callback2" in callbacks_called

    def test_progress_tracker_context_manager(self, tracker):
        """Test ProgressTracker as context manager."""
        with tracker as ctx_tracker:
            assert ctx_tracker is tracker
            assert tracker._progress == {}
            assert tracker._callbacks == []


class TestProgressCallbackProtocol:
    """Test the ProgressCallback protocol."""

    def test_progress_callback_protocol(self):
        """Test that a function can be used as a progress callback."""

        def test_callback(download_id, progress, **kwargs):
            pass

        # This should not raise any errors
        callback: ProgressCallback = test_callback
        assert callable(callback)

    def test_progress_callback_with_kwargs(self):
        """Test progress callback with additional kwargs."""

        def test_callback(download_id, progress, extra_data=None, **kwargs):
            pass

        # This should not raise any errors
        callback: ProgressCallback = test_callback
        assert callable(callback)


class TestProgressIntegration:
    """Test integration between progress components."""

    def test_full_download_progress_cycle(self):
        """Test a complete download progress cycle."""
        tracker = ProgressTracker()
        download_id = uuid4()

        # Start tracking
        progress = tracker.start_tracking(download_id, total_bytes=1024)
        assert progress.state == DownloadState.DOWNLOADING
        assert progress.percentage == 0.0

        # Update progress
        tracker.update_progress(download_id, 512)
        progress = tracker.get_progress(download_id)
        assert progress is not None
        assert progress.percentage == 50.0
        assert progress.downloaded_bytes == 512

        # Complete download
        tracker.mark_completed(download_id)
        progress = tracker.get_progress(download_id)
        assert progress is not None
        assert progress.state == DownloadState.COMPLETED
        assert progress.percentage == 100.0

        # Clear completed
        tracker.clear_completed()
        assert tracker.get_progress(download_id) is None

    def test_download_with_errors(self):
        """Test download progress with errors."""
        tracker = ProgressTracker()
        download_id = uuid4()

        # Start tracking
        tracker.start_tracking(download_id, total_bytes=1024)

        # Mark error
        tracker.mark_error(download_id, "Network error")
        progress = tracker.get_progress(download_id)
        assert progress is not None
        assert progress.state == DownloadState.FAILED
        assert progress.error_count == 1
        assert progress.last_error == "Network error"

        # Try again
        tracker.mark_error(download_id, "Another error")
        progress = tracker.get_progress(download_id)
        assert progress is not None
        assert progress.error_count == 2

    def test_multiple_downloads(self):
        """Test tracking multiple downloads."""
        tracker = ProgressTracker()
        download_id1 = uuid4()
        download_id2 = uuid4()

        # Start both downloads
        tracker.start_tracking(download_id1, total_bytes=1024)
        tracker.start_tracking(download_id2, total_bytes=2048)

        # Update progress on both
        tracker.update_progress(download_id1, 512)
        tracker.update_progress(download_id2, 1024)

        # Check progress
        progress1 = tracker.get_progress(download_id1)
        progress2 = tracker.get_progress(download_id2)

        assert progress1 is not None
        assert progress2 is not None
        assert progress1.percentage == 50.0
        assert progress2.percentage == 50.0

        # Complete one
        tracker.mark_completed(download_id1)
        assert progress1.state == DownloadState.COMPLETED
        assert progress2.state == DownloadState.DOWNLOADING
