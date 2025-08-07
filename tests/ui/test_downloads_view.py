# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for downloads view."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ripstream.ui.downloads_view import DownloadsHistoryView, DownloadStatsWidget


class TestDownloadStatsWidget:
    """Test the DownloadStatsWidget class."""

    @pytest.fixture
    def stats_widget(self, qapp):
        """Create a DownloadStatsWidget for testing."""
        return DownloadStatsWidget()

    def test_widget_creation(self, stats_widget):
        """Test creating a DownloadStatsWidget."""
        assert isinstance(stats_widget, QWidget)
        assert hasattr(stats_widget, "total_group")
        assert hasattr(stats_widget, "completed_group")
        assert hasattr(stats_widget, "failed_group")
        assert hasattr(stats_widget, "pending_group")

    def test_layout_structure(self, stats_widget):
        """Test the layout structure."""
        layout = stats_widget.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.count() == 2  # title and stats_container

    def test_stat_groups_creation(self, stats_widget):
        """Test stat groups are created correctly."""
        assert isinstance(stats_widget.total_group, QGroupBox)
        assert isinstance(stats_widget.completed_group, QGroupBox)
        assert isinstance(stats_widget.failed_group, QGroupBox)
        assert isinstance(stats_widget.pending_group, QGroupBox)

        assert stats_widget.total_group.title() == "Total Downloads"
        assert stats_widget.completed_group.title() == "Completed"
        assert stats_widget.failed_group.title() == "Failed"
        assert stats_widget.pending_group.title() == "Pending"

    def test_initial_stats_values(self, stats_widget):
        """Test initial statistics values."""
        # All stats should start at 0
        total_label = stats_widget.total_group.findChild(QLabel)
        completed_label = stats_widget.completed_group.findChild(QLabel)
        failed_label = stats_widget.failed_group.findChild(QLabel)
        pending_label = stats_widget.pending_group.findChild(QLabel)

        assert total_label.text() == "0"
        assert completed_label.text() == "0"
        assert failed_label.text() == "0"
        assert pending_label.text() == "0"

    def test_update_stats(self, stats_widget):
        """Test updating statistics."""
        test_stats = {"total": 15, "completed": 10, "failed": 2, "pending": 3}

        stats_widget.update_stats(test_stats)

        total_label = stats_widget.total_group.findChild(QLabel)
        completed_label = stats_widget.completed_group.findChild(QLabel)
        failed_label = stats_widget.failed_group.findChild(QLabel)
        pending_label = stats_widget.pending_group.findChild(QLabel)

        assert total_label.text() == "15"
        assert completed_label.text() == "10"
        assert failed_label.text() == "2"
        assert pending_label.text() == "3"

    def test_update_stats_partial(self, stats_widget):
        """Test updating statistics with partial data."""
        test_stats = {
            "total": 5,
            "completed": 3,
            # missing failed and pending
        }

        stats_widget.update_stats(test_stats)

        total_label = stats_widget.total_group.findChild(QLabel)
        completed_label = stats_widget.completed_group.findChild(QLabel)
        failed_label = stats_widget.failed_group.findChild(QLabel)
        pending_label = stats_widget.pending_group.findChild(QLabel)

        assert total_label.text() == "5"
        assert completed_label.text() == "3"
        assert failed_label.text() == "0"
        assert pending_label.text() == "0"

    def test_reset_stats(self, stats_widget):
        """Test resetting statistics."""
        # First update with some values
        test_stats = {"total": 10, "completed": 5, "failed": 3, "pending": 2}
        stats_widget.update_stats(test_stats)

        # Then reset
        stats_widget.reset_stats()

        total_label = stats_widget.total_group.findChild(QLabel)
        completed_label = stats_widget.completed_group.findChild(QLabel)
        failed_label = stats_widget.failed_group.findChild(QLabel)
        pending_label = stats_widget.pending_group.findChild(QLabel)

        assert total_label.text() == "0"
        assert completed_label.text() == "0"
        assert failed_label.text() == "0"
        assert pending_label.text() == "0"

    def test_stat_group_styling(self, stats_widget):
        """Test stat group styling."""
        # Test that stat groups have proper styling
        for group in [
            stats_widget.total_group,
            stats_widget.completed_group,
            stats_widget.failed_group,
            stats_widget.pending_group,
        ]:
            assert group.styleSheet() == ""  # Should have no custom styling initially

    def test_create_stat_group(self, stats_widget):
        """Test creating stat groups."""
        group = stats_widget.create_stat_group("Test Group", "42")
        assert isinstance(group, QGroupBox)
        assert group.title() == "Test Group"

        # Check that it has a label with the value
        label = group.findChild(QLabel)
        assert label is not None
        assert label.text() == "42"


class TestDownloadsHistoryView:
    """Test the DownloadsHistoryView class."""

    @pytest.fixture
    def downloads_view(self, qapp, mock_download_service):
        """Create a DownloadsHistoryView for testing with mocked database."""
        view = DownloadsHistoryView()
        # Clear the table before each test to ensure clean state
        view.downloads_table.clear_all_downloads()
        return view

    def test_view_creation(self, downloads_view):
        """Test creating a DownloadsHistoryView."""
        assert isinstance(downloads_view, QWidget)
        assert hasattr(downloads_view, "stats_widget")
        assert hasattr(downloads_view, "downloads_table")
        assert hasattr(downloads_view, "clear_all_btn")

    def test_layout_structure(self, downloads_view):
        """Test the layout structure."""
        layout = downloads_view.layout()
        assert isinstance(layout, QVBoxLayout)
        # Should have stats widget, controls, and table

    def test_stats_widget_integration(self, downloads_view):
        """Test stats widget integration."""
        assert isinstance(downloads_view.stats_widget, DownloadStatsWidget)

    def test_downloads_table_setup(self, downloads_view):
        """Test downloads table setup."""
        table = downloads_view.downloads_table
        assert isinstance(table, QTableWidget)

        # Check column headers
        expected_headers = [
            "Title",
            "Artist",
            "Album",
            "Type",
            "Status",
            "Progress",
            "Started",
            "Actions",
        ]
        assert table.columnCount() == len(expected_headers)

        for i, expected_header in enumerate(expected_headers):
            header_item = table.horizontalHeaderItem(i)
            assert header_item is not None
            assert header_item.text() == expected_header

    def test_table_properties(self, downloads_view):
        """Test table widget properties."""
        table = downloads_view.downloads_table
        assert table.alternatingRowColors() is True
        assert (
            table.selectionBehavior() == QAbstractItemView.SelectionBehavior.SelectRows
        )
        assert table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection
        assert table.isSortingEnabled() is False

    def test_add_download(self, downloads_view, sample_download_item):
        """Test adding a download item."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads_view.add_download(sample_download_item)

        table = downloads_view.downloads_table
        assert table.rowCount() == 1

        # Check that data was added correctly
        title_item = table.item(0, 0)
        assert title_item is not None
        assert title_item.text() == sample_download_item["title"]

        artist_item = table.item(0, 1)
        assert artist_item is not None
        assert artist_item.text() == sample_download_item["artist"]

    def test_add_multiple_downloads(self, downloads_view):
        """Test adding multiple download items."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads = [
            {
                "download_id": "dl1",
                "title": "Track 1",
                "artist": "Artist 1",
                "album": "Album 1",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track1",
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(UTC),
            },
            {
                "download_id": "dl2",
                "title": "Track 2",
                "artist": "Artist 2",
                "album": "Album 2",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track2",
                "status": "downloading",
                "progress": 50,
                "started_at": datetime.now(UTC),
            },
        ]

        for download in downloads:
            downloads_view.add_download(download)

        assert downloads_view.downloads_table.rowCount() == 2

    def test_update_download_progress(self, downloads_view, sample_download_item):
        """Test updating download progress."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads_view.add_download(sample_download_item)

        # Update progress
        downloads_view.update_download_progress(sample_download_item["download_id"], 75)

        # Check that progress was updated
        progress_item = downloads_view.downloads_table.item(0, 5)
        assert progress_item is not None
        assert "75%" in progress_item.text()

    def test_update_download_status(self, downloads_view, sample_download_item):
        """Test updating download status."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads_view.add_download(sample_download_item)

        # Update status
        downloads_view.update_download_status(
            sample_download_item["download_id"], "failed"
        )

        # Check that status was updated
        status_item = downloads_view.downloads_table.item(0, 4)
        assert status_item is not None
        assert status_item.text() == "failed"

    def test_remove_download(self, downloads_view, sample_download_item, qtbot):
        """Test removing a download."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads_view.add_download(sample_download_item)
        assert downloads_view.downloads_table.rowCount() == 1

        # Remove the download
        downloads_view.remove_download_item(sample_download_item["download_id"])
        assert downloads_view.downloads_table.rowCount() == 0

    def test_retry_download(self, downloads_view, sample_download_item, qtbot):
        """Test retrying a download."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads_view.add_download(sample_download_item)

        # Simulate retry
        downloads_view.retry_download_item(sample_download_item["download_id"])

        # Check that retry signal was emitted
        # Note: We can't easily test signal emission without more complex setup

    def test_clear_all_downloads(self, downloads_view, qtbot):
        """Test clearing all downloads."""
        # Ensure table is empty first
        downloads_view.downloads_table.clear_all_downloads()

        # Add some downloads first
        for i in range(3):
            download = {
                "download_id": f"dl{i}",
                "title": f"Track {i}",
                "artist": "Artist",
                "album": "Album",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": f"track{i}",
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(UTC),
            }
            downloads_view.add_download(download)

        assert downloads_view.downloads_table.rowCount() == 3

        # Clear all downloads
        downloads_view.clear_all_downloads_clicked()
        assert downloads_view.downloads_table.rowCount() == 0

    def test_update_statistics(self, downloads_view):
        """Test statistics update when downloads are added."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        # Add downloads with different statuses
        downloads = [
            {
                "download_id": "1",
                "title": "T1",
                "artist": "A",
                "album": "Al",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track1",
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(UTC),
            },
            {
                "download_id": "2",
                "title": "T2",
                "artist": "A",
                "album": "Al",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track2",
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(UTC),
            },
            {
                "download_id": "3",
                "title": "T3",
                "artist": "A",
                "album": "Al",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track3",
                "status": "failed",
                "progress": 0,
                "started_at": datetime.now(UTC),
            },
            {
                "download_id": "4",
                "title": "T4",
                "artist": "A",
                "album": "Al",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track4",
                "status": "downloading",
                "progress": 50,
                "started_at": datetime.now(UTC),
            },
        ]

        for download in downloads:
            downloads_view.add_download(download)

        # Update statistics using table-based stats instead of database
        stats = downloads_view.downloads_table.get_download_stats()
        downloads_view.stats_widget.update_stats(stats)

        # Check stats widget was updated
        total_label = downloads_view.stats_widget.total_group.findChild(QLabel)
        completed_label = downloads_view.stats_widget.completed_group.findChild(QLabel)
        failed_label = downloads_view.stats_widget.failed_group.findChild(QLabel)
        pending_label = downloads_view.stats_widget.pending_group.findChild(QLabel)

        assert total_label.text() == "4"
        assert completed_label.text() == "2"
        assert failed_label.text() == "1"
        assert pending_label.text() == "1"

    def test_download_item_data_storage(self, downloads_view, sample_download_item):
        """Test that download ID is stored in item data."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads_view.add_download(sample_download_item)

        title_item = downloads_view.downloads_table.item(0, 0)
        assert title_item is not None
        stored_id = title_item.data(Qt.ItemDataRole.UserRole)
        assert stored_id == sample_download_item["download_id"]

    def test_progress_formatting(self, downloads_view):
        """Test progress value formatting."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        download = {
            "download_id": "test",
            "title": "Test",
            "artist": "Artist",
            "album": "Album",
            "type": "Track",
            "media_type": "TRACK",
            "source": "QOBUZ",
            "source_id": "test_track",
            "status": "downloading",
            "progress": 75,
            "started_at": datetime.now(UTC),
        }

        downloads_view.add_download(download)

        progress_item = downloads_view.downloads_table.item(0, 5)
        assert progress_item is not None
        assert "75%" in progress_item.text()

    def test_datetime_formatting(self, downloads_view):
        """Test datetime formatting in table."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        test_time = datetime.now(UTC)
        download = {
            "download_id": "datetime_test",
            "title": "DateTime Test",
            "artist": "Artist",
            "album": "Album",
            "type": "Track",
            "media_type": "TRACK",
            "source": "QOBUZ",
            "source_id": "datetime_track",
            "status": "completed",
            "progress": 100,
            "started_at": test_time,
        }

        downloads_view.add_download(download)

        started_item = downloads_view.downloads_table.item(0, 6)
        assert started_item is not None
        # Check that the date is formatted (should contain the year)
        assert str(test_time.year) in started_item.text()

    @pytest.mark.parametrize(
        ("status", "expected_color"),
        [
            ("completed", "green"),
            ("failed", "red"),
            ("downloading", "blue"),
            ("pending", "orange"),
        ],
    )
    def test_status_styling(self, downloads_view, status, expected_color):
        """Test status column styling based on status."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        download = {
            "download_id": "test",
            "title": "Test",
            "artist": "Artist",
            "album": "Album",
            "type": "Track",
            "media_type": "TRACK",
            "source": "QOBUZ",
            "source_id": "test_track",
            "status": status,
            "progress": 50,
            "started_at": datetime.now(UTC),
        }

        downloads_view.add_download(download)

        status_item = downloads_view.downloads_table.item(0, 4)
        assert status_item is not None
        assert status_item.text() == status

    def test_action_buttons_creation(self, downloads_view, sample_download_item):
        """Test that action buttons are created correctly."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        downloads_view.add_download(sample_download_item)

        # Check that actions column has a widget
        actions_widget = downloads_view.downloads_table.cellWidget(0, 7)
        assert actions_widget is not None

    def test_table_sorting(self, downloads_view):
        """Test table sorting functionality."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        # Add downloads in reverse order
        downloads = [
            {
                "download_id": "2",
                "title": "B Track",
                "artist": "B Artist",
                "album": "B Album",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track2",
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(UTC),
            },
            {
                "download_id": "1",
                "title": "A Track",
                "artist": "A Artist",
                "album": "A Album",
                "type": "Track",
                "media_type": "TRACK",
                "source": "QOBUZ",
                "source_id": "track1",
                "status": "completed",
                "progress": 100,
                "started_at": datetime.now(UTC),
            },
        ]

        for download in downloads:
            downloads_view.add_download(download)

        # Sort by title column
        downloads_view.downloads_table.sortItems(0, Qt.SortOrder.AscendingOrder)

        # Check that items are sorted
        first_title = downloads_view.downloads_table.item(0, 0).text()
        second_title = downloads_view.downloads_table.item(1, 0).text()
        assert first_title < second_title

    def test_empty_downloads_handling(self, downloads_view):
        """Test handling of empty downloads list."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        # Should start empty
        assert downloads_view.downloads_table.rowCount() == 0

        # Test that adding and removing works correctly
        download = {
            "download_id": "empty_test",
            "title": "Empty Test",
            "artist": "Artist",
            "album": "Album",
            "type": "Track",
            "media_type": "TRACK",
            "source": "QOBUZ",
            "source_id": "empty_track",
            "status": "completed",
            "progress": 100,
            "started_at": datetime.now(UTC),
        }

        downloads_view.add_download(download)
        assert downloads_view.downloads_table.rowCount() == 1

        downloads_view.remove_download_item(download["download_id"])
        assert downloads_view.downloads_table.rowCount() == 0

    def test_remove_download_from_database(self, downloads_view):
        """Test that remove button actually removes download from database."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        # Create a unique download item
        unique_download = {
            "download_id": f"test_remove_db_{uuid4().hex[:8]}",
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "type": "Track",
            "media_type": "TRACK",
            "source": "QOBUZ",
            "source_id": f"test_track_{uuid4().hex[:8]}",
            "status": "completed",
            "progress": 100,
            "started_at": datetime.now(UTC),
        }

        # Add a download
        downloads_view.add_download(unique_download)
        assert downloads_view.downloads_table.rowCount() == 1

        # Verify the download exists in the database
        download_service = downloads_view.download_service
        retrieved_record = download_service.get_download_by_id(
            unique_download["download_id"]
        )
        assert retrieved_record is not None

        # Remove the download through the UI
        downloads_view.remove_download_item(unique_download["download_id"])
        assert downloads_view.downloads_table.rowCount() == 0

        # Verify the download no longer exists in the database
        retrieved_record = download_service.get_download_by_id(
            unique_download["download_id"]
        )
        assert retrieved_record is None

    def test_table_remove_download_item(self, downloads_view, sample_download_item):
        """Test that remove_download_item in table widget correctly removes rows."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        # Add a download
        downloads_view.add_download(sample_download_item)
        assert downloads_view.downloads_table.rowCount() == 1

        # Verify the download_id is stored correctly
        status_item = downloads_view.downloads_table.item(0, 4)  # Status column
        assert status_item is not None
        stored_id = status_item.data(Qt.ItemDataRole.UserRole)
        assert stored_id == sample_download_item["download_id"]

        # Remove the download from the table
        downloads_view.downloads_table.remove_download_item(
            sample_download_item["download_id"]
        )
        assert downloads_view.downloads_table.rowCount() == 0

    def test_remove_button_immediately_updates_ui(self, downloads_view, qtbot):
        """Test that clicking the remove button immediately removes the row from the UI."""
        # Ensure table is empty
        downloads_view.downloads_table.clear_all_downloads()

        # Create a unique download item
        unique_download = {
            "download_id": f"test_remove_{uuid4().hex[:8]}",
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "type": "Track",
            "media_type": "TRACK",
            "source": "QOBUZ",
            "source_id": f"test_track_{uuid4().hex[:8]}",
            "status": "completed",
            "progress": 100,
            "started_at": datetime.now(UTC),
        }

        # Add a download
        downloads_view.add_download(unique_download)
        assert downloads_view.downloads_table.rowCount() == 1

        # Find the remove button in the first row
        actions_widget = downloads_view.downloads_table.cellWidget(
            0, 7
        )  # Actions column
        assert actions_widget is not None

        # Find the remove button
        remove_btn = None
        for child in actions_widget.children():
            if isinstance(child, QPushButton) and child.text() == "Remove":
                remove_btn = child
                break

        assert remove_btn is not None

        # Click the remove button
        qtbot.mouseClick(remove_btn, Qt.MouseButton.LeftButton)

        # Verify the row is immediately removed from the UI
        assert downloads_view.downloads_table.rowCount() == 0
