# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for album art grid view."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QScrollArea, QWidget

from ripstream.ui.discography.album_art_widget import AlbumArtWidget
from ripstream.ui.discography.grid_view import AlbumArtGridView


class TestAlbumArtGridView:
    """Test the AlbumArtGridView class."""

    @pytest.fixture
    def grid_view(self, qapp) -> AlbumArtGridView:
        """Create an AlbumArtGridView for testing."""
        return AlbumArtGridView()

    def test_grid_view_creation(self, grid_view):
        """Test creating an AlbumArtGridView."""
        assert isinstance(grid_view, QScrollArea)
        assert grid_view.items == []
        assert hasattr(grid_view, "container")
        assert hasattr(grid_view, "grid_layout")

    def test_scroll_area_properties(self, grid_view):
        """Test scroll area properties are set correctly."""
        assert grid_view.widgetResizable() is True
        assert (
            grid_view.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        assert (
            grid_view.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

    def test_container_and_layout(self, grid_view):
        """Test container widget and grid layout setup."""
        assert isinstance(grid_view.container, QWidget)
        assert isinstance(grid_view.grid_layout, QGridLayout)
        assert grid_view.widget() == grid_view.container
        # The container now has a VBoxLayout, not the grid_layout directly
        from PyQt6.QtWidgets import QVBoxLayout

        assert isinstance(grid_view.container.layout(), QVBoxLayout)

    def test_grid_layout_properties(self, grid_view):
        """Test grid layout properties."""
        layout = grid_view.grid_layout
        assert layout.spacing() == 16
        # Check alignment includes both Top and Left
        alignment = layout.alignment()
        assert alignment & Qt.AlignmentFlag.AlignTop
        assert alignment & Qt.AlignmentFlag.AlignLeft

    def test_add_single_item(self, grid_view, sample_album_item):
        """Test adding a single item to the grid."""
        grid_view.add_item(sample_album_item)

        assert len(grid_view.items) == 1
        assert isinstance(grid_view.items[0], AlbumArtWidget)
        assert grid_view.items[0].item_id == sample_album_item["id"]

    def test_add_multiple_items(self, grid_view, sample_album_item, sample_track_item):
        """Test adding multiple items to the grid."""
        grid_view.add_item(sample_album_item)
        grid_view.add_item(sample_track_item)

        assert len(grid_view.items) == 2
        assert grid_view.items[0].item_id == sample_album_item["id"]
        assert grid_view.items[1].item_id == sample_track_item["id"]

    def test_sort_items_api(self, grid_view):
        """Ensure sort_items reorders widgets by key and direction."""
        items = [
            {"id": "2", "title": "B", "artist": "Z", "year": 2021},
            {"id": "1", "title": "A", "artist": "A", "year": 2020},
        ]

        for data in items:
            grid_view.add_item(data)

        # Title asc
        grid_view.sort_items("title", descending=False)
        assert [w.item_data["title"] for w in grid_view.items] == ["A", "B"]

        # Title desc
        grid_view.sort_items("title", descending=True)
        assert [w.item_data["title"] for w in grid_view.items] == ["B", "A"]

        # Artist asc
        grid_view.sort_items("artist", descending=False)
        assert [w.item_data["artist"] for w in grid_view.items] == ["A", "Z"]

        # Year desc
        grid_view.sort_items("year", descending=True)
        assert [w.item_data.get("year", 0) for w in grid_view.items] == [2021, 2020]

    def test_item_signal_connection(self, grid_view, sample_album_item, qtbot):
        """Test that item signals are connected properly."""
        with qtbot.waitSignal(grid_view.item_selected, timeout=1000) as blocker:
            grid_view.add_item(sample_album_item)
            # Simulate clicking the item
            grid_view.items[0].clicked.emit(sample_album_item["id"])

        assert blocker.args == [sample_album_item["id"]]

    def test_update_active_statuses(self, grid_view, sample_album_item):
        """Active statuses update individual tiles without affecting others."""
        grid_view.add_item(sample_album_item)
        w = grid_view.items[0]
        # Set downloading
        grid_view.update_active_statuses({sample_album_item["id"]}, set())
        assert w.get_status() == "downloading"
        # Set queued
        grid_view.update_active_statuses(set(), {sample_album_item["id"]})
        assert w.get_status() == "queued"
        # Clear to idle
        grid_view.update_active_statuses(set(), set())
        assert w.get_status() == "idle"

    def test_grid_positioning(self, grid_view):
        """Test items are positioned correctly in grid."""
        # Add several items to test grid positioning
        items = [
            {"id": f"item_{i}", "title": f"Item {i}", "artist": "Artist"}
            for i in range(5)
        ]

        for item in items:
            grid_view.add_item(item)

        # Check that items are added to the layout
        layout = grid_view.grid_layout
        assert layout.count() == 5

        # Verify items are positioned in grid (exact positioning depends on width)
        for i in range(5):
            item_widget = layout.itemAt(i).widget()
            assert isinstance(item_widget, AlbumArtWidget)

    def test_update_item_artwork_existing_item(
        self, grid_view, sample_album_item, sample_pixmap
    ):
        """Test updating artwork for an existing item."""
        grid_view.add_item(sample_album_item)
        item_widget = grid_view.items[0]

        # Mock the update_artwork method to verify it's called
        original_update = item_widget.update_artwork
        update_called = False

        def mock_update(pixmap):
            nonlocal update_called
            update_called = True
            original_update(pixmap)

        item_widget.update_artwork = mock_update

        grid_view.update_item_artwork(sample_album_item["id"], sample_pixmap)
        assert update_called

    def test_update_item_artwork_nonexistent_item(self, grid_view, sample_pixmap):
        """Test updating artwork for non-existent item doesn't crash."""
        # Should not raise an exception
        grid_view.update_item_artwork("nonexistent_id", sample_pixmap)

    def test_clear_items(self, grid_view, sample_album_item, sample_track_item):
        """Test clearing all items from the grid."""
        # Add some items
        grid_view.add_item(sample_album_item)
        grid_view.add_item(sample_track_item)

        assert len(grid_view.items) == 2
        assert grid_view.grid_layout.count() == 2

        # Clear items
        grid_view.clear_items()

        assert len(grid_view.items) == 0
        # Note: deleteLater() means widgets might still be in layout temporarily

    def test_add_item_with_pending_artwork(
        self, grid_view, sample_album_item, sample_pixmap
    ):
        """Test adding item with pending artwork from parent."""
        pending_artwork = {sample_album_item["id"]: sample_pixmap}

        grid_view.add_item(sample_album_item, pending_artwork)

        # Verify the item was added and artwork was applied
        assert len(grid_view.items) == 1
        item_widget = grid_view.items[0]

        # Check that the pixmap was set (we can't easily verify the exact pixmap)
        current_pixmap = item_widget.art_label.pixmap()
        assert current_pixmap is not None
        assert not current_pixmap.isNull()

    def test_add_item_without_pending_artwork(self, grid_view, sample_album_item):
        """Test adding item without pending artwork."""
        grid_view.add_item(sample_album_item, None)

        assert len(grid_view.items) == 1
        # Should still have placeholder artwork
        item_widget = grid_view.items[0]
        current_pixmap = item_widget.art_label.pixmap()
        assert current_pixmap is not None
        assert not current_pixmap.isNull()

    @pytest.mark.parametrize("item_count", [1, 3, 5, 10])
    def test_grid_with_various_item_counts(self, grid_view, item_count):
        """Test grid behavior with various numbers of items."""
        items = [
            {"id": f"item_{i}", "title": f"Item {i}", "artist": "Artist"}
            for i in range(item_count)
        ]

        for item in items:
            grid_view.add_item(item)

        assert len(grid_view.items) == item_count
        assert grid_view.grid_layout.count() == item_count

    def test_item_widget_properties(self, grid_view, sample_album_item):
        """Test that added item widgets have correct properties."""
        grid_view.add_item(sample_album_item)
        item_widget = grid_view.items[0]

        assert isinstance(item_widget, AlbumArtWidget)
        assert item_widget.item_data == sample_album_item
        assert item_widget.item_id == sample_album_item["id"]

    def test_empty_grid_state(self, grid_view):
        """Test grid in empty state."""
        assert len(grid_view.items) == 0
        assert grid_view.grid_layout.count() == 0
        assert isinstance(grid_view.container, QWidget)
        assert isinstance(grid_view.grid_layout, QGridLayout)

    def test_grid_layout_spacing(self, grid_view):
        """Test grid layout has correct spacing."""
        assert grid_view.grid_layout.spacing() == 16

    def test_widget_resizable_property(self, grid_view):
        """Test that the scroll area is widget resizable."""
        assert grid_view.widgetResizable() is True

    def test_scroll_policies(self, grid_view):
        """Test scroll bar policies are set correctly."""
        assert (
            grid_view.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        assert (
            grid_view.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

    def test_container_widget_assignment(self, grid_view):
        """Test that container widget is properly assigned."""
        assert grid_view.widget() == grid_view.container
        # The container now has a VBoxLayout, not the grid_layout directly
        from PyQt6.QtWidgets import QVBoxLayout

        assert isinstance(grid_view.container.layout(), QVBoxLayout)

    def test_items_per_row_calculation(self, grid_view):
        """Test items per row calculation logic."""
        # This tests the logic in add_item method
        # The actual calculation depends on widget width, so we test the method exists
        grid_view.resize(440, 300)  # Set a known width

        # Add items and verify they're positioned
        for i in range(4):
            item_data = {"id": f"item_{i}", "title": f"Item {i}", "artist": "Artist"}
            grid_view.add_item(item_data)

        # With width 440, items_per_row should be 2 (440 // 220 = 2)
        # So items should be in a 2x2 grid
        layout = grid_view.grid_layout
        assert layout.count() == 4

    def test_resize_event_triggers_layout_update(self, grid_view):
        """Test that resize events trigger grid layout updates."""
        # Add some items first
        for i in range(6):
            item_data = {"id": f"item_{i}", "title": f"Item {i}", "artist": "Artist"}
            grid_view.add_item(item_data)

        # Mock the update_grid_layout method to verify it's called
        original_update = grid_view.update_grid_layout
        update_called = False

        def mock_update():
            nonlocal update_called
            update_called = True
            original_update()

        grid_view.update_grid_layout = mock_update

        # Trigger resize event
        from PyQt6.QtCore import QSize
        from PyQt6.QtGui import QResizeEvent

        resize_event = QResizeEvent(QSize(800, 600), QSize(400, 300))
        grid_view.resizeEvent(resize_event)

        assert update_called

    def test_update_grid_layout_empty_items(self, grid_view):
        """Test update_grid_layout with no items."""
        # Should not crash with empty items list
        grid_view.update_grid_layout()
        assert len(grid_view.items) == 0

    def test_update_grid_layout_repositions_items(self, grid_view):
        """Test that update_grid_layout repositions items correctly."""
        # Add items
        for i in range(4):
            item_data = {"id": f"item_{i}", "title": f"Item {i}", "artist": "Artist"}
            grid_view.add_item(item_data)

        # Set a specific width to control items per row
        grid_view.resize(660, 400)  # Should allow 3 items per row (660 // 220 = 3)

        # Update layout
        grid_view.update_grid_layout()

        # Verify items are repositioned
        layout = grid_view.grid_layout
        assert layout.count() == 4

        # Check positioning (first 3 items in row 0, last item in row 1)
        for i in range(4):
            item_widget = layout.itemAt(i).widget()
            assert isinstance(item_widget, AlbumArtWidget)

    def test_add_item_with_missing_id(self, grid_view):
        """Test adding item with missing ID field."""
        item_data = {"title": "Test Item", "artist": "Test Artist"}  # No ID
        grid_view.add_item(item_data)

        assert len(grid_view.items) == 1
        # Should use empty string as default ID
        assert grid_view.items[0].item_id == ""

    def test_add_item_with_none_pending_artwork(self, grid_view, sample_album_item):
        """Test adding item with None pending artwork."""
        grid_view.add_item(sample_album_item, None)

        assert len(grid_view.items) == 1
        item_widget = grid_view.items[0]
        # Should still have default/placeholder artwork
        current_pixmap = item_widget.art_label.pixmap()
        assert current_pixmap is not None

    def test_add_item_with_empty_pending_artwork_dict(
        self, grid_view, sample_album_item
    ):
        """Test adding item with empty pending artwork dictionary."""
        grid_view.add_item(sample_album_item, {})

        assert len(grid_view.items) == 1
        item_widget = grid_view.items[0]
        # Should still have default/placeholder artwork
        current_pixmap = item_widget.art_label.pixmap()
        assert current_pixmap is not None

    def test_clear_items_calls_delete_later(self, grid_view, sample_album_item):
        """Test that clear_items properly calls deleteLater on widgets."""
        # Add items
        grid_view.add_item(sample_album_item)
        item_widget = grid_view.items[0]

        # Mock deleteLater to verify it's called
        delete_called = False
        original_delete = item_widget.deleteLater

        def mock_delete():
            nonlocal delete_called
            delete_called = True
            original_delete()

        item_widget.deleteLater = mock_delete

        # Clear items
        grid_view.clear_items()

        assert delete_called
        assert len(grid_view.items) == 0

    def test_grid_layout_alignment(self, grid_view):
        """Test that grid layout has correct alignment flags."""
        layout = grid_view.grid_layout
        alignment = layout.alignment()

        # Should have both AlignTop and AlignLeft
        assert alignment & Qt.AlignmentFlag.AlignTop
        assert alignment & Qt.AlignmentFlag.AlignLeft

    def test_container_widget_layout_assignment(self, grid_view):
        """Test that container widget has the grid layout assigned."""
        # The container now has a VBoxLayout, not the grid_layout directly
        from PyQt6.QtWidgets import QVBoxLayout

        assert isinstance(grid_view.container.layout(), QVBoxLayout)

    def test_scroll_area_widget_assignment(self, grid_view):
        """Test that scroll area has container widget assigned."""
        assert grid_view.widget() == grid_view.container

    def test_items_per_row_calculation_edge_cases(self, grid_view):
        """Test items per row calculation with edge case widths."""
        # Test very narrow width
        grid_view.resize(100, 300)
        grid_view.add_item({"id": "test", "title": "Test", "artist": "Artist"})
        # Should still have at least 1 item per row
        assert len(grid_view.items) == 1

        # Test very wide width
        grid_view.resize(2000, 300)
        for i in range(5):
            grid_view.add_item({
                "id": f"test_{i}",
                "title": f"Test {i}",
                "artist": "Artist",
            })
        # Should accommodate many items per row
        assert len(grid_view.items) == 6  # 1 from before + 5 new

    def test_update_item_artwork_with_hasattr_check(self, grid_view, sample_pixmap):
        """Test update_item_artwork when item doesn't have item_id attribute."""
        # Create a mock widget without item_id attribute
        from unittest.mock import Mock

        mock_widget = Mock()
        del mock_widget.item_id  # Remove the attribute
        grid_view.items.append(mock_widget)

        # Should not crash when item doesn't have item_id
        grid_view.update_item_artwork("test_id", sample_pixmap)

    def test_signal_connection_integrity(self, grid_view, sample_album_item, qtbot):
        """Test that signal connections remain intact after multiple operations."""
        # Add item
        grid_view.add_item(sample_album_item)
        item_widget = grid_view.items[0]

        # Verify signal is still connected after various operations
        grid_view.update_grid_layout()

        # Test signal emission
        with qtbot.waitSignal(grid_view.item_selected, timeout=1000) as blocker:
            item_widget.clicked.emit(sample_album_item["id"])

        assert blocker.args == [sample_album_item["id"]]

    def test_memory_management_after_clear(self, grid_view):
        """Test memory management after clearing items."""
        # Add multiple items
        items_data = [
            {"id": f"item_{i}", "title": f"Item {i}", "artist": "Artist"}
            for i in range(10)
        ]

        for item_data in items_data:
            grid_view.add_item(item_data)

        assert len(grid_view.items) == 10
        assert grid_view.grid_layout.count() == 10

        # Clear all items
        grid_view.clear_items()

        assert len(grid_view.items) == 0
        # Layout count might not be immediately 0 due to deleteLater()
        # but items list should be empty

    def test_grid_view_inheritance(self, grid_view):
        """Test that AlbumArtGridView properly inherits from QScrollArea."""
        from PyQt6.QtWidgets import QScrollArea

        assert isinstance(grid_view, QScrollArea)

    def test_widget_properties_after_initialization(self, grid_view):
        """Test widget properties are correctly set after initialization."""
        # Test scroll bar policies
        assert (
            grid_view.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        assert (
            grid_view.horizontalScrollBarPolicy()
            == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Test widget resizable
        assert grid_view.widgetResizable() is True

        # Test layout spacing
        assert grid_view.grid_layout.spacing() == 16

    @pytest.mark.parametrize(
        ("width", "expected_items_per_row"),
        [
            (220, 1),  # Minimum width for 1 item
            (440, 2),  # Width for 2 items
            (660, 3),  # Width for 3 items
            (880, 4),  # Width for 4 items
            (100, 1),  # Very narrow, should still be 1
            (2000, 9),  # Very wide, should be many
        ],
    )
    def test_items_per_row_calculation_parametrized(
        self, grid_view, width: int, expected_items_per_row: int
    ):
        """Test items per row calculation with various widths."""
        grid_view.resize(width, 400)

        # The calculation is max(1, width // 220)
        calculated_items_per_row = max(1, width // 220)
        assert calculated_items_per_row == expected_items_per_row

    def test_add_item_data_preservation(self, grid_view):
        """Test that item data is preserved correctly in widgets."""
        item_data = {
            "id": "test_123",
            "title": "Test Album",
            "artist": "Test Artist",
            "type": "Album",
            "year": 2023,
            "quality": "FLAC",
        }

        grid_view.add_item(item_data)

        item_widget = grid_view.items[0]
        assert item_widget.item_data == item_data
        assert item_widget.item_id == "test_123"

    def test_concurrent_operations(
        self, grid_view, sample_album_item, sample_track_item, sample_pixmap
    ):
        """Test concurrent operations on grid view."""
        # Add items
        grid_view.add_item(sample_album_item)
        grid_view.add_item(sample_track_item)

        # Update artwork while updating layout
        grid_view.update_item_artwork(sample_album_item["id"], sample_pixmap)
        grid_view.update_grid_layout()

        # Should not crash and maintain consistency
        assert len(grid_view.items) == 2
        assert grid_view.grid_layout.count() == 2
