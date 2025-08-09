# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for album art widget."""

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout

from ripstream.ui.discography.album_art_widget import AlbumArtWidget


class TestAlbumArtWidget:
    """Test the AlbumArtWidget class."""

    @pytest.fixture
    def widget(self, qapp, sample_album_item):
        """Create an AlbumArtWidget for testing."""
        return AlbumArtWidget(sample_album_item)

    def test_widget_creation(self, widget, sample_album_item):
        """Test creating an AlbumArtWidget."""
        assert widget.item_data == sample_album_item
        assert widget.item_id == sample_album_item["id"]
        assert widget.art_label is not None
        assert isinstance(widget.art_label, QLabel)

    def test_widget_size(self, widget):
        """Test widget has correct fixed size."""
        assert widget.size().width() == 180
        assert widget.size().height() == 260

    def test_widget_layout(self, widget):
        """Test widget has correct layout structure."""
        layout = widget.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.count() == 2  # art_container, text_container

    def test_art_label_properties(self, widget):
        """Test art label has correct properties."""
        art_label = widget.art_label
        assert art_label.size().width() == 180
        assert art_label.size().height() == 180
        assert art_label.alignment() == Qt.AlignmentFlag.AlignCenter

    def test_initial_artwork_placeholder(self, widget, sample_album_item):
        """Test initial placeholder artwork is created."""
        pixmap = widget.art_label.pixmap()
        assert pixmap is not None
        assert not pixmap.isNull()
        assert pixmap.size().width() == 180
        assert pixmap.size().height() == 180

    def test_update_artwork(self, widget, sample_pixmap):
        """Test updating artwork with new pixmap."""
        widget.art_label.pixmap()
        widget.update_artwork(sample_pixmap)

        new_pixmap = widget.art_label.pixmap()
        assert new_pixmap is not None
        assert not new_pixmap.isNull()
        # Should be scaled to fit the label
        assert new_pixmap.size().width() <= 180
        assert new_pixmap.size().height() <= 180

    def test_update_artwork_with_null_pixmap(self, widget):
        """Test updating artwork with null pixmap doesn't change anything."""
        original_pixmap = widget.art_label.pixmap()
        original_size = original_pixmap.size() if original_pixmap else None
        null_pixmap = QPixmap()  # Null pixmap

        widget.update_artwork(null_pixmap)

        # Should remain unchanged - compare size since pixmap objects are different instances
        current_pixmap = widget.art_label.pixmap()
        current_size = current_pixmap.size() if current_pixmap else None
        assert current_size == original_size

    def test_mouse_click_emits_signal(self, widget, qtbot):
        """Test mouse click emits clicked signal."""
        with qtbot.waitSignal(widget.clicked, timeout=1000) as blocker:
            qtbot.mouseClick(widget, Qt.MouseButton.LeftButton)

        assert blocker.args == [widget.item_id]

    @pytest.mark.parametrize(
        ("item_data", "expected_title", "expected_artist"),
        [
            (
                {"id": "1", "title": "Album Title", "artist": "Artist Name"},
                "Album Title",
                "Artist Name",
            ),
            ({"id": "2", "title": "", "artist": ""}, "Unknown Title", "Unknown Artist"),
            ({"id": "3"}, "Unknown Title", "Unknown Artist"),
        ],
    )
    def test_title_and_artist_labels(
        self, qapp, item_data, expected_title, expected_artist
    ):
        """Test title and artist labels are created correctly."""
        widget = AlbumArtWidget(item_data)
        layout = widget.layout()

        assert layout is not None
        assert isinstance(layout, QVBoxLayout)

        # Get the text container (index 1) and its layout
        text_container_item = layout.itemAt(1)
        assert text_container_item is not None

        text_container = text_container_item.widget()
        assert text_container is not None

        text_layout = text_container.layout()
        assert text_layout is not None
        assert isinstance(text_layout, QVBoxLayout)

        # Get the title and artist labels from text container
        title_item = text_layout.itemAt(0)
        artist_item = text_layout.itemAt(1)

        assert title_item is not None
        assert artist_item is not None

        title_label = title_item.widget()
        artist_label = artist_item.widget()

        assert isinstance(title_label, QLabel)
        assert isinstance(artist_label, QLabel)

        # Handle year in title
        expected_title_with_year = expected_title
        if item_data.get("year"):
            expected_title_with_year = f"{expected_title} ({item_data['year']})"

        assert title_label.text() == expected_title_with_year
        assert artist_label.text() == expected_artist

    def test_placeholder_artwork_generation(self, qapp):
        """Test placeholder artwork generation with different titles."""
        test_cases = [
            {"id": "1", "title": "Album", "artist": "Artist"},
            {"id": "2", "title": "Test", "artist": "Artist"},
            {"id": "3", "title": "", "artist": "Artist"},
            {"id": "4", "title": "123", "artist": "Artist"},
        ]

        for item_data in test_cases:
            widget = AlbumArtWidget(item_data)
            assert widget.art_label is not None
            pixmap = widget.art_label.pixmap()

            assert pixmap is not None
            assert not pixmap.isNull()
            assert pixmap.size().width() == 180
            assert pixmap.size().height() == 180

    def test_widget_styling(self, widget):
        """Test widget has correct styling applied."""
        style_sheet = widget.styleSheet()
        assert "background-color:" in style_sheet

    def test_art_label_styling(self, widget):
        """Test art label has correct styling applied."""
        art_label = widget.art_label
        style_sheet = art_label.styleSheet()
        assert "border:" in style_sheet
        assert "background-color:" in style_sheet

    def test_widget_with_large_pixmap(self, widget):
        """Test widget handles large pixmaps correctly."""
        # Create a large pixmap
        large_pixmap = QPixmap(1000, 1000)
        large_pixmap.fill(QColor("red"))

        widget.update_artwork(large_pixmap)

        # Should be scaled down to fit
        result_pixmap = widget.art_label.pixmap()
        assert result_pixmap.size().width() <= 180
        assert result_pixmap.size().height() <= 180

    def test_widget_with_small_pixmap(self, widget):
        """Test widget handles small pixmaps correctly."""
        # Create a small pixmap
        small_pixmap = QPixmap(50, 50)
        small_pixmap.fill(QColor("green"))

        widget.update_artwork(small_pixmap)

        # Should maintain aspect ratio and not exceed label size
        result_pixmap = widget.art_label.pixmap()
        assert result_pixmap.size().width() <= 180
        assert result_pixmap.size().height() <= 180

    def test_widget_accessibility(self, widget):
        """Test widget accessibility properties."""
        # Check that labels have proper text for screen readers
        layout = widget.layout()
        assert layout is not None

        # Get the text container (index 1) and its layout
        text_container_item = layout.itemAt(1)
        assert text_container_item is not None

        text_container = text_container_item.widget()
        assert text_container is not None

        text_layout = text_container.layout()
        assert text_layout is not None

        title_item = text_layout.itemAt(0)
        artist_item = text_layout.itemAt(1)

        assert title_item is not None
        assert artist_item is not None

        title_label = title_item.widget()
        artist_label = artist_item.widget()

        assert isinstance(title_label, QLabel)
        assert isinstance(artist_label, QLabel)
        assert title_label.text() != ""
        assert artist_label.text() != ""

    def test_download_button_initial_idle_state(self, widget: AlbumArtWidget):
        """Download button should start in idle (enabled, download icon, tooltip)."""
        btn = widget.download_btn
        assert btn.isEnabled() is True
        assert "Download" in btn.toolTip()

    def test_set_queued_status_updates_button(self, widget: AlbumArtWidget):
        """Queued state disables the button and sets queued styling."""
        widget.set_queued_status()
        btn = widget.download_btn
        assert btn.isEnabled() is False
        assert "Queued" in btn.toolTip()
        assert widget.get_status() == "queued"

    def test_set_downloading_status_updates_button(self, widget: AlbumArtWidget):
        """Downloading state disables the button and sets downloading styling."""
        widget.set_downloading_status()
        btn = widget.download_btn
        assert btn.isEnabled() is False
        assert "Downloading" in btn.toolTip()
        assert widget.get_status() == "downloading"

    def test_set_downloaded_status_true(self, widget: AlbumArtWidget):
        """Downloaded state sets check icon, disables clicks, and tooltip."""
        widget.set_downloaded_status(True)
        btn = widget.download_btn
        assert btn.isEnabled() is True  # remains enabled for hover but click is no-op
        assert "Already downloaded" in btn.toolTip()
        assert widget.get_status() == "downloaded"

    def test_set_downloaded_status_false_does_not_reset(self, widget: AlbumArtWidget):
        """Calling with False should not reset an existing non-idle state."""
        widget.set_queued_status()
        widget.set_downloaded_status(False)
        assert widget.get_status() == "queued"

    def test_title_tooltip_only_when_truncated(self, qapp):
        """Tooltip on widget should be set only when title is truncated."""
        # Short title (no truncation)
        w1 = AlbumArtWidget({"id": "a1", "title": "Short", "artist": "A"})
        assert w1.toolTip() in (None, "")

        # Long title (truncation expected)
        long_title = "This is a very very long album title that will be cut"
        w2 = AlbumArtWidget({
            "id": "a2",
            "title": long_title,
            "artist": "A",
            "year": 2024,
            "hires": True,
        })
        assert w2.toolTip() is not None
        assert long_title.split()[0] in w2.toolTip()

    def test_load_artwork_method(self, qapp):
        """Test the load_artwork method creates proper placeholder."""
        item_data = {"id": "test", "title": "Test Album", "artist": "Test Artist"}
        widget = AlbumArtWidget(item_data)

        # The load_artwork method should have been called during initialization
        assert widget.art_label is not None
        pixmap = widget.art_label.pixmap()
        assert pixmap is not None
        assert not pixmap.isNull()

        # Should contain the first letter of the title
        # We can't easily test the actual content, but we can verify it's not empty
        assert pixmap.size().width() == 180
        assert pixmap.size().height() == 180
