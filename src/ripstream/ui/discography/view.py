# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Complete discography view with grid/list toggle."""

from typing import Any

import qtawesome as qta
from PyQt6.QtCore import QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from ripstream.ui.discography.grid_view import AlbumArtGridView
from ripstream.ui.discography.list_view import DiscographyListView

# SCREAMING CONSTANTS for favorites flyout icon sizing
FAVORITES_ICON_WIDTH_PX = 100
FAVORITES_ICON_HEIGHT_PX = 100


class DiscographyView(QWidget):
    """Complete discography view with grid/list toggle."""

    item_selected = pyqtSignal(str)  # item_id
    download_requested = pyqtSignal(dict)  # item_details
    view_changed = pyqtSignal(str)  # view_type
    favorites_open_requested = pyqtSignal(dict)  # data for opening a favorite
    favorites_remove_requested = pyqtSignal(dict)  # data for removing a favorite

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "grid"
        self._current_sort_key = "title"
        self._current_sort_desc = False
        self._sort_applied = False
        self._sort_base_labels: dict[str, str] = {
            "title": "Title",
            "artist": "Artist",
            "year": "Year",
        }
        self.pending_artwork = {}  # Store artwork updates until items are available
        self._consumed_artwork_ids = set()  # Track which artwork has been consumed
        self.downloaded_albums = set()  # Store downloaded album_id/source combinations
        self._downloading_album_ids: set[str] = set()
        self._pending_album_ids: set[str] = set()
        self._search_debounce_ms: int = 300
        self._search_timer: QTimer | None = None
        self.search_input: QLineEdit | None = None
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

    def update_active_album_statuses(
        self, downloading_album_ids: set[str], pending_album_ids: set[str]
    ) -> None:
        """Update active album statuses (downloading/pending) and refresh UI."""
        self._downloading_album_ids = downloading_album_ids or set()
        self._pending_album_ids = pending_album_ids or set()
        # Update grid view widgets
        for widget in self.grid_view.items:
            album_id = getattr(widget, "item_id", "")
            if not album_id:
                continue
            # Do not override already downloaded tiles
            if widget.get_status() == "downloaded":
                continue
            if album_id in self._downloading_album_ids:
                widget.set_downloading_status()
            elif (
                album_id in self._pending_album_ids
                and widget.get_status() != "downloaded"
            ):
                widget.set_queued_status()
            elif widget.get_status() in {"queued", "downloading"}:
                # If no longer active and not downloaded, revert to idle
                widget.set_idle_status()

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
        self.sort_title_btn.setCheckable(True)
        self.sort_title_btn.setIcon(qta.icon("fa5s.font"))
        self.sort_artist_btn = QPushButton("Artist")
        self.sort_artist_btn.setCheckable(True)
        self.sort_artist_btn.setIcon(qta.icon("fa5s.user"))
        self.sort_year_btn = QPushButton("Year")
        self.sort_year_btn.setCheckable(True)
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
        # Sunken divider next to sort controls
        sort_divider = QFrame()
        sort_divider.setFrameShape(QFrame.Shape.VLine)
        sort_divider.setFrameShadow(QFrame.Shadow.Sunken)
        controls_layout.addWidget(sort_divider)
        # Search & favorites controls
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search albums or tracks…")
        from contextlib import suppress

        with suppress(Exception):
            # Older bindings may not support it
            self.search_input.setClearButtonEnabled(True)
        controls_layout.addWidget(self.search_input)

        # Add stretch between search and favorites actions
        controls_layout.addStretch()

        # Favorites toggle button (Add/Remove)
        self.favorite_toggle_btn = QPushButton(" Add to favorites")
        self.favorite_toggle_btn.setIcon(qta.icon("fa5s.star"))
        self.favorite_toggle_btn.setEnabled(False)
        # External handler will connect to clicked
        controls_layout.addWidget(self.favorite_toggle_btn)

        # Favorites flyout button with a gallery of thumbnails
        self.favorites_btn = QToolButton()
        self.favorites_btn.setText("Favorites")
        self.favorites_btn.setIcon(qta.icon("fa5s.heart"))
        self.favorites_btn.setCheckable(True)
        self.favorites_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.favorites_menu = QMenu(self)
        self.favorites_btn.setMenu(self.favorites_menu)
        controls_layout.addWidget(self.favorites_btn)
        # Debounce timer
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_debounced)
        self.search_input.textChanged.connect(self._on_search_text_changed)

        layout.addLayout(controls_layout)

        # Sort buttons group (exclusive selection)
        # Note: we don't rely on the group for toggling direction; it only reflects active key visually
        self.sort_button_group = QButtonGroup()
        self.sort_button_group.setExclusive(True)
        self.sort_button_group.addButton(self.sort_title_btn)
        self.sort_button_group.addButton(self.sort_artist_btn)
        self.sort_button_group.addButton(self.sort_year_btn)

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

        # Initialize sort UI state
        self._update_sort_ui()

    # --- Favorites helpers ---
    def update_favorite_toggle(
        self, *, is_favorite: bool, enabled: bool = True
    ) -> None:
        """Update the label and enabled state of the favorites toggle button."""
        if not hasattr(self, "favorite_toggle_btn") or not self.favorite_toggle_btn:
            return
        self.favorite_toggle_btn.setEnabled(bool(enabled))
        self.favorite_toggle_btn.setText(
            " Remove from favorites" if is_favorite else " Add to favorites"
        )

    def populate_favorites_menu(self, items: list[dict[str, Any]]) -> None:
        """Populate the Favorites menu with a thumbnail gallery only."""
        self.favorites_menu.clear()
        from PyQt6.QtGui import QIcon, QPixmap

        gallery = QWidget()
        layout = QHBoxLayout(gallery)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # Create a thumb for each favorite
        for fav in items:
            name = str(fav.get("name", "Artist"))
            btn = QToolButton()
            btn.setAutoRaise(True)
            btn.setToolTip(name)
            btn.setIconSize(QSize(FAVORITES_ICON_WIDTH_PX, FAVORITES_ICON_HEIGHT_PX))

            icon = QIcon()
            pixmap: QPixmap | None = None
            # Pixmap may be populated by earlier artwork_ready events. If not present,
            # try to infer from a photo_url field.
            if isinstance(fav.get("pixmap"), QPixmap):
                pixmap = fav["pixmap"]
            if pixmap and not pixmap.isNull():
                icon = QIcon(pixmap)
            else:
                icon = qta.icon("fa5s.user")
            btn.setIcon(icon)

            data_open = {
                "source": fav.get("source"),
                "artist_id": fav.get("artist_id"),
                "artist_url": fav.get("artist_url"),
                "name": name,
                "favorite_id": fav.get("id"),
            }
            btn.clicked.connect(
                lambda _=False, d=data_open: self.favorites_open_requested.emit(d)
            )
            layout.addWidget(btn)

        # If empty, show a placeholder label
        if layout.count() == 0:
            placeholder = QLabel("No favorites yet")
            placeholder.setStyleSheet("color: #777; padding: 6px;")
            layout.addWidget(placeholder)

        action = QWidgetAction(self.favorites_menu)
        action.setDefaultWidget(gallery)
        self.favorites_menu.addAction(action)

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

        # Reapply current sort to the newly shown view for consistency (if applied)
        self._apply_sort_to_views()
        self._update_sort_ui()
        # Reapply filter so the newly shown view matches current search
        self._apply_search_filter()

    # --- Session snapshot helpers ---
    def build_session_snapshot(self) -> dict[str, Any]:
        """Build a compact snapshot of current content and UI state."""
        snapshot: dict[str, Any] = {
            **self._snapshot_view_and_sort(),
            **self._snapshot_search(),
            **self._snapshot_scroll_positions(),
            **self._snapshot_selection(),
        }
        snapshot["items"] = self._snapshot_items()
        return snapshot

    def _snapshot_view_and_sort(self) -> dict[str, Any]:
        return {
            "view_type": self.current_view,
            "sort_key": self._current_sort_key,
            "sort_desc": self._current_sort_desc,
            "sort_applied": bool(self._sort_applied),
        }

    def _snapshot_search(self) -> dict[str, Any]:
        if self.search_input is not None:
            return {"search_query": self.search_input.text()}
        return {"search_query": ""}

    def _snapshot_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        album_to_art_url = self._map_album_to_artwork_url_from_list()
        from PyQt6.QtCore import Qt

        for row in range(self.list_view.rowCount()):
            title_item = self.list_view.item(row, 0)
            if not title_item:
                continue
            row_data = title_item.data(Qt.ItemDataRole.UserRole + 1)
            if isinstance(row_data, dict):
                items.append(row_data)
        for widget in getattr(self.grid_view, "items", []):
            data = getattr(widget, "item_data", None)
            if not data:
                continue
            pruned = {k: v for k, v in data.items() if k != "pixmap"}
            if not pruned.get("artwork_url"):
                album_id = str(pruned.get("id") or "")
                inferred = album_to_art_url.get(album_id)
                if inferred:
                    pruned["artwork_url"] = inferred
            items.append(pruned)
        return items

    def _map_album_to_artwork_url_from_list(self) -> dict[str, str]:
        from PyQt6.QtCore import Qt

        mapping: dict[str, str] = {}
        for row in range(self.list_view.rowCount()):
            title_item = self.list_view.item(row, 0)
            if not title_item:
                continue
            row_data = title_item.data(Qt.ItemDataRole.UserRole + 1)
            if not isinstance(row_data, dict):
                continue
            album_id = str(row_data.get("album_id") or "")
            art_url = row_data.get("artwork_url")
            if album_id and isinstance(art_url, str) and art_url:
                mapping.setdefault(album_id, art_url)
        return mapping

    def _snapshot_scroll_positions(self) -> dict[str, int]:
        grid_scrollbar = getattr(self.grid_view, "verticalScrollBar", None)
        list_scrollbar = getattr(self.list_view, "verticalScrollBar", None)
        grid_val = (
            self.grid_view.verticalScrollBar().value()
            if callable(grid_scrollbar)
            else 0
        )
        list_val = (
            self.list_view.verticalScrollBar().value()
            if callable(list_scrollbar)
            else 0
        )
        return {"grid_scroll": grid_val, "list_scroll": list_val}

    def _snapshot_selection(self) -> dict[str, Any]:
        from PyQt6.QtCore import Qt as _Qt

        current_row = self.list_view.currentRow()
        if current_row >= 0:
            title_item = self.list_view.item(current_row, 0)
            if title_item:
                selected_id = title_item.data(_Qt.ItemDataRole.UserRole)
                if selected_id:
                    return {"selected_list_item_id": selected_id}
        return {}

    def restore_session_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Restore content and UI state from a snapshot dict with small helpers."""
        if not snapshot:
            return
        self.clear_all()
        self._restore_items(snapshot.get("items", []))
        self._restore_view(snapshot.get("view_type"))
        self._restore_search(snapshot.get("search_query", "") or "")
        self._restore_sort(snapshot)
        self._restore_scrolls(snapshot)
        self._restore_selection(snapshot.get("selected_list_item_id"))
        self._enrich_album_artwork_urls_from_list()

    def _restore_items(self, items: Any) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = (item.get("type") or "").lower()
            if item_type == "album":
                self.grid_view.add_item(item, self.pending_artwork)
            elif item_type == "track" or item.get("track_number") is not None:
                self.list_view.add_item(item, item.get("source"))

    def _restore_view(self, view_type: Any) -> None:
        if view_type in {"grid", "list"}:
            self.switch_view(view_type)

    def _restore_search(self, query: str) -> None:
        if self.search_input is not None:
            self.search_input.setText(query)
            self._apply_search_filter()

    def _restore_sort(self, snapshot: dict[str, Any]) -> None:
        if "sort_key" in snapshot:
            self._current_sort_key = snapshot.get("sort_key", self._current_sort_key)
        if "sort_desc" in snapshot:
            self._current_sort_desc = bool(snapshot.get("sort_desc"))
        if snapshot.get("sort_applied"):
            self._sort_applied = True
            self._apply_sort_to_views()
            self._update_sort_ui()

    def _restore_scrolls(self, snapshot: dict[str, Any]) -> None:
        grid_scroll = int(snapshot.get("grid_scroll", 0) or 0)
        self.grid_view.verticalScrollBar().setValue(grid_scroll)
        list_scroll = int(snapshot.get("list_scroll", 0) or 0)
        self.list_view.verticalScrollBar().setValue(list_scroll)

    def _restore_selection(self, selected_id: Any) -> None:
        if not selected_id:
            return
        from PyQt6.QtCore import Qt as _Qt

        for row in range(self.list_view.rowCount()):
            title_item = self.list_view.item(row, 0)
            if title_item and title_item.data(_Qt.ItemDataRole.UserRole) == selected_id:
                self.list_view.setCurrentCell(row, 0)
                break

    def _enrich_album_artwork_urls_from_list(self) -> None:
        from PyQt6.QtCore import Qt as _Qt2

        album_to_art_url: dict[str, str] = {}
        for row in range(self.list_view.rowCount()):
            title_item = self.list_view.item(row, 0)
            if not title_item:
                continue
            row_data = title_item.data(_Qt2.ItemDataRole.UserRole + 1)
            if not isinstance(row_data, dict):
                continue
            album_id = str(row_data.get("album_id") or "")
            art_url = row_data.get("artwork_url")
            if album_id and isinstance(art_url, str) and art_url:
                album_to_art_url.setdefault(album_id, art_url)

        for widget in getattr(self.grid_view, "items", []):
            album_id = getattr(widget, "item_id", "")
            if not album_id:
                continue
            data = getattr(widget, "item_data", {}) or {}
            if not data.get("artwork_url"):
                inferred = album_to_art_url.get(album_id)
                if inferred:
                    data["artwork_url"] = inferred
                    widget.item_data = data

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

        # Maintain sorting live if already applied
        if self._sort_applied:
            self._apply_sort_to_views()
        # Maintain filtering live
        self._apply_search_filter()

    def add_album_content(
        self,
        album_info: dict[str, Any],
        tracks: list[dict[str, Any]],
        service: str | None = None,
    ):
        """Add album content - single album in grid view, individual tracks in list view."""
        album_id = album_info.get("id", "")

        # Only add album to grid view if it's not already present
        grid_has_album = False
        items_attr = getattr(self.grid_view, "items", [])
        for widget in items_attr:
            if hasattr(widget, "item_id") and widget.item_id == album_id:
                grid_has_album = True
                break

        if not grid_has_album and (
            tracks
            or (
                album_info
                and any(album_info.get(key) for key in ["id", "title", "artist"])
            )
        ):
            # For grid view, add the album as a single item
            # Prefer album artwork thumbnail when available; otherwise fallback to first track artwork
            artwork_url = (
                album_info.get("artwork_thumbnail")
                if isinstance(album_info, dict)
                else None
            )
            if not artwork_url and tracks:
                track0 = tracks[0] if isinstance(tracks, list) and tracks else {}
                artwork_url = (
                    track0.get("artwork_url") if isinstance(track0, dict) else None
                )

            album_item = {
                "id": album_id,
                "title": album_info.get("title", "Unknown Album"),
                "artist": album_info.get("artist", "Unknown Artist"),
                "type": "Album",
                "year": album_info.get("year", ""),
                "duration_formatted": album_info.get("total_duration", ""),
                "track_count": album_info.get("total_tracks", len(tracks)),
                "quality": album_info.get("quality", ""),
                "artwork_url": artwork_url,
                "hires": album_info.get("hires", False),
                "is_explicit": album_info.get("is_explicit", False),
                "source": service,
            }
            # Pass parent pending artwork to grid view
            self.grid_view.add_item(album_item, self.pending_artwork)

            # Track if artwork was consumed for the album
            if album_id in self.pending_artwork:
                self._consumed_artwork_ids.add(album_id)
        else:
            # Even if we didn't add to grid (already present), mark artwork as consumed if pending
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

        # Maintain sorting live if already applied
        if self._sort_applied:
            self._apply_sort_to_views()
        # Maintain filtering live
        self._apply_search_filter()

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

        # Reapply current sort after content changes (if applied)
        self._apply_sort_to_views()
        self._update_sort_ui()
        # Reapply filter after content changes
        self._apply_search_filter()

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
                # Maintain sorting live during progressive updates if applied
                if self._sort_applied:
                    self._apply_sort_to_views()

    def sort_items(self, sort_by: str):
        """Sort items by the specified criteria.

        Clicking the same sort key toggles ascending/descending.
        """
        if not self._sort_applied:
            # First application of sort: always start ascending
            self._current_sort_key = sort_by
            self._current_sort_desc = False
            self._sort_applied = True
        else:
            if sort_by == self._current_sort_key:
                self._current_sort_desc = not self._current_sort_desc
            else:
                self._current_sort_key = sort_by
                self._current_sort_desc = False

        self._apply_sort_to_views()
        self._update_sort_ui()

    def _apply_sort_to_views(self) -> None:
        """Apply current sort settings to both views."""
        if not getattr(self, "_sort_applied", False):
            return

        sort_key = getattr(self, "_current_sort_key", "title")
        descending = getattr(self, "_current_sort_desc", False)

        if hasattr(self, "grid_view") and self.grid_view:
            sort_func = getattr(self.grid_view, "sort_items", None)
            if callable(sort_func):
                sort_func(sort_key, descending)

        if hasattr(self, "list_view") and self.list_view:
            sort_func = getattr(self.list_view, "sort_items", None)
            if callable(sort_func):
                sort_func(sort_key, descending)

    def _update_sort_ui(self) -> None:
        """Reflect current sort key/direction in button texts and check state."""
        key = self._current_sort_key
        desc = self._current_sort_desc
        applied = self._sort_applied

        def label(base: str, active: bool) -> str:
            if not active or not applied:
                return base
            return f"{base} {'▼' if desc else '▲'}"

        # Update texts
        self.sort_title_btn.setText(
            label(self._sort_base_labels["title"], key == "title")
        )
        self.sort_artist_btn.setText(
            label(self._sort_base_labels["artist"], key == "artist")
        )
        self.sort_year_btn.setText(label(self._sort_base_labels["year"], key == "year"))

        # Update checked state
        if not applied:
            # No sort applied yet: no button appears active
            self.sort_title_btn.setChecked(False)
            self.sort_artist_btn.setChecked(False)
            self.sort_year_btn.setChecked(False)
        else:
            if key == "title":
                self.sort_title_btn.setChecked(True)
                self.sort_artist_btn.setChecked(False)
                self.sort_year_btn.setChecked(False)
            elif key == "artist":
                self.sort_title_btn.setChecked(False)
                self.sort_artist_btn.setChecked(True)
                self.sort_year_btn.setChecked(False)
            else:
                self.sort_title_btn.setChecked(False)
                self.sort_artist_btn.setChecked(False)
                self.sort_year_btn.setChecked(True)

    def _on_search_text_changed(self, _text: str) -> None:
        """Debounce search input changes before applying filter."""
        if self._search_timer is None:
            return
        self._search_timer.start(self._search_debounce_ms)

    def _on_search_debounced(self) -> None:
        """Apply filter after debounce timeout."""
        self._apply_search_filter()

    def _apply_search_filter(self) -> None:
        """Apply current search text as filter to both views.

        - Grid view filters by album title
        - List view filters by album or track title
        """
        query = ""
        if self.search_input is not None:
            query = self.search_input.text()

        if hasattr(self, "grid_view") and self.grid_view:
            set_filter = getattr(self.grid_view, "set_filter", None)
            if callable(set_filter):
                set_filter(query)

        if hasattr(self, "list_view") and self.list_view:
            set_filter = getattr(self.list_view, "set_filter", None)
            if callable(set_filter):
                set_filter(query)

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
                if is_downloaded:
                    widget.set_downloaded_status(True)
                else:
                    # Maintain active statuses if present
                    if album_id in self._downloading_album_ids:
                        widget.set_downloading_status()
                    elif album_id in self._pending_album_ids:
                        widget.set_queued_status()
                    else:
                        widget.set_idle_status()
