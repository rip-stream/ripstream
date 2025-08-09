# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Grid view for displaying album artwork."""

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ripstream.ui.discography.album_art_widget import AlbumArtWidget


class AlbumArtGridView(QScrollArea):
    """Grid view for displaying album artwork."""

    item_selected = pyqtSignal(str)  # item_id
    download_requested = pyqtSignal(dict)  # item_details

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.count_label = None
        self._current_downloaded_albums = set()  # Initialize empty set
        self.setup_ui()

    def setup_ui(self):
        """Set up the grid view."""
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Main container widget
        self.container = QWidget()
        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(8)  # Reduced spacing between header and grid

        # Count header
        self.count_label = QLabel("0 Albums")
        self.count_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                margin-bottom: 0px;
            }
        """)
        main_layout.addWidget(self.count_label)

        # Grid container
        grid_container = QWidget()
        self.grid_layout = QGridLayout(grid_container)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        main_layout.addWidget(grid_container)
        main_layout.addStretch()  # Add stretch to push content to top
        self.setWidget(self.container)

    def add_item(self, item_data: dict[str, Any], parent_pending_artwork=None):
        """Add an item to the grid."""
        item_id = item_data.get("id", "")

        art_widget = AlbumArtWidget(item_data)
        art_widget.clicked.connect(self.item_selected.emit)
        art_widget.download_requested.connect(self.download_requested.emit)

        # Calculate grid position
        items_per_row = max(1, self.width() // 200)  # 180 + 20 margin
        row = len(self.items) // items_per_row
        col = len(self.items) % items_per_row

        self.grid_layout.addWidget(art_widget, row, col)
        self.items.append(art_widget)

        # Update count
        self.update_count()

        # Check parent pending artwork
        pending_pixmap = None
        if parent_pending_artwork and item_id in parent_pending_artwork:
            pending_pixmap = parent_pending_artwork[item_id]

        if pending_pixmap:
            art_widget.update_artwork(pending_pixmap)

        # Apply current download status to the new widget
        if hasattr(self, "_current_downloaded_albums"):
            art_widget.update_download_status_from_albums(
                self._current_downloaded_albums
            )

    def sort_items(self, sort_by: str, descending: bool = False):
        """Sort grid items in-place and refresh layout.

        Supported sort keys: "title", "artist", "year" (ascending).
        """
        if not self.items:
            return

        def normalize_text(value: Any) -> str:
            if value is None:
                return ""
            return str(value).lower()

        def normalize_year(value: Any) -> int:
            try:
                # Some sources provide year as str or may be empty/"-"
                if value in (None, "", "-"):
                    return 0
                return int(value)
            except (ValueError, TypeError):
                return 0

        def item_key(widget: AlbumArtWidget):  # type: ignore[name-defined]
            data = getattr(widget, "item_data", {}) or {}
            if sort_by == "artist":
                return (
                    normalize_text(data.get("artist", "")),
                    normalize_text(data.get("title", "")),
                )
            if sort_by == "year":
                return (
                    normalize_year(data.get("year")),
                    normalize_text(data.get("title", "")),
                )
            # Default to title
            return (
                normalize_text(data.get("title", "")),
                normalize_text(data.get("artist", "")),
            )

        # Reorder widgets and refresh positions
        self.items.sort(key=item_key, reverse=descending)
        self.update_grid_layout()

    def update_item_artwork(self, item_id: str, pixmap: QPixmap):
        """Update artwork for a specific item."""
        # Try to find and update the item immediately
        for item in self.items:
            if hasattr(item, "item_id") and item.item_id == item_id:
                item.update_artwork(pixmap)
                return

        # If item not found, the parent DiscographyView will handle pending artwork

    def clear_items(self):
        """Clear all items from the grid."""
        for item in self.items:
            item.deleteLater()
        self.items.clear()

        # Clear layout
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child and child.widget():
                widget = child.widget()
                if widget:
                    widget.deleteLater()

        # Update count
        self.update_count()

    def resizeEvent(self, a0):  # noqa: N802
        """Handle resize events to adjust grid layout."""
        super().resizeEvent(a0)
        self.update_grid_layout()

    def update_grid_layout(self):
        """Update the grid layout based on current width."""
        if not self.items:
            return

        items_per_row = max(1, self.width() // 200)

        # Rearrange items
        for i, item in enumerate(self.items):
            row = i // items_per_row
            col = i % items_per_row
            self.grid_layout.addWidget(item, row, col)

    def update_count(self):
        """Update the count label."""
        if self.count_label:
            count = len(self.items)
            if count == 1:
                self.count_label.setText("1 Album")
            else:
                self.count_label.setText(f"{count} Albums")

    def update_download_statuses(self, downloaded_albums: set):
        """Update download statuses for all album art widgets.

        Args:
            downloaded_albums: Set of (album_id, source) tuples for downloaded albums
        """
        # Store current downloaded albums for new widgets
        self._current_downloaded_albums = downloaded_albums

        for item in self.items:
            if isinstance(item, AlbumArtWidget):
                item.update_download_status_from_albums(downloaded_albums)

    def update_active_statuses(
        self, downloading_album_ids: set[str], pending_album_ids: set[str]
    ) -> None:
        """Update active statuses (downloading/pending) for all items."""
        for item in self.items:
            if not isinstance(item, AlbumArtWidget):
                continue
            album_id = getattr(item, "item_id", "")
            if not album_id:
                continue
            if album_id in downloading_album_ids:
                item.set_downloading_status()
            elif album_id in pending_album_ids and item.get_status() != "downloaded":
                item.set_queued_status()
            elif item.get_status() in {"queued", "downloading"}:
                item.set_idle_status()
