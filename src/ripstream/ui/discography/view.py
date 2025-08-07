# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Complete discography view with grid/list toggle."""

from typing import Any

import qtawesome as qta
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ripstream.ui.discography.grid_view import AlbumArtGridView
from ripstream.ui.discography.list_view import DiscographyListView


class DiscographyView(QWidget):
    """Complete discography view with grid/list toggle."""

    item_selected = pyqtSignal(str)  # item_id
    download_requested = pyqtSignal(dict)  # item_details
    view_changed = pyqtSignal(str)  # view_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "grid"
        self.pending_artwork = {}  # Store artwork updates until items are available
        self._consumed_artwork_ids = set()  # Track which artwork has been consumed
        self.downloaded_albums = set()  # Store downloaded album_id/source combinations
        self.setup_ui()

    def update_downloaded_albums(self, downloaded_albums: set):
        """Update downloaded albums and refresh widget statuses.

        Args:
            downloaded_albums: Set of (album_id, source) tuples for downloaded albums
        """
        self.downloaded_albums = downloaded_albums

        # Update all album art widgets in grid view
        if hasattr(self, "grid_view") and self.grid_view:
            self.grid_view.update_download_statuses(downloaded_albums)

        # Update all album art widgets in list view
        if hasattr(self, "list_view") and self.list_view:
            self.list_view.update_download_statuses(downloaded_albums)

        # Also initialize child views if they don't have the state yet
        self._ensure_child_views_initialized()

    def _ensure_child_views_initialized(self):
        """Ensure child views have the current downloaded albums state."""
        if self.downloaded_albums:
            if (
                hasattr(self, "grid_view")
                and self.grid_view
                and not hasattr(self.grid_view, "_current_downloaded_albums")
            ):
                self.grid_view.update_download_statuses(self.downloaded_albums)
            if (
                hasattr(self, "list_view")
                and self.list_view
                and not hasattr(self.list_view, "_current_downloaded_albums")
            ):
                self.list_view.update_download_statuses(self.downloaded_albums)

    def setup_ui(self):
        """Set up the discography view."""
        layout = QVBoxLayout(self)

        # Controls bar
        controls_layout = QHBoxLayout()

        # View toggle buttons
        self.view_button_group = QButtonGroup()

        self.grid_view_btn = QToolButton()
        self.grid_view_btn.setText("Grid")
        self.grid_view_btn.setIcon(qta.icon("fa5s.th"))
        self.grid_view_btn.setCheckable(True)
        self.grid_view_btn.setChecked(True)
        self.grid_view_btn.clicked.connect(lambda: self.switch_view("grid"))

        self.list_view_btn = QToolButton()
        self.list_view_btn.setText("List")
        self.list_view_btn.setIcon(qta.icon("fa5s.list"))
        self.list_view_btn.setCheckable(True)
        self.list_view_btn.clicked.connect(lambda: self.switch_view("list"))

        self.view_button_group.addButton(self.grid_view_btn)
        self.view_button_group.addButton(self.list_view_btn)

        # Sort controls
        self.sort_label = QLabel("Sort by:")
        self.sort_title_btn = QPushButton("Title")
        self.sort_title_btn.setIcon(qta.icon("fa5s.font"))
        self.sort_artist_btn = QPushButton("Artist")
        self.sort_artist_btn.setIcon(qta.icon("fa5s.user"))
        self.sort_year_btn = QPushButton("Year")
        self.sort_year_btn.setIcon(qta.icon("fa5s.calendar-alt"))

        self.sort_title_btn.clicked.connect(lambda: self.sort_items("title"))
        self.sort_artist_btn.clicked.connect(lambda: self.sort_items("artist"))
        self.sort_year_btn.clicked.connect(lambda: self.sort_items("year"))

        controls_layout.addWidget(QLabel("View:"))
        controls_layout.addWidget(self.grid_view_btn)
        controls_layout.addWidget(self.list_view_btn)
        controls_layout.addWidget(QLabel("|"))
        controls_layout.addWidget(self.sort_label)
        controls_layout.addWidget(self.sort_title_btn)
        controls_layout.addWidget(self.sort_artist_btn)
        controls_layout.addWidget(self.sort_year_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Stacked widget for different views
        self.stacked_widget = QStackedWidget()

        # Grid view
        self.grid_view = AlbumArtGridView()
        self.grid_view.item_selected.connect(self.item_selected.emit)
        self.grid_view.download_requested.connect(self.download_requested.emit)

        # List view
        self.list_view = DiscographyListView()
        self.list_view.item_selected.connect(self.item_selected.emit)
        self.list_view.download_requested.connect(self.download_requested.emit)

        self.stacked_widget.addWidget(self.grid_view)
        self.stacked_widget.addWidget(self.list_view)

        layout.addWidget(self.stacked_widget)

        # Set default view
        self.switch_view("grid")

    def switch_view(self, view_type: str):
        """Switch between grid and list views."""
        self.current_view = view_type

        if view_type == "grid":
            self.stacked_widget.setCurrentWidget(self.grid_view)
            self.grid_view_btn.setChecked(True)
            self.list_view_btn.setChecked(False)
        elif view_type == "list":
            self.stacked_widget.setCurrentWidget(self.list_view)
            self.grid_view_btn.setChecked(False)
            self.list_view_btn.setChecked(True)

        self.view_changed.emit(view_type)

    def add_item(self, item_data: dict[str, Any], service: str | None = None):
        """Add an item to both views."""
        item_id = item_data.get("id", "")

        # Ensure item_data has the source field for download status tracking
        item_data_with_source = item_data.copy()
        if service and "source" not in item_data_with_source:
            item_data_with_source["source"] = service

        # Pass parent pending artwork to grid view
        self.grid_view.add_item(item_data_with_source, self.pending_artwork)
        self.list_view.add_item(item_data_with_source, service)

        # Track if artwork was consumed for this item
        if item_id in self.pending_artwork:
            self._consumed_artwork_ids.add(item_id)

    def add_album_content(
        self,
        album_info: dict[str, Any],
        tracks: list[dict[str, Any]],
        service: str | None = None,
    ):
        """Add album content - single album in grid view, individual tracks in list view."""
        album_id = album_info.get("id", "")

        # Only add album to grid view if we have tracks or meaningful album info
        # Don't add empty albums to grid view
        if tracks or (
            album_info and any(album_info.get(key) for key in ["id", "title", "artist"])
        ):
            # For grid view, add the album as a single item
            album_item = {
                "id": album_id,
                "title": album_info.get("title", "Unknown Album"),
                "artist": album_info.get("artist", "Unknown Artist"),
                "type": "Album",
                "year": album_info.get("year", ""),
                "duration_formatted": album_info.get("total_duration", ""),
                "track_count": album_info.get("total_tracks", len(tracks)),
                "quality": album_info.get("quality", ""),
                "artwork_url": tracks[0].get("artwork_url") if tracks else None,
                "hires": album_info.get("hires", False),
                "is_explicit": album_info.get("is_explicit", False),
                "source": service,
            }
            # Pass parent pending artwork to grid view
            self.grid_view.add_item(album_item, self.pending_artwork)

            # Track if artwork was consumed for the album
            if album_id in self.pending_artwork:
                self._consumed_artwork_ids.add(album_id)

        # For list view, add individual tracks (always add tracks if they exist)
        for track in tracks:
            # Add album_id to track data so we can find tracks by album later
            track_with_album_id = track.copy()
            track_with_album_id["album_id"] = album_id
            self.list_view.add_item(track_with_album_id, service)
            # Track consumed artwork for tracks too
            track_id = track.get("id", "")
            if track_id in self.pending_artwork:
                self._consumed_artwork_ids.add(track_id)

    def update_item_artwork(self, item_id: str, pixmap: QPixmap):
        """Update artwork for a specific item in both views."""
        self.grid_view.update_item_artwork(item_id, pixmap)
        # List view doesn't show artwork, so no update needed there

        # Also store in our own pending artwork cache for any future items
        self.pending_artwork[item_id] = pixmap

    def clear_all(self):
        """Clear all items from both views and pending artwork."""
        self.clear_items()
        self.pending_artwork.clear()
        self._consumed_artwork_ids.clear()

    def clear_items(self):
        """Clear all items from both views."""
        self.grid_view.clear_items()
        self.list_view.clear_items()

    def _clear_consumed_artwork(self):
        """Clear artwork that has been consumed by items to prevent memory leaks."""
        for item_id in self._consumed_artwork_ids:
            self.pending_artwork.pop(item_id, None)
        self._consumed_artwork_ids.clear()

    def clear_all_pending_artwork(self):
        """Clear all pending artwork. Use when switching to completely different content."""
        self.pending_artwork.clear()
        self._consumed_artwork_ids.clear()

    def set_content(self, metadata: dict[str, Any]):
        """Set content based on metadata type."""
        if metadata is None:
            return

        content_type = metadata.get("content_type", "")
        service = metadata.get("service")

        if content_type == "album":
            # Handle album content - single album in grid, tracks in list
            album_info = metadata.get("album_info", {})
            tracks = metadata.get("items", [])

            # Only add album content if there are tracks or valid album info
            if tracks or album_info:
                self.add_album_content(album_info, tracks, service)
        elif content_type == "artist":
            # Handle artist content - collection of albums and singles
            albums_or_singles = metadata.get("items", [])
            for album_or_single in albums_or_singles:
                # Each item should have "type" field indicating "album" or "single"
                if album_or_single.get("content_type") in ["album", "single"]:
                    self.add_album_content(
                        album_or_single.get("album_info"),
                        album_or_single.get("items", []),
                        service,
                    )
                else:
                    # If type is not recognized, treat as generic item
                    self.add_item(album_or_single, service)
        else:
            # Handle other content types - add items to both views
            items = metadata.get("items", [])
            for item in items:
                self.add_item(item, service)

        # Clean up consumed artwork after content is set
        self._clear_consumed_artwork()

        # Update album widgets opacity based on current downloaded albums
        self._update_album_downloaded_status()

    def add_album_progressively(self, album_metadata: dict[str, Any]):
        """Add a single album to the view progressively during streaming."""
        if album_metadata is None:
            return

        content_type = album_metadata.get("content_type", "")
        service = album_metadata.get("service")

        if content_type in ["album", "single"]:
            album_info = album_metadata.get("album_info", {})
            tracks = album_metadata.get("items", [])

            # Add the album content to both views
            if tracks or album_info:
                self.add_album_content(album_info, tracks, service)
                # Update opacity for the newly added album
                self._update_album_downloaded_status()

    def sort_items(self, sort_by: str):
        """Sort items by the specified criteria."""
        # This would implement sorting logic

    def set_loading_state(self, loading: bool):
        """Set loading state for the view."""
        self.setEnabled(not loading)

    def get_current_view_type(self) -> str:
        """Get the current view type."""
        return self.current_view

    def _update_album_downloaded_status(self):
        """Update the download status of album art widgets based on download history."""
        # Update grid view widgets
        for widget in self.grid_view.items:
            if hasattr(widget, "item_data"):
                album_id = widget.item_data.get("id", "")
                source = widget.item_data.get("source", "")
                album_key = (album_id, source)
                is_downloaded = album_key in self.downloaded_albums
                widget.set_downloaded_status(is_downloaded)
