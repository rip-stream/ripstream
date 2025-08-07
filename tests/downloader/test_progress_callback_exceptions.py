# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for progress callback exception handling."""

import logging
from unittest.mock import Mock
from uuid import uuid4

import pytest

from ripstream.downloader.progress import ProgressTracker


class TestProgressCallbackExceptions:
    """Test exception handling in progress callbacks."""

    def test_callback_type_error_handled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that TypeError in callback is handled gracefully."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def failing_callback(download_id, progress):
            # Simulate TypeError
            msg = "Invalid argument type"
            raise TypeError(msg)

        tracker.add_callback(failing_callback)

        with caplog.at_level(logging.WARNING):
            tracker.start_tracking(download_id)

        # Should have logged warning but not crashed
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Progress callback failed" in caplog.records[0].message
        assert str(download_id) in caplog.records[0].message

        # Progress should still be tracked
        assert tracker.get_progress(download_id) is not None

    def test_callback_value_error_handled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that ValueError in callback is handled gracefully."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def failing_callback(download_id, progress):
            # Simulate ValueError
            msg = "Invalid value"
            raise ValueError(msg)

        tracker.add_callback(failing_callback)

        with caplog.at_level(logging.WARNING):
            # Start tracking first, then update
            tracker.start_tracking(download_id)
            tracker.update_progress(download_id, 100)

        # Should have logged warning
        assert any(
            "Progress callback failed" in record.message for record in caplog.records
        )

    def test_callback_attribute_error_handled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that AttributeError in callback is handled gracefully."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def failing_callback(download_id, progress):
            # Simulate AttributeError
            msg = "'NoneType' object has no attribute 'foo'"
            raise AttributeError(msg)

        tracker.add_callback(failing_callback)

        with caplog.at_level(logging.WARNING):
            tracker.start_tracking(download_id)

        # Should have logged warning
        assert any(
            "Progress callback failed" in record.message for record in caplog.records
        )

    def test_callback_key_error_handled(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that KeyError in callback is handled gracefully."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def failing_callback(download_id, progress):
            # Simulate KeyError
            msg = "missing_key"
            raise KeyError(msg)

        tracker.add_callback(failing_callback)

        with caplog.at_level(logging.WARNING):
            tracker.start_tracking(download_id)

        # Should have logged warning
        assert any(
            "Progress callback failed" in record.message for record in caplog.records
        )

    def test_callback_index_error_handled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that IndexError in callback is handled gracefully."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def failing_callback(download_id, progress):
            # Simulate IndexError
            msg = "list index out of range"
            raise IndexError(msg)

        tracker.add_callback(failing_callback)

        with caplog.at_level(logging.WARNING):
            tracker.start_tracking(download_id)

        # Should have logged warning
        assert any(
            "Progress callback failed" in record.message for record in caplog.records
        )

    def test_callback_unexpected_exception_handled(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that unexpected exceptions in callback are handled and logged as errors."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def failing_callback(download_id, progress):
            # Simulate unexpected exception
            msg = "Unexpected runtime error"
            raise RuntimeError(msg)

        tracker.add_callback(failing_callback)

        with caplog.at_level(logging.ERROR):
            tracker.start_tracking(download_id)

        # Should have logged error for unexpected exception
        assert any(
            "Unexpected error in progress callback" in record.message
            for record in caplog.records
        )
        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_records) == 1

    def test_multiple_callbacks_one_fails(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that one failing callback doesn't prevent others from being called."""
        tracker = ProgressTracker()
        download_id = uuid4()

        successful_callback = Mock()

        def failing_callback(download_id, progress):
            msg = "Callback failed"
            raise ValueError(msg)

        tracker.add_callback(failing_callback)
        tracker.add_callback(successful_callback)

        with caplog.at_level(logging.WARNING):
            tracker.start_tracking(download_id)

        # Successful callback should still be called
        successful_callback.assert_called_once()

        # Should have logged warning for failed callback
        assert any(
            "Progress callback failed" in record.message for record in caplog.records
        )

    def test_callback_system_exit_not_caught(self) -> None:
        """Test that SystemExit is not caught (should propagate)."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def exit_callback(download_id, progress):
            msg = "Exiting"
            raise SystemExit(msg)

        tracker.add_callback(exit_callback)

        # SystemExit should propagate and not be caught
        with pytest.raises(SystemExit):
            tracker.start_tracking(download_id)

    def test_callback_keyboard_interrupt_not_caught(self) -> None:
        """Test that KeyboardInterrupt is not caught (should propagate)."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def interrupt_callback(download_id, progress):
            msg = "User interrupted"
            raise KeyboardInterrupt(msg)

        tracker.add_callback(interrupt_callback)

        # KeyboardInterrupt should propagate and not be caught
        with pytest.raises(KeyboardInterrupt):
            tracker.start_tracking(download_id)

    def test_progress_tracking_continues_after_callback_failure(self) -> None:
        """Test that progress tracking continues normally after callback failures."""
        tracker = ProgressTracker()
        download_id = uuid4()

        def failing_callback(download_id, progress):
            msg = "Always fails"
            raise ValueError(msg)

        tracker.add_callback(failing_callback)

        # Start tracking
        progress = tracker.start_tracking(download_id, total_bytes=1000)
        assert progress is not None

        # Update progress - should work despite callback failure
        tracker.update_progress(download_id, 500)
        updated_progress = tracker.get_progress(download_id)
        assert updated_progress is not None
        assert updated_progress.downloaded_bytes == 500

        # Mark completed - should work despite callback failure
        tracker.mark_completed(download_id)
        final_progress = tracker.get_progress(download_id)
        assert final_progress is not None
        assert final_progress.is_complete
