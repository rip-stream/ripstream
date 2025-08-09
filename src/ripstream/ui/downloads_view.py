# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Downloads history view with table and statistics."""

from typing import Any

import qtawesome as qta
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

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

        stats_layout.addWidget(self.total_group)
        stats_layout.addWidget(self.completed_group)
        stats_layout.addWidget(self.failed_group)
        stats_layout.addWidget(self.pending_group)
        stats_layout.addStretch()

        layout.addWidget(stats_container)

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

    def update_stats(self, stats: dict[str, int]):
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

    def reset_stats(self):
        """Reset all statistics to zero."""
        self.update_stats({"total": 0, "completed": 0, "failed": 0, "pending": 0})


class DownloadsTableWidget(QTableWidget):
    """Table widget for displaying download history."""

    retry_requested = pyqtSignal(str)  # download_id
    remove_requested = pyqtSignal(str)  # download_id

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

        # Retry button (only for failed downloads)
        if status == DownloadStatus.FAILED or str(status).lower() == "failed":
            retry_btn = QPushButton("Retry")
            retry_btn.setIcon(qta.icon("fa5s.redo"))
            retry_btn.setFixedSize(60, 25)
            retry_btn.clicked.connect(lambda: self.retry_requested.emit(download_id))
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
        self, download_id: str, progress: int, status: DownloadStatus
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

                # Update actions widget
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

        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.clear_completed_btn)
        controls_layout.addWidget(self.clear_all_btn)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Downloads table
        self.downloads_table = DownloadsTableWidget()
        self.downloads_table.retry_requested.connect(self.retry_download.emit)
        self.downloads_table.remove_requested.connect(self.remove_download_item)
        layout.addWidget(self.downloads_table)

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
            )

            if download_id:
                # Update the download data with the real ID
                download_data["download_id"] = download_id
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
        self, download_id: str, progress: int, status: DownloadStatus | None = None
    ):
        """Update download progress."""
        try:
            if status is None:
                # If no status provided, use DOWNLOADING as default
                status = DownloadStatus.DOWNLOADING

            # Update UI immediately (this is fast)
            self.downloads_table.update_download_progress(download_id, progress, status)

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
            self.downloads_table.update_download_progress(download_id, progress, status)
            if progress % 10 == 0 or progress == 100:
                self.update_stats()
                self._emit_active_albums_update()

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
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to remove download")
            # Still remove from UI even if database fails
            self.downloads_table.remove_download_item(download_id)

        # Emit signal for external handling
        self.remove_download.emit(download_id)
        self.update_stats()

    def update_stats(self):
        """Update the statistics display."""
        try:
            # Get statistics from the database
            stats = self.download_service.get_download_statistics()
            self.stats_widget.update_stats(stats)
        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to update statistics")
            # Fallback to table-based stats
            stats = self.downloads_table.get_download_stats()
            self.stats_widget.update_stats(stats)

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

            # Emit signal for external handling
            self.clear_all_downloads.emit()

            # Update statistics
            self.update_stats()
            self._emit_active_albums_update()

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to clear all downloads")
