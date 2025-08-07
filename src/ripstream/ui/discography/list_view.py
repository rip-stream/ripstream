# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""List view for displaying discography items."""

from typing import Any, ClassVar

import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)


class QualityMapper:
    """Generic quality mapping system for different streaming services."""

    # Quality mappings for each service
    QUALITY_MAPPINGS: ClassVar[dict[str, dict[int, str]]] = {
        "qobuz": {
            1: "320kbps MP3",
            2: "16-bit/44.1kHz FLAC",
            3: "24-bit/≤96kHz FLAC",
            4: "24-bit/≥96kHz FLAC",
        },
        "tidal": {
            0: "256kbps AAC",
            1: "320kbps AAC",
            2: "16-bit/44.1kHz FLAC",
            3: "24-bit/44.1kHz MQA FLAC",
        },
        "deezer": {
            0: "128kbps MP3",
            1: "320kbps MP3",
            2: "16-bit/44.1kHz FLAC",
        },
        "soundcloud": {
            0: "128kbps MP3",
        },
        "youtube": {
            0: "Variable Quality",
        },
    }

    @classmethod
    def get_quality_description(cls, service: str, quality_value: Any) -> str:
        """
        Get quality description for a given service and quality value.

        Args:
            service: The streaming service name (e.g., 'qobuz', 'tidal')
            quality_value: The quality value (int or str)

        Returns
        -------
            Human-readable quality description or the original value if not found
        """
        if not service or quality_value is None:
            return str(quality_value) if quality_value is not None else "-"

        service_lower = service.lower()
        service_mappings = cls.QUALITY_MAPPINGS.get(service_lower, {})

        # Try to convert quality_value to int if it's a string
        try:
            if isinstance(quality_value, str) and quality_value.isdigit():
                quality_value = int(quality_value)
        except (ValueError, TypeError):
            pass

        # Return mapped description or original value
        if isinstance(quality_value, int) and quality_value in service_mappings:
            return service_mappings[quality_value]
        return str(quality_value)


class DiscographyListView(QTableWidget):
    """List view for displaying discography items."""

    item_selected = pyqtSignal(str)  # item_id
    download_requested = pyqtSignal(dict)  # item_details

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_downloaded_albums = set()  # Initialize empty set
        self.setup_ui()

    def setup_ui(self):
        """Set up the list view."""
        # Set up columns
        headers = [
            "Title",
            "Artist",
            "Album",
            "Year",
            "Duration",
            "Tracks",
            "Quality",
            "Actions",
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        # Configure table
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSortingEnabled(True)

        # Disable editing for all items
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Configure column widths
        header = self.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
            header.setSectionResizeMode(
                1, QHeaderView.ResizeMode.ResizeToContents
            )  # Artist
            header.setSectionResizeMode(
                2, QHeaderView.ResizeMode.ResizeToContents
            )  # Type
            header.setSectionResizeMode(
                3, QHeaderView.ResizeMode.ResizeToContents
            )  # Year
            header.setSectionResizeMode(
                4, QHeaderView.ResizeMode.ResizeToContents
            )  # Duration
            header.setSectionResizeMode(
                5, QHeaderView.ResizeMode.ResizeToContents
            )  # Tracks
            header.setSectionResizeMode(
                6, QHeaderView.ResizeMode.ResizeToContents
            )  # Quality
            header.setSectionResizeMode(
                7, QHeaderView.ResizeMode.ResizeToContents
            )  # Actions

        # Connect selection signal
        self.itemSelectionChanged.connect(self.on_selection_changed)

        # Connect double-click signal
        self.itemDoubleClicked.connect(self.on_item_double_clicked)

    def add_item(self, item_data: dict[str, Any], service: str | None = None):
        """Add an item to the list."""
        row = self.rowCount()
        self.insertRow(row)

        # Title (without track number prefix)
        title = item_data.get("title", "Unknown")
        title_item = QTableWidgetItem(title)
        title_item.setData(Qt.ItemDataRole.UserRole, item_data.get("id"))
        # Store the complete item data for later retrieval
        title_item.setData(Qt.ItemDataRole.UserRole + 1, item_data)
        self.setItem(row, 0, title_item)

        # Artist
        artist = item_data.get("artist", "")
        if not artist:
            artist = "Unknown"
        artist_item = QTableWidgetItem(artist)
        self.setItem(row, 1, artist_item)

        # Type (show album name for tracks, truncated if too long)
        item_type = item_data.get("type", "Album")
        if item_type == "Track" and "album" in item_data:
            album_name = item_data["album"]
            # Truncate album name if longer than 25 characters
            if len(album_name) > 25:
                album_name = album_name[:22] + "..."
            type_display = album_name
        else:
            type_display = item_type
        type_item = QTableWidgetItem(type_display)
        self.setItem(row, 2, type_item)

        # Year
        year = item_data.get("year", "")
        year_item = QTableWidgetItem(str(year) if year else "-")
        self.setItem(row, 3, year_item)

        # Duration
        duration = item_data.get("duration_formatted", "")
        duration_item = QTableWidgetItem(duration or "-")
        self.setItem(row, 4, duration_item)

        # Tracks (show track number for individual tracks)
        track_number = item_data.get("track_number")
        if item_type == "Track" and track_number:
            tracks_item = QTableWidgetItem(f"Track {track_number}")
        else:
            track_count = item_data.get("track_count", 0)
            tracks_item = QTableWidgetItem(str(track_count) if track_count else "-")
        self.setItem(row, 5, tracks_item)

        # Quality (mapped to human-readable description)
        quality = item_data.get("quality", "")
        service_ = item_data.get("service", service)
        quality_description = QualityMapper.get_quality_description(service_, quality)
        quality_item = QTableWidgetItem(quality_description)
        self.setItem(row, 6, quality_item)

        # Actions
        actions_widget = self.create_actions_widget(item_data)
        self.setCellWidget(row, 7, actions_widget)

        # Apply current download status to the new item
        if hasattr(self, "_current_downloaded_albums"):
            self._apply_download_status_to_row(
                row, item_data, self._current_downloaded_albums
            )

    def create_actions_widget(self, item_data: dict[str, Any]) -> QWidget:
        """Create action buttons for an item."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)

        item_data.get("id", "")

        # Download button
        download_btn = QPushButton("Download")
        download_btn.setIcon(qta.icon("fa5s.download"))
        download_btn.setFixedSize(80, 25)
        download_btn.clicked.connect(lambda: self.download_requested.emit(item_data))
        layout.addWidget(download_btn)

        layout.addStretch()
        return widget

    def on_selection_changed(self):
        """Handle selection changes."""
        current_row = self.currentRow()
        if current_row >= 0:
            title_item = self.item(current_row, 0)
            if title_item:
                item_id = title_item.data(Qt.ItemDataRole.UserRole)
                if item_id:
                    self.item_selected.emit(item_id)

    def _extract_row_data(self, row: int) -> dict[str, Any]:
        """Extract data from a table row."""
        row_data = {}
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                if col == 0:  # Title column has the item_id in UserRole
                    row_data["id"] = item.data(Qt.ItemDataRole.UserRole)
                    row_data["title"] = item.text()
                elif col == 1:  # Artist column
                    row_data["artist"] = item.text()
                elif col == 2:  # Type/Album column
                    row_data["type"] = item.text()
                elif col == 3:  # Year column
                    row_data["year"] = item.text()
                elif col == 4:  # Duration column
                    row_data["duration_formatted"] = item.text()
                elif col == 5:  # Tracks column
                    row_data["track_count"] = item.text()
                elif col == 6:  # Quality column
                    row_data["quality"] = item.text()
        return row_data

    def on_item_double_clicked(self, item):
        """Handle double-click events on items."""
        if not item:
            return

        row = item.row()
        title_item = self.item(row, 0)
        if not title_item:
            return

        item_id = title_item.data(Qt.ItemDataRole.UserRole)
        if not item_id:
            return

        row_data = self._extract_row_data(row)
        self.download_requested.emit(row_data)

    def get_tracks_by_album_id(self, album_id: str) -> list[dict[str, Any]]:
        """Get all tracks that belong to a specific album ID."""
        tracks = []
        for row in range(self.rowCount()):
            title_item = self.item(row, 0)  # Title column
            if title_item:
                # Get the complete item data
                item_data = title_item.data(Qt.ItemDataRole.UserRole + 1)
                if item_data and isinstance(item_data, dict):
                    # Check if this track belongs to the album
                    track_album_id = item_data.get("album_id")
                    if track_album_id == album_id:
                        tracks.append(item_data)
        return tracks

    def clear_items(self):
        """Clear all items from the list."""
        self.setRowCount(0)

    def update_download_statuses(self, downloaded_albums: set):
        """Update download statuses for all items in the list.

        Args:
            downloaded_albums: Set of (album_id, source) tuples for downloaded albums
        """
        # Store current downloaded albums for new items
        self._current_downloaded_albums = downloaded_albums

        for row in range(self.rowCount()):
            title_item = self.item(row, 0)
            if title_item:
                item_data = title_item.data(Qt.ItemDataRole.UserRole + 1)
                if item_data and isinstance(item_data, dict):
                    self._apply_download_status_to_row(
                        row, item_data, downloaded_albums
                    )

    def _apply_download_status_to_row(
        self, row: int, item_data: dict, downloaded_albums: set
    ):
        """Apply download status to a specific row."""
        album_id = item_data.get("id")
        source = item_data.get("source")

        if album_id and source:
            is_downloaded = (album_id, source) in downloaded_albums

            # Get the actions widget (download button)
            actions_widget = self.cellWidget(row, 7)
            if actions_widget:
                # Update the download button appearance
                download_btn = actions_widget.findChild(QPushButton)
                if download_btn:
                    if is_downloaded:
                        download_btn.setText("Downloaded")
                        download_btn.setIcon(
                            qta.icon("fa5s.check-circle", color="green")
                        )
                        download_btn.setEnabled(False)
                        download_btn.setStyleSheet("""
                            QPushButton {
                                background-color: rgba(0, 128, 0, 0.3);
                                color: green;
                                border: 1px solid green;
                            }
                        """)
                    else:
                        download_btn.setText("Download")
                        download_btn.setIcon(qta.icon("fa5s.download"))
                        download_btn.setEnabled(True)
                        download_btn.setStyleSheet("")
