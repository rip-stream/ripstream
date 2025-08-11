# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Download handler for managing download operations and UI updates."""

import logging
from datetime import UTC, datetime
from typing import Any

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from ripstream.config.user import UserConfig
from ripstream.models.enums import DownloadStatus
from ripstream.ui.download_worker import DownloadWorker
from ripstream.ui.downloads_view import DownloadsHistoryView

logger = logging.getLogger(__name__)


class DownloadHandler(QObject):
    """Handles download operations and UI updates."""

    downloaded_albums_updated = pyqtSignal(set)  # set of (album_id, source) tuples

    def __init__(
        self, config: UserConfig, downloads_view: DownloadsHistoryView, status_label
    ):
        super().__init__()
        self.config = config
        self.downloads_view = downloads_view
        self.status_label = status_label
        self.download_workers: list[DownloadWorker] = []
        self.worker_queue_index = 0  # Round-robin assignment
        self._setup_download_workers()

    def _setup_download_workers(self):
        """Set up download workers based on user configuration."""
        # Determine number of workers based on config
        if not self.config.downloads.concurrency:
            # Single-threaded mode
            max_workers = 1
        else:
            max_workers = self.config.downloads.max_connections
            if max_workers <= 0:  # -1 or invalid values
                max_workers = 6  # Default fallback
            # Cap at reasonable limit to prevent resource exhaustion
            max_workers = min(max_workers, 10)

        # Create workers
        for _i in range(max_workers):
            worker = self._create_download_worker()
            self.download_workers.append(worker)
            self._connect_worker_signals(worker)

    def _create_download_worker(self) -> DownloadWorker:
        """Create and configure download worker."""
        return DownloadWorker(self.config)

    def _connect_worker_signals(self, worker: DownloadWorker):
        """Connect download worker signals to handlers."""
        worker.download_started.connect(self._handle_download_started)
        worker.download_progress.connect(self._handle_download_progress)
        worker.download_completed.connect(self._handle_download_completed)
        worker.download_error.connect(self._handle_download_error)
        # Connect raw speed updates so we can compute averages at the UI
        worker.download_speed.connect(self._handle_download_speed)

    def handle_download_request(
        self, item_details: dict, existing_download_id: str | None = None
    ):
        """Handle download request for an item."""
        if existing_download_id:
            # This is a retry - update the existing download record
            self.downloads_view.update_download_status(existing_download_id, "PENDING")
            download_id = existing_download_id
        else:
            # This is a new download - create a new record
            download_data = self._create_download_record(item_details)

            # Add to downloads view and get the database download_id
            self.downloads_view.add_download(download_data)

            # Get the download_id from the database record
            download_id = download_data.get("download_id")

        # Get the next available worker (round-robin)
        worker = self._get_next_worker()

        # Start worker if not running
        if not worker.isRunning():
            worker.start()

        # Queue the download with the correct download_id
        worker.queue_download(item_details, download_id)

    def _get_next_worker(self) -> DownloadWorker:
        """Get the next worker using round-robin assignment."""
        if not self.download_workers:
            msg = "No download workers available"
            raise RuntimeError(msg)

        worker = self.download_workers[self.worker_queue_index]
        self.worker_queue_index = (self.worker_queue_index + 1) % len(
            self.download_workers
        )
        return worker

    def _create_download_record(self, item_details: dict) -> dict[str, Any]:
        """Create a download record for the downloads view."""
        # Normalize common metadata keys from providers/workers
        track_number = (
            item_details.get("track_number") or item_details.get("tracknumber") or None
        )
        disc_number = (
            item_details.get("disc_number") or item_details.get("discnumber") or None
        )

        # Duration can appear as seconds or milliseconds depending on provider
        duration_seconds = item_details.get("duration_seconds")
        if duration_seconds is None:
            dur = item_details.get("duration")
            if isinstance(dur, (int, float)):
                duration_seconds = float(dur)
            else:
                dur_ms = item_details.get("duration_ms")
                if isinstance(dur_ms, (int, float)):
                    duration_seconds = float(dur_ms) / 1000.0

        record: dict[str, Any] = {
            "title": item_details.get("title", "Unknown Title"),
            "artist": item_details.get("artist", "Unknown Artist"),
            "album": item_details.get(
                "album", item_details.get("type", "Unknown Album")
            ),
            "media_type": "track",
            "source": item_details.get("source", "qobuz"),
            "source_id": item_details.get("id", ""),
            "progress": 0,
            "started_at": datetime.now(UTC),
            "completed_at": None,
            "album_id": item_details.get("album_id"),
            # pass-through of technical audio info from metadata providers when present
            "audio_info": item_details.get("audio_info"),
            # enrich with optional fields expected by DownloadRecord when available
            "track_number": track_number,
            "disc_number": disc_number,
            "duration_seconds": duration_seconds,
            "album_artist": item_details.get("album_artist")
            or item_details.get("albumartist"),
        }

        return record

    def _handle_download_started(self, _download_id: str, item_details: dict):
        """Handle download started signal."""
        title = item_details.get("title", "Unknown Title")
        self.status_label.setText(f"Download started: {title}")

    def _handle_download_progress(self, download_id: str, progress_percentage: int):
        """Handle download progress signal."""
        self.downloads_view.update_download_progress(
            download_id, progress_percentage, DownloadStatus.DOWNLOADING
        )

    def _handle_download_speed(self, download_id: str, speed_bps: float):
        """Handle per-thread raw speed updates (bytes per second)."""
        # Only update the raw speed; avoid DB writes and heavy UI work.
        # The stats timer will refresh the average periodically.
        self.downloads_view.update_download_speed(download_id, float(speed_bps))

    def _get_current_progress(self, download_id: str) -> int:
        """Read current progress for a download_id from the table to reuse on speed-only updates."""
        table = self.downloads_view.downloads_table
        for row in range(table.rowCount()):
            status_item = table.item(row, 4)
            if (
                status_item
                and status_item.data(Qt.ItemDataRole.UserRole) == download_id
            ):
                progress_item = table.item(row, 5)
                if progress_item:
                    try:
                        return int(str(progress_item.text()).replace("%", "").strip())
                    except ValueError:
                        return 0
        return 0

    def _handle_download_completed(self, download_id: str, success: bool, message: str):
        """Handle download completed signal."""
        if success:
            self.status_label.setText(f"Download completed: {message}")
            self.downloads_view.update_download_status(
                download_id, DownloadStatus.COMPLETED.value
            )
            # Emit signal to update album art widgets
            self._emit_downloaded_albums_update()
        else:
            self.status_label.setText(f"Download failed: {message}")
            self.downloads_view.update_download_status(
                download_id, DownloadStatus.FAILED.value
            )

    def _handle_download_error(self, download_id: str, error_message: str):
        """Handle download error signal."""
        self.status_label.setText(f"Download error: {error_message}")
        self.downloads_view.update_download_status(
            download_id, DownloadStatus.FAILED.value
        )
        QMessageBox.warning(None, "Download Error", f"Download failed: {error_message}")

    def _emit_downloaded_albums_update(self):
        """Emit signal with updated downloaded albums."""
        try:
            # Get downloaded albums from the download service
            downloaded_albums = (
                self.downloads_view.download_service.get_downloaded_albums()
            )
            self.downloaded_albums_updated.emit(downloaded_albums)
        except Exception:
            logger.exception("Failed to emit downloaded albums update")

    def cleanup(self):
        """Clean up download resources."""
        for worker in self.download_workers:
            if worker.isRunning():
                worker.stop()
                worker.quit()
                worker.wait()
        self.download_workers.clear()
