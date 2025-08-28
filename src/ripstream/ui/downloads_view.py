# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Downloads history view with table and statistics."""

from typing import Any

import qtawesome as qta
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from ripstream.config.user import UserConfig
from ripstream.models.download_service import DownloadService
from ripstream.models.enums import DownloadStatus


class DownloadStatsWidget(QWidget):
    """Widget displaying download statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.reset_stats()

    def setup_ui(self):
        """Set up the statistics UI."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Download Statistics")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Stats container
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)

        # Create stat groups
        self.total_group = self.create_stat_group("Total Downloads", "0")
        self.completed_group = self.create_stat_group("Completed", "0")
        self.failed_group = self.create_stat_group("Failed", "0")
        self.pending_group = self.create_stat_group("Pending", "0")
        self.speed_group = self.create_stat_group("Average Speed", "0 Mbps")

        stats_layout.addWidget(self.total_group)
        stats_layout.addWidget(self.completed_group)
        stats_layout.addWidget(self.failed_group)
        stats_layout.addWidget(self.pending_group)
        stats_layout.addWidget(self.speed_group)
        stats_layout.addStretch()

        layout.addWidget(stats_container)

        # Configure speed label: fixed width (up to "9,999.9 Mbps") and right-aligned to prevent flicker
        speed_label = self.speed_group.findChild(QLabel)
        if speed_label:
            font = QFont(speed_label.font())
            font.setBold(True)
            # Match the CSS font-size used in create_stat_group
            font.setPixelSize(24)
            speed_label.setFont(font)
            metrics = QFontMetrics(font)
            max_text = "9,999.9 Mbps"
            fixed_width = metrics.horizontalAdvance(max_text) + 8  # small padding
            speed_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            speed_label.setMinimumWidth(fixed_width)
            speed_label.setMaximumWidth(fixed_width)

    def create_stat_group(self, title: str, value: str) -> QGroupBox:
        """Create a statistics group widget."""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)

        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2196F3;
                margin: 10px;
            }
        """)

        layout.addWidget(value_label)
        return group

    def update_stats(self, stats: dict[str, Any]):
        """Update the statistics display."""
        # Update total
        total_label = self.total_group.findChild(QLabel)
        if total_label:
            total_label.setText(str(stats.get("total", 0)))

        # Update completed
        completed_label = self.completed_group.findChild(QLabel)
        if completed_label:
            completed_label.setText(str(stats.get("completed", 0)))

        # Update failed
        failed_label = self.failed_group.findChild(QLabel)
        if failed_label:
            failed_label.setText(str(stats.get("failed", 0)))

        # Update pending
        pending_label = self.pending_group.findChild(QLabel)
        if pending_label:
            pending_label.setText(str(stats.get("pending", 0)))

        # Update average speed text
        speed_label = self.speed_group.findChild(QLabel)
        if speed_label:
            text = stats.get("average_speed_text")
            if not isinstance(text, str):
                text = "0 Mbps"
            speed_label.setText(text)

    def reset_stats(self):
        """Reset all statistics to zero."""
        self.update_stats({
            "total": 0,
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "average_speed_text": "0 Mbps",
        })


class DownloadsTableWidget(QTableWidget):
    """Table widget for displaying download history."""

    retry_requested = pyqtSignal(str)  # download_id
    remove_requested = pyqtSignal(str)  # download_id
    info_requested = pyqtSignal(str)  # download_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the table UI."""
        # Set up columns
        headers = [
            "Title",
            "Artist",
            "Album",
            "Type",
            "Status",
            "Progress",
            "Started",
            "Actions",
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        # Configure table
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Disable sorting entirely to prevent cell widget issues
        self.setSortingEnabled(False)

        # Configure column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Title
        header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )  # Artist
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Album
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )  # Status
        header.setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )  # Progress
        header.setSectionResizeMode(
            6, QHeaderView.ResizeMode.ResizeToContents
        )  # Started
        header.setSectionResizeMode(
            7, QHeaderView.ResizeMode.ResizeToContents
        )  # Actions

        # Enable custom context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, pos) -> None:
        # Determine the row at the click position
        global_pos = self.viewport().mapToGlobal(pos)
        row = self.rowAt(pos.y())
        if row < 0:
            return
        # Retrieve download_id from Title column user data
        title_item = self.item(row, 0)
        download_id = None
        if title_item:
            download_id = title_item.data(Qt.ItemDataRole.UserRole)
        if not download_id:
            # Fallback to status column user data
            status_item = self.item(row, 4)
            if status_item:
                download_id = status_item.data(Qt.ItemDataRole.UserRole)
        if not download_id:
            return

        menu = QMenu(self)
        info_action = QAction("Info...", self)
        info_action.triggered.connect(
            lambda: self.info_requested.emit(str(download_id))
        )
        menu.addAction(info_action)
        menu.exec(global_pos)

    def add_download_item(self, download_data: dict[str, Any]):
        """Add a download item to the table."""
        # Insert new downloads at the top (row 0) so they appear first
        row = 0
        self.insertRow(row)

        # Title
        title_item = QTableWidgetItem(download_data.get("title", "Unknown"))
        title_item.setData(Qt.ItemDataRole.UserRole, download_data.get("download_id"))
        self.setItem(row, 0, title_item)

        # Artist
        artist_item = QTableWidgetItem(download_data.get("artist", "Unknown"))
        self.setItem(row, 1, artist_item)

        # Album
        album_item = QTableWidgetItem(download_data.get("album", "Unknown"))
        self.setItem(row, 2, album_item)

        # Type
        type_item = QTableWidgetItem(download_data.get("type", "Track"))
        self.setItem(row, 3, type_item)

        # Status
        status = download_data.get("status", DownloadStatus.PENDING)
        status_text = status.value if hasattr(status, "value") else str(status)
        status_item = QTableWidgetItem(status_text)
        status_item.setData(Qt.ItemDataRole.UserRole, download_data.get("download_id"))

        # Color code status
        if status == DownloadStatus.COMPLETED or status_text == "completed":
            status_item.setBackground(Qt.GlobalColor.green)
        elif status == DownloadStatus.FAILED or status_text == "failed":
            status_item.setBackground(Qt.GlobalColor.red)
        elif status == DownloadStatus.DOWNLOADING or status_text == "downloading":
            status_item.setBackground(Qt.GlobalColor.yellow)

        self.setItem(row, 4, status_item)

        # Progress
        progress = download_data.get("progress", 0)
        progress_item = QTableWidgetItem(f"{progress}%")
        self.setItem(row, 5, progress_item)

        # Started
        started_at = download_data.get("started_at")
        started_text = started_at.strftime("%Y-%m-%d %H:%M") if started_at else "-"
        started_item = QTableWidgetItem(started_text)

        # Set sort data for proper chronological sorting
        if started_at:
            # Use timestamp for sorting (newer items have higher values)
            started_item.setData(Qt.ItemDataRole.UserRole + 1, started_at.timestamp())
        else:
            # Use 0 for items without start time (they'll appear last when sorted descending)
            started_item.setData(Qt.ItemDataRole.UserRole + 1, 0)

        self.setItem(row, 6, started_item)

        # Actions
        actions_widget = self.create_actions_widget(download_data)
        self.setCellWidget(row, 7, actions_widget)

    def create_actions_widget(self, download_data: dict[str, Any]) -> QWidget:
        """Create action buttons for a download item."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)

        download_id = download_data.get("download_id", "")
        status = download_data.get("status", DownloadStatus.PENDING)

        # Retry button (always present; enabled only when failed)
        retry_btn = QPushButton("Retry")
        retry_btn.setIcon(qta.icon("fa5s.redo"))
        retry_btn.setFixedSize(60, 25)
        retry_btn.clicked.connect(lambda: self.retry_requested.emit(download_id))
        # Enable for failed or completed status to allow forced retry
        status_text = status.value if hasattr(status, "value") else str(status)
        status_text_lc = status_text.lower()
        is_retryable = status in (
            DownloadStatus.FAILED,
            DownloadStatus.COMPLETED,
        ) or status_text_lc in ("failed", "completed")
        retry_btn.setEnabled(is_retryable)
        layout.addWidget(retry_btn)

        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setIcon(qta.icon("fa5s.times"))
        remove_btn.setFixedSize(60, 25)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(download_id))
        layout.addWidget(remove_btn)

        layout.addStretch()
        return widget

    def update_download_progress(
        self,
        download_id: str,
        progress: int,
        status: DownloadStatus,
        _speed_bps: float | None = None,
    ):
        """Update the progress of a specific download."""
        for row in range(self.rowCount()):
            status_item = self.item(row, 4)
            if (
                status_item
                and status_item.data(Qt.ItemDataRole.UserRole) == download_id
            ):
                # Update progress
                progress_item = self.item(row, 5)
                if progress_item:
                    progress_item.setText(f"{progress}%")

                # Update status
                status_text = status.value if hasattr(status, "value") else str(status)
                status_item.setText(status_text)

                # Update status color
                if status == DownloadStatus.COMPLETED or status_text == "completed":
                    status_item.setBackground(Qt.GlobalColor.green)
                elif status == DownloadStatus.FAILED or status_text == "failed":
                    status_item.setBackground(Qt.GlobalColor.red)
                elif (
                    status == DownloadStatus.DOWNLOADING or status_text == "downloading"
                ):
                    status_item.setBackground(Qt.GlobalColor.yellow)

                # Update actions widget (retry enabled for failed or completed)
                actions_widget = self.create_actions_widget({
                    "download_id": download_id,
                    "status": status,
                })
                self.setCellWidget(row, 7, actions_widget)
                break

    def remove_download_item(self, download_id: str):
        """Remove a download item from the table."""
        for row in range(self.rowCount()):
            status_item = self.item(row, 4)
            if (
                status_item
                and status_item.data(Qt.ItemDataRole.UserRole) == download_id
            ):
                self.removeRow(row)
                break

    def clear_all_downloads(self):
        """Clear all download items from the table."""
        self.setRowCount(0)

    def get_download_stats(self) -> dict[str, int]:
        """Get current download statistics."""
        stats = {
            "total": self.rowCount(),
            "completed": 0,
            "failed": 0,
            "pending": 0,
        }

        for row in range(self.rowCount()):
            status_item = self.item(row, 4)
            if status_item:
                status_text = status_item.text().lower()
                if "completed" in status_text:
                    stats["completed"] += 1
                elif "failed" in status_text:
                    stats["failed"] += 1
                else:
                    # Count downloading and other statuses as pending
                    stats["pending"] += 1

        return stats


class DownloadsHistoryView(QWidget):
    """Complete downloads history view with table and statistics."""

    retry_download = pyqtSignal(str)  # download_id
    remove_download = pyqtSignal(str)  # download_id
    clear_all_downloads = pyqtSignal()
    downloaded_albums_updated = pyqtSignal(set)  # set of (album_id, source) tuples
    active_albums_updated = pyqtSignal(
        set, set
    )  # (downloading_album_ids, pending_album_ids)

    def __init__(self, parent=None, config: UserConfig | None = None):
        super().__init__(parent)
        self.config = config or UserConfig()
        self.download_service = DownloadService(self.config)
        self._speeds_bps: dict[str, float] = {}
        # Map any external IDs provided by callers to the actual DB record IDs stored in the table
        self._id_aliases: dict[str, str] = {}
        self._current_info_index: int | None = None
        self._info_dialog: QDialog | None = None
        self._info_labels: dict[str, QLabel] = {}
        self._artwork_label: QLabel | None = None
        self._info_prev_btn: QPushButton | None = None
        self._info_next_btn: QPushButton | None = None
        self.setup_ui()
        self.setup_timer()
        self.load_downloads()

    def setup_ui(self):
        """Set up the downloads history UI."""
        layout = QVBoxLayout(self)

        # Statistics widget
        self.stats_widget = DownloadStatsWidget()
        layout.addWidget(self.stats_widget)

        # Controls
        controls_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt"))
        self.refresh_btn.clicked.connect(self.refresh_downloads)

        self.clear_completed_btn = QPushButton("Clear Completed")
        self.clear_completed_btn.setIcon(qta.icon("fa5s.check"))
        self.clear_completed_btn.clicked.connect(self.clear_completed_downloads)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setIcon(qta.icon("fa5s.trash"))
        self.clear_all_btn.clicked.connect(self.clear_all_downloads_clicked)

        # Vertical separator between Clear All and Retry All
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)

        # Retry All button
        self.retry_all_btn = QPushButton("Retry All")
        # Use a redo icon
        self.retry_all_btn.setIcon(qta.icon("fa5s.redo"))
        self.retry_all_btn.clicked.connect(self.retry_all_downloads_clicked)
        # Disabled by default until we detect retryable items
        self.retry_all_btn.setEnabled(False)

        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.clear_completed_btn)
        controls_layout.addWidget(self.clear_all_btn)
        controls_layout.addWidget(separator)
        controls_layout.addWidget(self.retry_all_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Downloads table
        self.downloads_table = DownloadsTableWidget()
        self.downloads_table.retry_requested.connect(self.retry_download.emit)
        self.downloads_table.remove_requested.connect(self.remove_download_item)
        self.downloads_table.info_requested.connect(self._open_info_dialog_by_id)
        layout.addWidget(self.downloads_table)

    # ---------- Info dialog ----------
    def _collect_visible_ids(self) -> list[str]:
        ids: list[str] = []
        for row in range(self.downloads_table.rowCount()):
            item = self.downloads_table.item(row, 0)
            download_id = item.data(Qt.ItemDataRole.UserRole) if item else None
            if download_id:
                ids.append(str(download_id))
        return ids

    def _open_info_dialog_by_id(self, download_id: str) -> None:
        ids = self._collect_visible_ids()
        try:
            self._current_info_index = ids.index(download_id)
        except ValueError:
            self._current_info_index = None
        self._ensure_info_dialog()
        self._update_info_dialog(download_id)

    def _navigate_info(self, delta: int) -> None:
        ids = self._collect_visible_ids()
        if self._current_info_index is None:
            return
        new_index = self._current_info_index + delta
        if new_index < 0 or new_index >= len(ids):
            return
        self._current_info_index = new_index
        self._update_info_dialog(ids[new_index])

    def _ensure_info_dialog(self) -> None:
        if self._info_dialog is not None and not self._info_dialog.isHidden():
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Download Info")
        vlayout = QVBoxLayout(dialog)

        tabs = QTabWidget(dialog)
        # Info tab setup with labels to update
        info_tab = QWidget()
        form = QFormLayout(info_tab)

        def mk(label: str) -> QLabel:
            ql = QLabel("")
            form.addRow(label, ql)
            return ql

        self._info_labels = {
            "filename": mk("Filename:"),
            "format": mk("Format:"),
            "length": mk("Length:"),
            "bitrate": mk("Bitrate:"),
            "sample_rate": mk("Sample rate:"),
            "bits_per_sample": mk("Bits per sample:"),
            "channels": mk("Channels:"),
            "album": mk("Album:"),
            "track_number": mk("Track number:"),
            "disc_number": mk("Disc number:"),
        }
        tabs.addTab(info_tab, "Info")

        # Artwork tab with a persistent label
        artwork_tab = QWidget()
        artwork_layout = QVBoxLayout(artwork_tab)
        self._artwork_label = QLabel("No artwork found")
        self._artwork_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        artwork_layout.addWidget(self._artwork_label)
        tabs.addTab(artwork_tab, "Artwork")

        vlayout.addWidget(tabs)

        # Buttons
        btn_row = QHBoxLayout()
        self._info_prev_btn = QPushButton("Previous")
        self._info_next_btn = QPushButton("Next")
        ok_btn = QPushButton("OK")
        btn_row.addWidget(self._info_prev_btn)
        btn_row.addWidget(self._info_next_btn)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        vlayout.addLayout(btn_row)

        self._info_prev_btn.clicked.connect(lambda: self._navigate_info(-1))
        self._info_next_btn.clicked.connect(lambda: self._navigate_info(1))
        ok_btn.clicked.connect(dialog.accept)

        def _on_closed(_code: int) -> None:
            self._info_dialog = None
            self._info_labels = {}
            self._artwork_label = None
            self._info_prev_btn = None
            self._info_next_btn = None

        dialog.finished.connect(_on_closed)

        self._info_dialog = dialog
        dialog.show()

    def _update_info_dialog(self, download_id: str) -> None:
        if self._info_dialog is None:
            return
        details = self.download_service.get_download_details(download_id)
        if not details:
            return

        self._set_info_labels(details)
        self._refresh_artwork(details.get("filename") or "")

        # Update nav button states
        ids = self._collect_visible_ids()
        if self._current_info_index is not None:
            if self._info_prev_btn is not None:
                self._info_prev_btn.setEnabled(self._current_info_index > 0)
            if self._info_next_btn is not None:
                self._info_next_btn.setEnabled(self._current_info_index < len(ids) - 1)

    def _set_info_labels(self, details: dict[str, Any]) -> None:
        def set_text(key: str, value: str) -> None:
            lbl = self._info_labels.get(key)
            if lbl is not None:
                lbl.setText(value)

        set_text("filename", details.get("filename", ""))
        set_text("format", details.get("format", ""))
        set_text("length", details.get("length", ""))
        set_text("bitrate", details.get("bitrate", ""))
        set_text("sample_rate", details.get("sample_rate", ""))
        bps = details.get("bits_per_sample")
        set_text("bits_per_sample", str(bps) if bps is not None else "")
        set_text("channels", details.get("channels", ""))
        set_text("album", details.get("album", ""))
        tn = details.get("track_number")
        set_text("track_number", str(tn) if tn is not None else "")
        dn = details.get("disc_number")
        set_text("disc_number", str(dn) if dn is not None else "")

    def _refresh_artwork(self, file_path: str) -> None:
        label = self._artwork_label
        if label is None:
            return

        from PyQt6.QtGui import QPixmap

        label.setText("No artwork found")
        label.setPixmap(QPixmap())

        cover_path = self._locate_external_cover(file_path)
        if cover_path and self._render_image_path_to_label(label, cover_path):
            return

        embedded_bytes = self._read_embedded_bytes(file_path)
        if embedded_bytes:
            self._set_label_pixmap_from_bytes(label, embedded_bytes)

    @staticmethod
    def _locate_external_cover(file_path: str) -> str | None:
        from pathlib import Path

        try:
            parent = Path(file_path).parent if file_path else None
            if parent and parent.exists():
                for name in ["cover.jpg", "cover.jpeg", "cover.png"]:
                    p = parent / name
                    if p.exists():
                        return str(p)
        except (OSError, ValueError):
            return None
        return None

    @staticmethod
    def _render_image_path_to_label(label: QLabel, image_path: str) -> bool:
        from PIL import Image
        from PyQt6.QtGui import QPixmap

        try:
            from io import BytesIO

            with Image.open(image_path) as img:
                img.thumbnail((512, 512))
                buf = BytesIO()
                img.save(buf, format="PNG")
                data = buf.getvalue()
            pm = QPixmap()
            if pm.loadFromData(data):
                label.setText("")
                label.setPixmap(pm)
                return True
        except (OSError, ValueError):
            return False
        return False

    @staticmethod
    def _read_embedded_bytes(file_path: str) -> bytes | None:
        if not file_path or "." not in file_path:
            return None

        ext = file_path.rsplit(".", 1)[-1].lower()
        try:
            if ext == "flac":
                return DownloadsHistoryView._extract_flac_cover_bytes(file_path)
            if ext == "mp3":
                return DownloadsHistoryView._extract_mp3_cover_bytes(file_path)
            if ext in {"m4a", "mp4", "aac"}:
                return DownloadsHistoryView._extract_mp4_cover_bytes(file_path)
        except (OSError, ValueError):
            return None
        return None

    @staticmethod
    def _extract_flac_cover_bytes(file_path: str) -> bytes | None:
        from mutagen import MutagenError  # type: ignore

        try:
            from mutagen.flac import FLAC  # type: ignore

            fl = FLAC(file_path)
            if getattr(fl, "pictures", None):
                return fl.pictures[0].data
        except (MutagenError, OSError, ValueError):
            return None
        return None

    @staticmethod
    def _extract_mp3_cover_bytes(file_path: str) -> bytes | None:
        from mutagen import MutagenError  # type: ignore

        try:
            from mutagen.id3 import ID3  # type: ignore

            id3 = ID3(file_path)
            apics = id3.getall("APIC")
            if apics:
                return apics[0].data
        except (MutagenError, OSError, ValueError):
            return None
        return None

    @staticmethod
    def _extract_mp4_cover_bytes(file_path: str) -> bytes | None:
        from mutagen import MutagenError  # type: ignore

        try:
            from mutagen.mp4 import MP4  # type: ignore

            mp4 = MP4(file_path)
            covr = (mp4.tags or {}).get("covr")
            if covr:
                return bytes(covr[0])
        except (MutagenError, OSError, ValueError):
            return None
        return None

    @staticmethod
    def _set_label_pixmap_from_bytes(label: QLabel, data: bytes) -> bool:
        from PyQt6.QtGui import QPixmap

        pm = QPixmap()
        if not pm.loadFromData(data):
            return False
        if pm.width() > 512 or pm.height() > 512:
            pm = pm.scaled(
                512,
                512,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        label.setText("")
        label.setPixmap(pm)
        return True

    def setup_timer(self):
        """Set up timer for periodic updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(5000)  # Update every 5 seconds

    def add_download(self, download_data: dict[str, Any]):
        """Add a new download to the history."""
        try:
            # Convert string values to enums if needed
            media_type = download_data.get("media_type")
            if isinstance(media_type, str):
                from ripstream.models.enums import MediaType

                try:
                    media_type = MediaType(media_type.lower())
                except ValueError:
                    media_type = MediaType.TRACK

            source = download_data.get("source")
            if isinstance(source, str):
                from ripstream.models.enums import StreamingSource

                try:
                    source = StreamingSource(source.lower())
                except ValueError:
                    source = StreamingSource.QOBUZ

            # Add to database first
            original_id = download_data.get("download_id")
            download_id = self.download_service.add_download_record(
                title=download_data.get("title", "Unknown"),
                artist=download_data.get("artist", "Unknown"),
                album=download_data.get("album"),
                media_type=media_type,
                source=source,
                source_id=download_data.get("source_id", ""),
                source_url=download_data.get("source_url"),
                session_id=download_data.get("session_id"),
                album_id=download_data.get("album_id"),
                audio_info=download_data.get("audio_info"),
            )

            if download_id:
                # Update the download data with the real ID
                download_data["download_id"] = download_id
                # Record alias mapping if an external ID was provided
                if original_id and original_id != download_id:
                    self._id_aliases[str(original_id)] = str(download_id)
                self.downloads_table.add_download_item(download_data)
                self.update_stats()
            else:
                # If database add failed, still add to UI for consistency
                self.downloads_table.add_download_item(download_data)
                self.update_stats()

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to add download to database")
            # Still add to UI even if database fails
            self.downloads_table.add_download_item(download_data)
            self.update_stats()

    def update_download_progress(
        self,
        download_id: str,
        progress: int,
        status: DownloadStatus | None = None,
        speed_bps: float | None = None,
    ):
        """Update download progress."""
        try:
            # Normalize caller-provided ID to internal DB ID if necessary
            download_id = self._id_aliases.get(download_id, download_id)
            if status is None:
                # If no status provided, use DOWNLOADING as default
                status = DownloadStatus.DOWNLOADING

            if speed_bps is not None:
                self._speeds_bps[download_id] = max(0.0, float(speed_bps))

            # Update UI immediately (this is fast)
            self.downloads_table.update_download_progress(
                download_id, progress, status, speed_bps
            )

            # Only update database for significant progress changes or completion
            # This prevents UI hanging from frequent database writes
            should_update_db = (
                progress == 100  # Always update on completion
                or progress == 0  # Always update on start
                or progress % 10 == 0  # Update every 10%
                or status
                in [
                    DownloadStatus.COMPLETED,
                    DownloadStatus.FAILED,
                ]  # Update on status change
            )

            if should_update_db:
                # Update in database (potentially slow operation)
                self.download_service.update_download_status(
                    download_id, status, float(progress)
                )

            # Update stats less frequently to avoid UI lag
            if progress % 5 == 0 or progress == 100:
                self.update_stats()
                self._emit_active_albums_update()

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to update download progress")
            # Still update UI even if database fails
            self.downloads_table.update_download_progress(
                download_id, progress, status, speed_bps
            )
            if progress % 10 == 0 or progress == 100:
                self.update_stats()
                self._emit_active_albums_update()

    def update_download_speed(self, download_id: str, speed_bps: float) -> None:
        """Lightweight updater for raw speed samples without triggering DB writes or heavy UI work."""
        try:
            normalized_id = self._id_aliases.get(download_id, download_id)
            self._speeds_bps[normalized_id] = max(0.0, float(speed_bps))
        except (TypeError, ValueError):
            # Do not let bad input crash UI
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Invalid speed for %s", download_id, exc_info=True)

    def update_download_status(self, download_id: str, status: str):
        """Update download status."""
        try:
            # Convert string status to DownloadStatus enum if needed
            try:
                status_enum = DownloadStatus(status)
            except ValueError:
                # If status string doesn't match enum, use PENDING as default
                status_enum = DownloadStatus.PENDING

            # Get current progress from UI
            current_progress = 0
            for row in range(self.downloads_table.rowCount()):
                status_item = self.downloads_table.item(row, 4)
                if (
                    status_item
                    and status_item.data(Qt.ItemDataRole.UserRole) == download_id
                ):
                    progress_item = self.downloads_table.item(row, 5)
                    if progress_item:
                        try:
                            current_progress = int(
                                progress_item.text().replace("%", "")
                            )
                        except ValueError:
                            current_progress = 0
                    break

            # Update in database
            self.download_service.update_download_status(
                download_id, status_enum, float(current_progress)
            )

            # Update in UI
            self.downloads_table.update_download_progress(
                download_id, current_progress, status_enum
            )
            self.update_stats()
            self._emit_active_albums_update()

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to update download status")
            # Still update UI even if database fails
            self.downloads_table.update_download_progress(
                download_id, current_progress, status_enum
            )
            self.update_stats()
            self._emit_active_albums_update()

    def update_statistics(self):
        """Update statistics - alias for update_stats."""
        self.update_stats()

    def retry_download_item(self, download_id: str):
        """Retry a download item."""
        try:
            # Retry in database
            success = self.download_service.retry_download(download_id)
            if success:
                # Update UI to reflect retry
                self.update_download_status(download_id, DownloadStatus.PENDING.value)
            else:
                # Log failure but don't crash UI
                import logging

                logger = logging.getLogger(__name__)
                logger.warning("Failed to retry download: %s", download_id)
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to retry download")

        # Emit signal for external handling
        self.retry_download.emit(download_id)

    def remove_download_item(self, download_id: str):
        """Remove a download item."""
        try:
            # Remove from database
            success = self.download_service.remove_download(download_id)
            if success:
                # Remove from UI
                self.downloads_table.remove_download_item(download_id)
            else:
                # Log failure but still remove from UI for consistency
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "Failed to remove download from database: %s", download_id
                )
                self.downloads_table.remove_download_item(download_id)
            # Forget any stored speed for this download
            self._speeds_bps.pop(download_id, None)
            # Clean up aliases pointing to or from this ID
            aliases_to_remove = [
                k
                for k, v in self._id_aliases.items()
                if v == download_id or k == download_id
            ]
            for k in aliases_to_remove:
                self._id_aliases.pop(k, None)
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to remove download")
            # Still remove from UI even if database fails
            self.downloads_table.remove_download_item(download_id)
            self._speeds_bps.pop(download_id, None)
            aliases_to_remove = [
                k
                for k, v in self._id_aliases.items()
                if v == download_id or k == download_id
            ]
            for k in aliases_to_remove:
                self._id_aliases.pop(k, None)

        # Emit signal for external handling
        self.remove_download.emit(download_id)
        self.update_stats()

    def update_stats(self):
        """Update the statistics display."""
        try:
            # Get statistics from the database
            stats = self.download_service.get_download_statistics()
            stats["average_speed_text"] = self._format_average_active_speed()
            self.stats_widget.update_stats(stats)
            # Enable/disable Retry All based on retryable failed items
            self._update_retry_all_button_state()
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to update statistics")
            # Fallback to table-based stats
            stats = self.downloads_table.get_download_stats()
            stats["average_speed_text"] = self._format_average_active_speed()
            self.stats_widget.update_stats(stats)
            # Even on fallback, attempt to update Retry All button state
            self._update_retry_all_button_state()

    def _format_average_active_speed(self) -> str:
        """Compute and format the average speed of active items in kbps.

        Active items are ones with progress strictly between 0 and 100.
        Returns "0 kbps" when none.
        """
        speeds: list[float] = []
        for row in range(self.downloads_table.rowCount()):
            status_item = self.downloads_table.item(row, 4)
            progress_item = self.downloads_table.item(row, 5)
            if not status_item or not progress_item:
                continue
            try:
                progress_val = int(str(progress_item.text()).replace("%", "").strip())
            except (TypeError, ValueError):
                progress_val = 0
            if progress_val <= 0 or progress_val >= 100:
                continue
            download_id = status_item.data(Qt.ItemDataRole.UserRole)
            if not download_id:
                continue
            speed = self._speeds_bps.get(str(download_id))
            if speed is None:
                continue
            speeds.append(float(speed))

        if not speeds:
            return "0 Mbps"

        avg_bps = sum(speeds) / len(speeds)
        # Convert bytes per second to megabits per second (SI)
        avg_mbps = (avg_bps * 8.0) / 1_000_000.0
        return f"{avg_mbps:,.1f} Mbps"

    def refresh_downloads(self):
        """Refresh the downloads list."""
        self.load_downloads()
        self.update_stats()
        self._emit_downloaded_albums_update()
        self._emit_active_albums_update()

    def _emit_downloaded_albums_update(self):
        """Emit signal with updated downloaded albums."""
        try:
            downloaded_albums = self.download_service.get_downloaded_albums()
            self.downloaded_albums_updated.emit(downloaded_albums)
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to emit downloaded albums update")

    def _emit_active_albums_update(self):
        """Emit sets of album IDs that are downloading and pending."""
        try:
            active = self.download_service.get_active_downloads()
            downloading_albums = set()
            pending_albums = set()
            for record in active:
                album_id = getattr(record, "album_id", None)
                if not album_id:
                    continue
                status = getattr(record, "status", None)
                if status == DownloadStatus.DOWNLOADING:
                    downloading_albums.add(album_id)
                elif status == DownloadStatus.PENDING:
                    pending_albums.add(album_id)
            self.active_albums_updated.emit(downloading_albums, pending_albums)
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to emit active albums update")

    def emit_downloaded_albums_signal(self):
        """Emit the downloaded albums signal with current data."""
        try:
            # Use the download service method for consistency
            downloaded_albums = self.download_service.get_downloaded_albums()
            self.downloaded_albums_updated.emit(downloaded_albums)
        except Exception:
            # Log error but don't crash the UI
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to emit downloaded albums signal")

    def load_downloads(self):
        """Load downloads from the database."""
        try:
            # Clear existing items
            self.downloads_table.clear_all_downloads()
            self._speeds_bps.clear()

            # Load recent downloads from database
            downloads = self.download_service.get_recent_downloads()

            # Extract unique album_id/source combinations from completed downloads
            downloaded_albums = set()
            for download in downloads:
                # Only consider completed downloads
                if download.get("status") == DownloadStatus.COMPLETED:
                    album_id = download.get("album_id")
                    source = download.get("source")
                    if album_id and source:
                        downloaded_albums.add((album_id, source))

            # Add each download to the table
            for download in downloads:
                self.downloads_table.add_download_item(download)

            # Update statistics
            self.update_stats()

            # Emit signal with downloaded albums
            self.downloaded_albums_updated.emit(downloaded_albums)
            self._emit_active_albums_update()

        except Exception:
            # Log error but don't crash the UI
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to load downloads")

    def clear_completed_downloads(self):
        """Clear all completed downloads from the database and table."""
        try:
            # Remove completed downloads from database
            self.download_service.clear_completed_downloads()

            # Reload the table
            self.load_downloads()

            # Update statistics
            self.update_stats()
            self._emit_active_albums_update()

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to clear completed downloads")

    def clear_all_downloads_clicked(self):
        """Clear all downloads from the database and table."""
        try:
            # Remove all downloads from database
            self.download_service.clear_all_downloads()

            # Clear the table
            self.downloads_table.clear_all_downloads()
            self._speeds_bps.clear()

            # Emit signal for external handling
            self.clear_all_downloads.emit()

            # Update statistics
            self.update_stats()
            self._emit_active_albums_update()

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to clear all downloads")

    def retry_all_downloads_clicked(self):
        """Retry all failed downloads and refresh the view."""
        try:
            retried = self.download_service.retry_failed_downloads()
            # Refresh UI if any were reset
            if retried is not None:
                self.load_downloads()
                self.update_stats()
                self._emit_active_albums_update()
                self._update_retry_all_button_state()
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to retry all downloads")

    def _update_retry_all_button_state(self) -> None:
        """Enable Retry All only when there are retryable failed downloads."""
        try:
            retryable_count = self.download_service.failed_downloads.count_retryable()
            self.retry_all_btn.setEnabled(retryable_count > 0)
        except (SQLAlchemyError, AttributeError):
            # On error, keep it disabled to be safe
            self.retry_all_btn.setEnabled(False)
