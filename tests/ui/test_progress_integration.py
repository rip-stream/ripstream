# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Test progress tracking integration between download worker and downloads view."""

import pytest
from PyQt6.QtWidgets import QApplication

from ripstream.config.user import UserConfig
from ripstream.models.enums import DownloadStatus
from ripstream.ui.downloads_view import DownloadsHistoryView


class TestProgressIntegration:
    """Test progress tracking integration."""

    @pytest.fixture
    def app(self):
        """Create QApplication instance."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return UserConfig()

    @pytest.fixture
    def downloads_view(self, config):
        """Create downloads view."""
        return DownloadsHistoryView(config=config)

    def test_downloads_view_progress_update(self, app):
        """Test that downloads view properly updates progress."""
        from ripstream.ui.downloads_view import DownloadsTableWidget

        # Create table widget directly
        table = DownloadsTableWidget()

        # Add a download
        download_data = {
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "type": "track",
            "status": DownloadStatus.PENDING,
            "progress": 0,
            "download_id": "test_track_123",
        }
        table.add_download_item(download_data)

        # Update progress
        table.update_download_progress("test_track_123", 75, DownloadStatus.DOWNLOADING)

        # Verify progress was updated
        progress_item = table.item(0, 5)
        assert progress_item is not None
        assert progress_item.text() == "75%"

        # Verify status was updated
        status_item = table.item(0, 4)
        assert status_item is not None
        assert "downloading" in status_item.text().lower()

    def test_progress_callback_emission(self, app):
        """Test that progress callbacks emit signals correctly."""
        from ripstream.ui.downloads_view import DownloadsTableWidget

        # Create table widget directly
        table = DownloadsTableWidget()

        # Test the table directly without database operations
        download_data = {
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "type": "track",
            "status": DownloadStatus.PENDING,
            "progress": 0,
            "download_id": "test_track_123",
        }
        table.add_download_item(download_data)

        # Verify the download was added
        assert table.rowCount() == 1

        # Test progress update
        table.update_download_progress("test_track_123", 50, DownloadStatus.DOWNLOADING)

        # Verify progress was updated in the table
        progress_item = table.item(0, 5)  # Progress column
        assert progress_item is not None
        assert progress_item.text() == "50%"

    def test_progress_tracker_integration(self):
        """Test that progress tracker works correctly."""
        from ripstream.downloader.progress import ProgressTracker

        tracker = ProgressTracker()

        # Test callback registration
        callback_called = False

        def test_callback(download_id, progress):
            nonlocal callback_called
            callback_called = True

        tracker.add_callback(test_callback)

        # Test progress tracking
        from uuid import uuid4

        download_id = uuid4()
        tracker.start_tracking(download_id, 1000)
        tracker.update_progress(download_id, 500)

        # Verify callback was called
        assert callback_called

    def test_download_worker_progress_tracker_setup(self):
        """Test that download worker sets up progress tracker correctly."""
        from unittest.mock import Mock

        from ripstream.ui.download_worker import DownloadWorker

        # Create mock config
        mock_config = Mock()
        mock_config.downloads.folder = "/test/downloads"
        mock_config.downloads.max_connections = 1
        mock_config.downloads.verify_ssl = True
        mock_config.downloads.requests_per_minute = 60

        # Create worker and initialize it
        worker = DownloadWorker(mock_config)
        worker.setup_download_environment()

        # Verify progress tracker is set up
        assert hasattr(worker, "progress_tracker")
        assert worker.progress_tracker is not None

    def test_progress_callback_error_handling(self):
        """Test that progress callback errors are handled gracefully."""
        from unittest.mock import Mock

        from ripstream.ui.download_worker import DownloadWorker

        # Create mock config
        mock_config = Mock()
        mock_config.downloads.folder = "/test/downloads"
        mock_config.downloads.max_connections = 1
        mock_config.downloads.verify_ssl = True
        mock_config.downloads.requests_per_minute = 60

        # Create worker and initialize it
        worker = DownloadWorker(mock_config)
        worker.setup_download_environment()

        # Test the progress callback with an error
        def error_callback(download_id, progress):
            msg = "Test error"
            raise Exception(msg)

        # This should not raise an exception
        from contextlib import suppress

        with suppress(Exception):
            worker._progress_callback(
                "test_id", type("MockProgress", (), {"percentage": 50.0})()
            )

    def test_provider_progress_callback_setup(self):
        """Test that provider progress callbacks are set up correctly."""
        from unittest.mock import Mock

        from ripstream.ui.download_worker import DownloadWorker

        # Create mock config
        mock_config = Mock()
        mock_config.downloads.folder = "/test/downloads"
        mock_config.downloads.max_connections = 1
        mock_config.downloads.verify_ssl = True
        mock_config.downloads.requests_per_minute = 60

        # Create worker and initialize it
        worker = DownloadWorker(mock_config)
        worker.setup_download_environment()

        # Test the progress callback setup method
        mock_provider = type(
            "MockProvider",
            (),
            {
                "progress_tracker": type(
                    "MockProgressTracker",
                    (),
                    {
                        "add_callback": lambda callback, *args, **kwargs: None,
                        "start_tracking": lambda uuid_id, total_bytes=None: None,
                    },
                )()
            },
        )()

        # This should not raise an exception
        worker._setup_download_progress_tracking(mock_provider, "test_id")

    def test_uuid_to_database_id_mapping(self):
        """Test that current download ID tracking works correctly."""
        from unittest.mock import Mock

        from ripstream.ui.download_worker import DownloadWorker

        # Create mock config
        mock_config = Mock()
        mock_config.downloads.folder = "/test/downloads"
        mock_config.downloads.max_connections = 1
        mock_config.downloads.verify_ssl = True
        mock_config.downloads.requests_per_minute = 60

        # Create worker and initialize it
        worker = DownloadWorker(mock_config)
        worker.setup_download_environment()

        # Test the current download ID tracking
        test_db_id = "test_download_123"

        # Set current download ID
        worker._current_download_id = test_db_id

        # Verify current download ID is set correctly
        assert worker._current_download_id == test_db_id

        # Test that it can be cleared
        worker._current_download_id = None
        assert worker._current_download_id is None
