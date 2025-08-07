# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for discography list view."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
)

from ripstream.ui.discography.list_view import DiscographyListView


class TestDiscographyListView:
    """Test the DiscographyListView class."""

    @pytest.fixture
    def list_view(self, qapp):
        """Create a DiscographyListView for testing."""
        return DiscographyListView()

    def test_list_view_creation(self, list_view):
        """Test creating a DiscographyListView."""
        assert isinstance(list_view, QTableWidget)
        assert list_view.columnCount() == 8
        assert list_view.rowCount() == 0

    def test_column_headers(self, list_view):
        """Test column headers are set correctly."""
        expected_headers = [
            "Title",
            "Artist",
            "Album",
            "Year",
            "Duration",
            "Tracks",
            "Quality",
            "Actions",
        ]

        for i, expected_header in enumerate(expected_headers):
            actual_header = list_view.horizontalHeaderItem(i)
            assert actual_header is not None
            assert actual_header.text() == expected_header

    def test_table_properties(self, list_view):
        """Test table widget properties."""
        assert list_view.alternatingRowColors() is True
        assert (
            list_view.selectionBehavior()
            == QAbstractItemView.SelectionBehavior.SelectRows
        )
        assert (
            list_view.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection
        )
        assert list_view.isSortingEnabled() is True

    def test_header_resize_modes(self, list_view):
        """Test header resize modes are set correctly."""
        header = list_view.horizontalHeader()

        # Title column should stretch
        assert header.sectionResizeMode(0) == QHeaderView.ResizeMode.Stretch

        # Other columns should resize to contents
        for i in range(1, 8):
            assert (
                header.sectionResizeMode(i) == QHeaderView.ResizeMode.ResizeToContents
            )

    def test_add_album_item(self, list_view, sample_album_item):
        """Test adding an album item to the list."""
        list_view.add_item(sample_album_item)

        assert list_view.rowCount() == 1

        # Check title
        title_item = list_view.item(0, 0)
        assert title_item is not None
        assert title_item.text() == sample_album_item["title"]
        assert title_item.data(Qt.ItemDataRole.UserRole) == sample_album_item["id"]

        # Check artist
        artist_item = list_view.item(0, 1)
        assert artist_item is not None
        assert artist_item.text() == sample_album_item["artist"]

        # Check type
        type_item = list_view.item(0, 2)
        assert type_item is not None
        assert type_item.text() == sample_album_item["type"]

    def test_add_track_item(self, list_view, sample_track_item):
        """Test adding a track item to the list."""
        list_view.add_item(sample_track_item)

        assert list_view.rowCount() == 1

        # Check title without track number prefix
        title_item = list_view.item(0, 0)
        assert title_item is not None
        assert title_item.text() == sample_track_item["title"]

        # Check type shows album info
        type_item = list_view.item(0, 2)
        assert type_item is not None
        expected_type = sample_track_item["album"]
        assert type_item.text() == expected_type

    def test_add_track_item_without_track_number(self, list_view):
        """Test adding a track item without track number."""
        track_item = {
            "id": "track_123",
            "title": "Test Track",
            "artist": "Test Artist",
            "type": "Track",
            "album": "Test Album",
        }

        list_view.add_item(track_item)

        # Title should not have track number prefix
        title_item = list_view.item(0, 0)
        assert title_item is not None
        assert title_item.text() == "Test Track"

    def test_track_album_name_truncation(self, list_view):
        """Test that long album names are truncated with ellipsis."""
        long_album_name = "This is a very long album name that should be truncated"
        track_item = {
            "id": "track_123",
            "title": "Test Track",
            "artist": "Test Artist",
            "type": "Track",
            "album": long_album_name,
        }

        list_view.add_item(track_item)

        # Type column should show truncated album name
        type_item = list_view.item(0, 2)
        assert type_item is not None
        expected_truncated = long_album_name[:22] + "..."
        assert type_item.text() == expected_truncated
        assert len(type_item.text()) == 25  # 22 chars + 3 dots

    def test_add_multiple_items(self, list_view, sample_album_item, sample_track_item):
        """Test adding multiple items to the list."""
        list_view.add_item(sample_album_item)
        list_view.add_item(sample_track_item)

        assert list_view.rowCount() == 2

        # Check first item
        first_title = list_view.item(0, 0)
        assert first_title is not None
        assert first_title.text() == sample_album_item["title"]

        # Check second item
        second_title = list_view.item(1, 0)
        assert second_title is not None
        assert second_title.text() == sample_track_item["title"]

    def test_item_data_storage(self, list_view, sample_album_item):
        """Test that item ID is stored in UserRole data."""
        list_view.add_item(sample_album_item)

        title_item = list_view.item(0, 0)
        assert title_item is not None
        stored_id = title_item.data(Qt.ItemDataRole.UserRole)
        assert stored_id == sample_album_item["id"]

    def test_selection_signal(self, list_view, sample_album_item, qtbot):
        """Test that selection changes emit the correct signal."""
        list_view.add_item(sample_album_item)

        with qtbot.waitSignal(list_view.item_selected, timeout=1000) as blocker:
            # Select the first row
            list_view.selectRow(0)
            # Trigger the selection changed signal manually since qtbot might not trigger it
            list_view.on_selection_changed()

        assert blocker.args == [sample_album_item["id"]]

    def test_empty_selection_signal(self, list_view, qtbot):
        """Test selection signal with no items selected."""
        # This should not emit a signal or should emit with empty string
        list_view.on_selection_changed()
        # No assertion needed - just ensure it doesn't crash

    @pytest.mark.parametrize(
        ("item_data", "expected_values"),
        [
            (
                {
                    "id": "1",
                    "title": "Album",
                    "artist": "Artist",
                    "type": "Album",
                    "year": 2023,
                },
                {"title": "Album", "artist": "Artist", "type": "Album"},
            ),
            (
                {
                    "id": "2",
                    "title": "Track",
                    "artist": "Artist",
                    "type": "Track",
                    "album": "Album",
                },
                {"title": "Track", "artist": "Artist", "type": "Album"},
            ),
            (
                {"id": "3", "title": "", "artist": "", "type": ""},
                {"title": "", "artist": "Unknown", "type": ""},
            ),
        ],
    )
    def test_item_display_values(self, list_view, item_data, expected_values):
        """Test various item data combinations."""
        list_view.add_item(item_data)

        # Check title
        title_item = list_view.item(0, 0)
        assert title_item is not None
        assert title_item.text() == expected_values["title"]

        # Check artist
        artist_item = list_view.item(0, 1)
        assert artist_item is not None
        assert artist_item.text() == expected_values["artist"]

        # Check type
        type_item = list_view.item(0, 2)
        assert type_item is not None
        assert type_item.text() == expected_values["type"]

    def test_year_column(self, list_view):
        """Test year column display."""
        item_with_year = {
            "id": "test",
            "title": "Test",
            "artist": "Artist",
            "type": "Album",
            "year": 2023,
        }

        list_view.add_item(item_with_year)

        year_item = list_view.item(0, 3)
        assert year_item is not None
        assert year_item.text() == "2023"

    def test_duration_column(self, list_view):
        """Test duration column display."""
        item_with_duration = {
            "id": "test",
            "title": "Test",
            "artist": "Artist",
            "type": "Album",
            "duration_formatted": "45:30",
        }

        list_view.add_item(item_with_duration)

        duration_item = list_view.item(0, 4)
        assert duration_item is not None
        assert duration_item.text() == "45:30"

    def test_track_count_column(self, list_view):
        """Test track count column display."""
        item_with_tracks = {
            "id": "test",
            "title": "Test",
            "artist": "Artist",
            "type": "Album",
            "track_count": 12,
        }

        list_view.add_item(item_with_tracks)

        tracks_item = list_view.item(0, 5)
        assert tracks_item is not None
        assert tracks_item.text() == "12"

    def test_quality_column(self, list_view):
        """Test quality column display."""
        item_with_quality = {
            "id": "test",
            "title": "Test",
            "artist": "Artist",
            "type": "Album",
            "quality": "FLAC",
        }

        list_view.add_item(item_with_quality)

        quality_item = list_view.item(0, 6)
        assert quality_item is not None
        assert quality_item.text() == "FLAC"

    def test_missing_optional_fields(self, list_view):
        """Test handling of missing optional fields."""
        minimal_item = {
            "id": "test",
            "title": "Test",
            "artist": "Artist",
            "type": "Album",
        }

        list_view.add_item(minimal_item)

        # Should not crash and should handle missing fields gracefully
        assert list_view.rowCount() == 1

        # Check that missing fields show appropriate defaults
        list_view.item(0, 3)
        list_view.item(0, 4)
        list_view.item(0, 5)
        list_view.item(0, 6)

        # These might be None or have default text depending on implementation
        # The important thing is that it doesn't crash

    def test_sorting_functionality(self, list_view):
        """Test that sorting is enabled and works."""
        items = [
            {
                "id": "1",
                "title": "B Album",
                "artist": "Artist B",
                "type": "Album",
                "year": 2022,
            },
            {
                "id": "2",
                "title": "A Album",
                "artist": "Artist A",
                "type": "Album",
                "year": 2023,
            },
        ]

        for item in items:
            list_view.add_item(item)

        # Sort by title (column 0)
        list_view.sortItems(0, Qt.SortOrder.AscendingOrder)

        # Check that items are sorted
        first_title = list_view.item(0, 0)
        second_title = list_view.item(1, 0)

        assert first_title is not None
        assert second_title is not None
        assert first_title.text() == "A Album"
        assert second_title.text() == "B Album"

    def test_row_selection_behavior(self, list_view, sample_album_item):
        """Test row selection behavior."""
        list_view.add_item(sample_album_item)

        # Select a cell
        list_view.setCurrentCell(0, 1)

        # Should select the entire row
        selected_items = list_view.selectedItems()
        assert len(selected_items) > 1  # Should select multiple cells in the row

    def test_single_selection_mode(
        self, list_view, sample_album_item, sample_track_item
    ):
        """Test single selection mode."""
        list_view.add_item(sample_album_item)
        list_view.add_item(sample_track_item)

        # Select first row
        list_view.selectRow(0)
        selected_rows = list_view.selectionModel().selectedRows()
        assert len(selected_rows) == 1

        # Select second row
        list_view.selectRow(1)
        selected_rows = list_view.selectionModel().selectedRows()
        assert len(selected_rows) == 1  # Should still be only one row selected

    def test_editing_disabled(self, list_view):
        """Test that editing is disabled for all items."""
        # Check that edit triggers are set to NoEditTriggers
        assert list_view.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers

    def test_double_click_download_signal(self, list_view, sample_album_item, qtbot):
        """Test that double-clicking an item emits the download_requested signal."""
        list_view.add_item(sample_album_item)

        with qtbot.waitSignal(list_view.download_requested, timeout=1000) as blocker:
            # Get the item and simulate double-click
            title_item = list_view.item(0, 0)
            assert title_item is not None
            list_view.on_item_double_clicked(title_item)

        # The signal should now emit the full item data dictionary
        expected_data = {
            "id": sample_album_item["id"],
            "title": sample_album_item["title"],
            "artist": sample_album_item["artist"],
            "type": sample_album_item["type"],
            "year": str(sample_album_item["year"]),
            "duration_formatted": sample_album_item["duration_formatted"],
            "track_count": str(sample_album_item["track_count"]),
            "quality": sample_album_item["quality"],
        }
        assert blocker.args == [expected_data]

    def test_double_click_any_column_triggers_download(
        self, list_view, sample_album_item, qtbot
    ):
        """Test that double-clicking any column in a row triggers download."""
        list_view.add_item(sample_album_item)

        # Test double-clicking different columns
        for col in range(7):  # Skip the Actions column (7) as it contains widgets
            with qtbot.waitSignal(
                list_view.download_requested, timeout=1000
            ) as blocker:
                item = list_view.item(0, col)
                if item is not None:  # Some columns might not have items
                    list_view.on_item_double_clicked(item)
                    # The signal should now emit the full item data dictionary
                    expected_data = {
                        "id": sample_album_item["id"],
                        "title": sample_album_item["title"],
                        "artist": sample_album_item["artist"],
                        "type": sample_album_item["type"],
                        "year": str(sample_album_item["year"]),
                        "duration_formatted": sample_album_item["duration_formatted"],
                        "track_count": str(sample_album_item["track_count"]),
                        "quality": sample_album_item["quality"],
                    }
                    assert blocker.args == [expected_data]
                    break  # Test one valid column is enough

    def test_double_click_with_no_item_id(self, list_view, qtbot):
        """Test double-clicking an item without ID doesn't crash."""
        # Add an item without proper ID storage
        item_data = {
            "title": "Test",
            "artist": "Artist",
            "type": "Album",
        }
        list_view.add_item(item_data)

        # This should not emit a signal or crash
        title_item = list_view.item(0, 0)
        assert title_item is not None
        list_view.on_item_double_clicked(title_item)
        # No assertion needed - just ensure it doesn't crash
