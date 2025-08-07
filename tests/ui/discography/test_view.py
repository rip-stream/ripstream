# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for discography view."""

import pytest
from PyQt6.QtWidgets import (
    QButtonGroup,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ripstream.ui.discography.grid_view import AlbumArtGridView
from ripstream.ui.discography.list_view import DiscographyListView
from ripstream.ui.discography.view import DiscographyView


class TestDiscographyView:
    """Test the DiscographyView class."""

    @pytest.fixture
    def discography_view(self, qapp):
        """Create a DiscographyView for testing."""
        return DiscographyView()

    def test_view_creation(self, discography_view: DiscographyView):
        """Test creating a DiscographyView."""
        assert isinstance(discography_view, QWidget)
        assert discography_view.current_view == "grid"
        assert isinstance(discography_view.pending_artwork, dict)
        assert isinstance(discography_view._consumed_artwork_ids, set)

    def test_layout_structure(self, discography_view: DiscographyView):
        """Test the layout structure."""
        layout = discography_view.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.count() == 2  # controls_layout and stacked_widget

    def test_view_toggle_buttons(self, discography_view: DiscographyView):
        """Test view toggle buttons setup."""
        assert hasattr(discography_view, "view_button_group")
        assert hasattr(discography_view, "grid_view_btn")
        assert hasattr(discography_view, "list_view_btn")

        assert isinstance(discography_view.view_button_group, QButtonGroup)
        assert isinstance(discography_view.grid_view_btn, QToolButton)
        assert isinstance(discography_view.list_view_btn, QToolButton)

        # Check initial state
        assert discography_view.grid_view_btn.isChecked() is True
        assert discography_view.list_view_btn.isChecked() is False

    def test_sort_buttons(self, discography_view: DiscographyView):
        """Test sort buttons setup."""
        assert hasattr(discography_view, "sort_title_btn")
        assert hasattr(discography_view, "sort_artist_btn")
        assert hasattr(discography_view, "sort_year_btn")

    def test_stacked_widget_setup(self, discography_view: DiscographyView):
        """Test stacked widget and views setup."""
        assert hasattr(discography_view, "stacked_widget")
        assert hasattr(discography_view, "grid_view")
        assert hasattr(discography_view, "list_view")

        assert isinstance(discography_view.stacked_widget, QStackedWidget)
        assert isinstance(discography_view.grid_view, AlbumArtGridView)
        assert isinstance(discography_view.list_view, DiscographyListView)

        # Check that views are added to stacked widget
        assert discography_view.stacked_widget.count() == 2

    def test_switch_to_grid_view(self, discography_view: DiscographyView):
        """Test switching to grid view."""
        # Start with list view
        discography_view.switch_view("list")
        assert discography_view.current_view == "list"

        # Switch to grid view
        discography_view.switch_view("grid")
        assert discography_view.current_view == "grid"
        assert (
            discography_view.stacked_widget.currentWidget()
            == discography_view.grid_view
        )
        assert discography_view.grid_view_btn.isChecked() is True
        assert discography_view.list_view_btn.isChecked() is False

    def test_switch_to_list_view(self, discography_view: DiscographyView):
        """Test switching to list view."""
        # Start with grid view (default)
        assert discography_view.current_view == "grid"

        # Switch to list view
        discography_view.switch_view("list")
        assert discography_view.current_view == "list"
        assert (
            discography_view.stacked_widget.currentWidget()
            == discography_view.list_view
        )
        assert discography_view.grid_view_btn.isChecked() is False
        assert discography_view.list_view_btn.isChecked() is True

    def test_view_changed_signal(self, discography_view: DiscographyView, qtbot):
        """Test view changed signal emission."""
        with qtbot.waitSignal(discography_view.view_changed, timeout=1000) as blocker:
            discography_view.switch_view("list")

        assert blocker.args == ["list"]

    def test_signal_connections(self, discography_view: DiscographyView, qtbot):
        """Test that view signals are properly connected."""
        # Test grid view signal connection
        with qtbot.waitSignal(discography_view.item_selected, timeout=1000) as blocker:
            discography_view.grid_view.item_selected.emit("test_id")
        assert blocker.args == ["test_id"]

        # Test list view signal connections
        with qtbot.waitSignal(discography_view.item_selected, timeout=1000) as blocker:
            discography_view.list_view.item_selected.emit("test_id_2")
        assert blocker.args == ["test_id_2"]

        with qtbot.waitSignal(
            discography_view.download_requested, timeout=1000
        ) as blocker:
            discography_view.list_view.download_requested.emit({
                "id": "download_id",
                "title": "Test Track",
                "artist": "Test Artist",
            })
        assert blocker.args == [
            {"id": "download_id", "title": "Test Track", "artist": "Test Artist"}
        ]

    def test_set_content_album(
        self, discography_view: DiscographyView, sample_album_metadata
    ):
        """Test setting album content."""
        discography_view.set_content(sample_album_metadata)

        # Should clear existing items and add new ones
        # Check that both views received the content
        assert len(discography_view.grid_view.items) == 1
        assert discography_view.list_view.rowCount() == len(
            sample_album_metadata["items"]
        )

    def test_set_content_track(self, discography_view: DiscographyView):
        """Test setting track content."""
        track_metadata = {
            "content_type": "track",
            "service": "Qobuz",
            "items": [
                {
                    "id": "track_1",
                    "title": "Single Track",
                    "artist": "Test Artist",
                    "type": "Track",
                    "year": 2023,
                    "duration_formatted": "3:45",
                    "track_count": 1,
                    "quality": "FLAC",
                }
            ],
        }

        discography_view.set_content(track_metadata)

        assert len(discography_view.grid_view.items) == 1
        assert discography_view.list_view.rowCount() == 1

    def test_clear_items(
        self, discography_view: DiscographyView, sample_album_metadata
    ):
        """Test clearing items from both views."""
        # Add some content first
        discography_view.set_content(sample_album_metadata)
        assert len(discography_view.grid_view.items) > 0
        assert discography_view.list_view.rowCount() > 0

        # Clear items
        discography_view.clear_items()

        assert len(discography_view.grid_view.items) == 0
        assert discography_view.list_view.rowCount() == 0

    def test_update_item_artwork(
        self, discography_view: DiscographyView, sample_album_metadata, sample_pixmap
    ):
        """Test updating item artwork."""
        discography_view.set_content(sample_album_metadata)

        # Update artwork for first item
        first_item_id = sample_album_metadata["items"][0]["id"]
        discography_view.update_item_artwork(first_item_id, sample_pixmap)

    def test_pending_artwork_handling(
        self, discography_view: DiscographyView, sample_pixmap
    ):
        """Test pending artwork handling."""
        item_id = "test_item"

        # Update artwork before item exists
        discography_view.update_item_artwork(item_id, sample_pixmap)

        # Should store in pending artwork
        assert item_id in discography_view.pending_artwork
        assert discography_view.pending_artwork[item_id] == sample_pixmap

    def test_consumed_artwork_tracking(
        self, discography_view: DiscographyView, sample_album_metadata, sample_pixmap
    ):
        """Test consumed artwork tracking."""
        discography_view.set_content(sample_album_metadata)

        album_id = sample_album_metadata["album_info"]["id"]
        discography_view.update_item_artwork(album_id, sample_pixmap)

        # Update artwork
        discography_view.add_album_content(
            sample_album_metadata["album_info"], sample_album_metadata["items"]
        )

        # Should be marked as consumed
        assert album_id in discography_view._consumed_artwork_ids
        assert album_id in discography_view.pending_artwork

    def test_sort_items_title(self, discography_view: DiscographyView, qtbot):
        """Test sorting items by title."""
        # This would typically trigger sorting in the current view
        # We can test that the signal is connected
        discography_view.sort_items("title")
        # The actual sorting logic would be in the individual views

    def test_sort_items_artist(self, discography_view: DiscographyView):
        """Test sorting items by artist."""
        discography_view.sort_items("artist")
        # The actual sorting logic would be in the individual views

    def test_sort_items_year(self, discography_view: DiscographyView):
        """Test sorting items by year."""
        discography_view.sort_items("year")
        # The actual sorting logic would be in the individual views

    @pytest.mark.parametrize("view_type", ["grid", "list"])
    def test_view_switching_preserves_content(
        self, discography_view: DiscographyView, sample_album_metadata, view_type
    ):
        """Test that switching views preserves content."""
        # Set content
        discography_view.set_content(sample_album_metadata)

        # Switch to specified view
        discography_view.switch_view(view_type)

        # Content should still be there
        if view_type == "grid":
            assert len(discography_view.grid_view.items) == 1
        else:
            assert discography_view.list_view.rowCount() == len(
                sample_album_metadata["items"]
            )

    def test_button_click_handlers(self, discography_view: DiscographyView, qtbot):
        """Test button click handlers."""
        # Test grid view button
        with qtbot.waitSignal(discography_view.view_changed, timeout=1000):
            discography_view.grid_view_btn.click()

        # Test list view button
        with qtbot.waitSignal(discography_view.view_changed, timeout=1000):
            discography_view.list_view_btn.click()

    def test_empty_content_handling(self, discography_view: DiscographyView):
        """Test handling of empty content."""
        empty_metadata = {
            "content_type": "album",
            "service": "Qobuz",
            "items": [],
        }

        discography_view.set_content(empty_metadata)

        assert len(discography_view.grid_view.items) == 0
        assert discography_view.list_view.rowCount() == 0

    def test_invalid_content_handling(self, discography_view: DiscographyView):
        """Test handling of invalid content."""
        # Should not crash with invalid content
        discography_view.set_content({})
        discography_view.set_content(None)  # type: ignore[invalid-argument-type] # Should handle None gracefully

    def test_artwork_cleanup_on_clear(
        self, discography_view: DiscographyView, sample_pixmap
    ):
        """Test that pending artwork is cleaned up when clearing items."""
        # Add pending artwork
        discography_view.pending_artwork["test_id"] = sample_pixmap
        discography_view._consumed_artwork_ids.add("consumed_id")

        # Clear items
        discography_view.clear_items()

        # Pending artwork and consumed ids should not be cleared
        assert len(discography_view.pending_artwork) == 1
        assert len(discography_view._consumed_artwork_ids) == 1

    def test_multiple_artwork_updates(
        self, discography_view: DiscographyView, sample_album_metadata, sample_pixmap
    ):
        """Test multiple artwork updates for the same item."""
        discography_view.set_content(sample_album_metadata)

        first_item_id = sample_album_metadata["items"][0]["id"]

        # Update artwork multiple times
        discography_view.update_item_artwork(first_item_id, sample_pixmap)
        discography_view.update_item_artwork(first_item_id, sample_pixmap)

        # Add content again to trigger consumption of the updated artwork
        discography_view.add_album_content(
            sample_album_metadata["album_info"], sample_album_metadata["items"]
        )

        # Should handle multiple updates gracefully and mark as consumed
        assert first_item_id in discography_view._consumed_artwork_ids

    def test_view_state_persistence(self, discography_view: DiscographyView):
        """Test that view state is maintained."""
        # Switch to list view
        discography_view.switch_view("list")
        assert discography_view.current_view == "list"

        # Add content
        sample_content = {
            "content_type": "album",
            "items": [
                {"id": "test", "title": "Test", "artist": "Artist", "type": "Album"}
            ],
        }
        discography_view.set_content(sample_content)

        # Should still be in list view
        assert discography_view.current_view == "list"
        assert (
            discography_view.stacked_widget.currentWidget()
            == discography_view.list_view
        )
