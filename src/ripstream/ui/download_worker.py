# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Download worker for handling asynchronous downloads."""

import asyncio
import logging
from contextlib import suppress
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QThread, pyqtSignal

from ripstream.config.user import UserConfig
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.exceptions import AuthenticationError
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.factory import DownloadProviderFactory
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)


class DownloadWorker(QThread):
    """Worker thread for handling downloads asynchronously."""

    download_started = pyqtSignal(str, dict)  # download_id, item_details
    download_progress = pyqtSignal(str, int)  # download_id, progress_percentage
    download_speed = pyqtSignal(str, float)  # download_id, bytes_per_second
    download_completed = pyqtSignal(str, bool, str)  # download_id, success, message
    download_error = pyqtSignal(str, str)  # download_id, error_message
    progress_check_requested = (
        pyqtSignal()
    )  # Signal to trigger progress check from main thread

    def __init__(self, config: UserConfig):
        super().__init__()
        self.config = config
        self.download_config: DownloaderConfig | None = None
        self.session_manager: SessionManager | None = None
        self.progress_tracker: ProgressTracker | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._download_queue = Queue()
        self._running = True
        # Mapping from UUID to database download ID
        self._download_id_mapping: dict[UUID, str] = {}
        self._current_download_id: str | None = None
        # Retry settings derived from user config
        try:
            cfg_val = getattr(self.config.downloads, "max_retries", 3)
            self._max_track_retries: int = max(0, int(cfg_val))
        except (TypeError, ValueError):
            self._max_track_retries = 3

        # Connect progress check signal to slot
        self.progress_check_requested.connect(self._handle_progress_check_request)

    def run(self):
        """Run the main thread."""
        # Set up the download environment
        self.setup_download_environment()

        # Process download tasks
        while self._running:
            try:
                # Get next download task (non-blocking)
                try:
                    task = self._download_queue.get_nowait()
                    self._process_download_task(task)
                except Empty:
                    # No tasks available, sleep briefly
                    self.msleep(100)
                except Exception:
                    logger.exception("Error getting task from queue")

            except Exception:
                logger.exception("Error in download worker")
                self.msleep(1000)  # Sleep longer on error

        # Clean up when thread stops
        self._cleanup()

    def stop(self):
        """Stop the worker thread."""
        self._running = False

    def queue_download(self, item_details: dict, download_id: str | None = None):
        """Queue a download task."""
        self._download_queue.put((item_details, download_id))

    def _process_download_task(self, task):
        """Process a single download task."""
        item_details, download_id = task
        self.run_download(item_details, download_id)

    def setup_download_environment(self):
        """Set up the download environment with user configuration."""
        self.download_config = self._create_download_config()
        self._apply_user_settings_to_config()
        self._initialize_session_components()

    def _create_download_config(self) -> DownloaderConfig:
        """Create downloader configuration from user settings."""
        return DownloaderConfig(
            download_directory=self.config.downloads.folder,
            max_concurrent_downloads=self.config.downloads.max_connections,
            verify_ssl=self.config.downloads.verify_ssl,
            source_settings=self._get_source_settings(),
        )

    def _get_source_settings(self) -> dict[str, dict[str, Any]]:
        """Get source-specific settings for download configuration."""
        timeout_seconds = self._get_timeout_seconds_default_safe()
        return {
            "qobuz": {
                "requests_per_minute": self.config.downloads.requests_per_minute,
                "timeout_seconds": timeout_seconds,
            }
        }

    def _initialize_session_components(self):
        """Initialize session manager and progress tracker."""
        self.session_manager = SessionManager(self.download_config)
        self.progress_tracker = ProgressTracker()

    def _apply_user_settings_to_config(self):
        """Apply user settings to the download configuration."""
        if not self.download_config:
            return

        self._apply_conversion_settings()
        self._apply_artwork_settings()
        self._apply_metadata_settings()
        self._apply_filepath_settings()
        self._apply_download_settings()

    def _apply_conversion_settings(self):
        """Apply audio conversion settings to download config."""
        if self.config.conversion.enabled:
            settings = {
                "conversion_enabled": True,
                "target_codec": self.config.conversion.codec,
                "sampling_rate": self.config.conversion.sampling_rate,
                "bit_depth": self.config.conversion.bit_depth,
                "lossy_bitrate": self.config.conversion.lossy_bitrate,
            }
            self._add_source_settings("default", settings)

    def _apply_artwork_settings(self):
        """Apply artwork settings to download config."""
        settings = {
            "embed_artwork": self.config.artwork.embed,
            "artwork_size": self.config.artwork.embed_size,
            "artwork_max_width": self.config.artwork.embed_max_width,
            "save_artwork": self.config.artwork.save_artwork,
            "saved_artwork_max_width": self.config.artwork.saved_max_width,
        }
        self._add_source_settings("default", settings)

    def _apply_metadata_settings(self):
        """Apply metadata settings to download config."""
        settings = {
            "embed_metadata": self.config.metadata.embed,
            "save_metadata": self.config.metadata.save,
            "metadata_format": self.config.metadata.format,
        }
        self._add_source_settings("default", settings)

    def _apply_filepath_settings(self):
        """Apply filepath settings to download config."""
        settings = {
            "use_source_subdirectories": self.config.downloads.source_subdirectories,
            "folder_format": self.config.filepaths.folder_format,
            "track_format": self.config.filepaths.track_format,
            "restrict_characters": self.config.filepaths.restrict_characters,
            "truncate_to": self.config.filepaths.truncate_to,
        }
        self._add_source_settings("default", settings)

    def _apply_download_settings(self):
        """Apply download behavior settings from user config to downloader config."""
        behavior_settings = {
            "timeout_seconds": self._get_timeout_seconds_default_safe(),
            "max_retries": self.config.downloads.max_retries,
            "retry_delay": self.config.downloads.retry_delay,
            "chunk_size": self.config.downloads.chunk_size,
        }
        self._add_source_settings("default", behavior_settings)

    def _get_timeout_seconds_default_safe(self) -> float:
        """Return a numeric timeout from config or a sensible default when missing.

        Some tests use lightweight mocks for `self.config.downloads` and may
        not define `timeout_seconds`. We fall back to 120.0 in that case, or
        when the provided value is not castable to float.
        """
        try:
            raw_value = getattr(self.config.downloads, "timeout_seconds", 120.0)
            return float(raw_value)
        except (TypeError, ValueError):
            return 120.0

    def _add_source_settings(self, source: str, settings: dict[str, Any]):
        """Add settings for a specific source."""
        if not self.download_config:
            return

        if source not in self.download_config.source_settings:
            self.download_config.source_settings[source] = {}

        self.download_config.source_settings[source].update(settings)

    def create_download_provider(
        self, service: StreamingSource, credentials: dict[str, Any] | None = None
    ):
        """Create a download provider for the specified service."""
        if not self.session_manager or not self.progress_tracker:
            msg = "Download environment not initialized"
            raise RuntimeError(msg)

        return DownloadProviderFactory.create_provider(
            service=service,
            config=self.download_config,
            session_manager=self.session_manager,
            progress_tracker=self.progress_tracker,
            credentials=credentials,
        )

    def run_download(self, item_details: dict, download_id: str | None = None):
        """Run a download in the worker thread."""
        provider = None
        try:
            # Create a single event loop for the entire download process
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            try:
                download_info = self._extract_download_info(item_details)
                provider = self._create_and_authenticate_provider(download_info)
                download_dir = self._determine_download_directory(download_info)

                # Use the provided download_id or fall back to item_id
                signal_download_id = download_id or download_info["item_id"]

                # Set up progress tracking for this specific download BEFORE starting
                self._setup_download_progress_tracking(provider, signal_download_id)

                self.download_started.emit(signal_download_id, item_details)

                result = self._execute_download(provider, download_info, download_dir)
                self._handle_download_result(result, download_info, signal_download_id)

            finally:
                # Clean up the provider
                if provider:
                    self._cleanup_provider(provider)

                # Clean up progress tracking
                self._cleanup_progress_tracking()

                # Clean up the session manager
                self._cleanup_session_manager()

                # Clean up the event loop
                if self._loop and not self._loop.is_closed():
                    # Cancel any pending tasks
                    pending_tasks = [
                        task
                        for task in asyncio.all_tasks(self._loop)
                        if not task.done()
                    ]
                    for task in pending_tasks:
                        task.cancel()

                    # Wait for tasks to complete
                    if pending_tasks:
                        self._loop.run_until_complete(
                            asyncio.gather(*pending_tasks, return_exceptions=True)
                        )

                    self._loop.close()
                    self._loop = None

        except Exception as e:
            logger.exception("Download failed for item %s", item_details.get("id", ""))
            signal_download_id = download_id or item_details.get("id", "")
            self.download_error.emit(signal_download_id, str(e))

    def _setup_download_progress_tracking(self, provider, download_id: str):
        """Set up progress tracking for a specific download."""
        if hasattr(provider, "progress_tracker") and provider.progress_tracker:
            # Store the database download ID for this download
            self._current_download_id = download_id

            # Store the provider's progress tracker for periodic checking
            self._current_provider = provider

            # Store last known progress to avoid missing updates
            self._last_known_progress = 0

            # Add a progress callback directly to the progress tracker
            progress_tracker = provider.progress_tracker
            progress_tracker.add_callback(self._progress_callback)

            # Set up periodic progress checking from main thread
            from PyQt6.QtCore import QTimer

            self._progress_check_timer = QTimer()
            self._progress_check_timer.timeout.connect(
                lambda: self.progress_check_requested.emit()
            )
            self._progress_check_timer.start(
                1000
            )  # Check every 1 second to avoid UI hanging

    def _progress_callback(self, _download_id, progress):
        """Handle progress updates from download operations."""
        if not hasattr(self, "_current_download_id") or not self._current_download_id:
            return

        try:
            current_progress = int(progress.percentage)

            # Emit progress updates more frequently to ensure UI updates
            if current_progress != self._last_known_progress or progress.is_complete:
                self.download_progress.emit(self._current_download_id, current_progress)
                self._last_known_progress = current_progress

            # Emit raw instantaneous speed for aggregation at UI, throttle to reduce UI load
            now_ms = (
                self.msecsSinceEpoch() if hasattr(self, "msecsSinceEpoch") else None
            )
            last_ms = getattr(self, "_last_speed_emit_ms", None)
            should_emit = last_ms is None
            if now_ms is not None:
                should_emit = should_emit or (now_ms - (last_ms or 0) >= 500)
            if should_emit:
                with suppress(Exception):
                    self.download_speed.emit(
                        self._current_download_id, float(progress.bytes_per_second)
                    )
                if now_ms is not None:
                    self._last_speed_emit_ms = now_ms

            # If completed, clean up progress tracking
            if progress.is_complete:
                self._cleanup_progress_tracking()

        except Exception:
            logger.exception("Error in progress callback")

    def _handle_progress_check_request(self):
        """Handle progress check request from main thread."""
        if self._is_progress_check_in_progress():
            return

        if not self._has_valid_provider_and_download():
            return

        try:
            self._progress_check_in_progress = True
            self._check_progress_updates()
        except Exception:
            logger.exception("Error in main thread progress check")
        finally:
            self._progress_check_in_progress = False

    def _is_progress_check_in_progress(self) -> bool:
        """Check if progress check is already in progress."""
        return (
            hasattr(self, "_progress_check_in_progress")
            and self._progress_check_in_progress
        )

    def _has_valid_provider_and_download(self) -> bool:
        """Check if we have valid provider and download ID."""
        return (
            hasattr(self, "_current_provider")
            and self._current_provider
            and hasattr(self, "_current_download_id")
            and self._current_download_id
        )

    def _check_progress_updates(self):
        """Check for progress updates from the provider."""
        progress_tracker = getattr(self._current_provider, "progress_tracker", None)
        if not progress_tracker:
            return

        all_progress = progress_tracker.get_all_progress()
        self._process_progress_entries(all_progress)

    def _process_progress_entries(self, all_progress):
        """Process progress entries to find active or completed downloads."""
        max_checks = 10  # Limit to prevent UI hanging

        for i, progress in enumerate(all_progress.values()):
            if i >= max_checks:
                break

            if progress.is_active or progress.is_complete:
                self._update_progress_if_needed(progress)
                if progress.is_complete:
                    self._cleanup_progress_tracking()
                break

    def _update_progress_if_needed(self, progress):
        """Update progress if it has changed."""
        current_progress = int(progress.percentage)
        if current_progress != self._last_known_progress:
            self.download_progress.emit(self._current_download_id, current_progress)
            self._last_known_progress = current_progress
        # Emit speed samples during checks, respecting throttle
        now_ms = self.msecsSinceEpoch() if hasattr(self, "msecsSinceEpoch") else None
        last_ms = getattr(self, "_last_speed_emit_ms", None)
        should_emit = last_ms is None
        if now_ms is not None:
            should_emit = should_emit or (now_ms - (last_ms or 0) >= 500)
        if should_emit:
            with suppress(Exception):
                self.download_speed.emit(
                    self._current_download_id, float(progress.bytes_per_second)
                )
            if now_ms is not None:
                self._last_speed_emit_ms = now_ms

    def _cleanup_progress_tracking(self):
        """Clean up progress tracking."""
        # Stop the progress check timer
        if hasattr(self, "_progress_check_timer"):
            self._progress_check_timer.stop()
            self._progress_check_timer.deleteLater()
            delattr(self, "_progress_check_timer")

        # Clean up progress check guard
        if hasattr(self, "_progress_check_in_progress"):
            delattr(self, "_progress_check_in_progress")

        # Remove the callback from the progress tracker
        if hasattr(self, "_current_provider") and self._current_provider:
            progress_tracker = getattr(self._current_provider, "progress_tracker", None)
            if progress_tracker:
                from contextlib import suppress

                with suppress(ValueError, AttributeError):
                    # Callback might not be registered or tracker might not support removal
                    progress_tracker.remove_callback(self._progress_callback)

        if hasattr(self, "_current_provider"):
            delattr(self, "_current_provider")

        if hasattr(self, "_current_download_id"):
            delattr(self, "_current_download_id")

        if hasattr(self, "_last_known_progress"):
            delattr(self, "_last_known_progress")

    def _extract_download_info(self, item_details: dict) -> dict[str, Any]:
        """Extract and validate download information from item details."""
        return {
            "item_id": item_details.get("id", ""),
            "title": item_details.get("title", "Unknown Title"),
            "artist": item_details.get("artist", "Unknown Artist"),
            "album": item_details.get(
                "album", item_details.get("type", "Unknown Album")
            ),
            "source": item_details.get("source", "qobuz"),
            "content_type": self._determine_content_type(item_details),
            "streaming_source": self._determine_streaming_source(item_details),
        }

    def _determine_content_type(self, item_details: dict) -> ContentType:
        """Determine content type from item details."""
        item_type = item_details.get("type", "").lower()

        if "album" in item_type:
            return ContentType.ALBUM
        if "playlist" in item_type:
            return ContentType.PLAYLIST
        if "artist" in item_type:
            return ContentType.ARTIST
        return ContentType.TRACK

    def _determine_streaming_source(self, item_details: dict) -> StreamingSource:
        """Determine streaming source from item details."""
        source = item_details.get("source", "qobuz").lower()

        source_mapping = {
            "tidal": StreamingSource.TIDAL,
            "deezer": StreamingSource.DEEZER,
            "youtube": StreamingSource.YOUTUBE,
        }

        return source_mapping.get(source, StreamingSource.QOBUZ)

    def _create_and_authenticate_provider(self, download_info: dict) -> Any:
        """Create and authenticate download provider."""
        # Get service credentials
        credentials = self._get_service_credentials(download_info["source"])

        # Create provider with credentials
        provider = self.create_download_provider(
            download_info["streaming_source"], credentials
        )

        # Authenticate using the current event loop
        auth_result = self._loop.run_until_complete(provider.authenticate())
        if not auth_result:
            msg = f"Failed to authenticate with {download_info['source']}"
            raise AuthenticationError(msg, source=download_info["source"])
        return provider

    def _get_service_credentials(self, source: str) -> dict[str, Any]:
        """Get service credentials from configuration."""
        service_config = self.config.get_service_config(source)

        # Use the service config's built-in method to get credentials
        return service_config.get_decoded_credentials()

    def _determine_download_directory(self, download_info: dict) -> str:
        """Determine download directory based on user settings."""
        base_folder = Path(self.config.downloads.folder)

        use_source_subdirs = getattr(
            self.config.downloads, "source_subdirectories", False
        )
        if use_source_subdirs:
            base_folder = base_folder / download_info["source"].upper()

        # Create directory if it doesn't exist
        base_folder.mkdir(parents=True, exist_ok=True)

        return str(base_folder)

    def _execute_download(
        self, provider: Any, download_info: dict, download_dir: str
    ) -> Any:
        """Execute the actual download."""
        return self._loop.run_until_complete(
            provider.download_content(
                content_id=download_info["item_id"],
                content_type=download_info["content_type"],
                download_directory=download_dir,
            )
        )

    def _handle_download_result(
        self, result: Any, download_info: dict, download_id: str
    ):
        """Handle download result and emit appropriate signals."""
        results = self._normalize_provider_results(result)
        retryable_failures = self._get_retryable_failures(results)

        # Retry loop up to configured limit
        if retryable_failures:
            retryable_failures = self._retry_failures(download_info, retryable_failures)

        overall_success = not retryable_failures
        if overall_success:
            message = f"Successfully downloaded {download_info['title']}"
            self.download_completed.emit(download_id, True, message)
        else:
            error_message = self._summarize_errors(results, retryable_failures)
            self.download_completed.emit(download_id, False, error_message)

    def _normalize_provider_results(self, result: Any) -> list[Any]:
        """Normalize provider result(s) into a list."""
        try:
            if hasattr(result, "download_results"):
                return list(result.download_results or [])
        except (AttributeError, TypeError) as e:
            logger.warning("Failed to normalize provider results: %s", e)
        return [result]

    def _get_retryable_failures(self, results: list[Any]) -> list[Any]:
        """Identify results that should be retried at the worker level."""
        retryable: list[Any] = []
        for r in results:
            try:
                success = getattr(r, "success", False)
                file_path = getattr(r, "file_path", None)
                file_exists = bool(file_path) and Path(str(file_path)).exists()
                if (not success) or (file_path and not file_exists):
                    if not success and not file_path:
                        logger.info("Retrying failed item without file_path")
                    elif file_path and not file_exists:
                        logger.info("Retrying missing file on disk: %s", file_path)
                    retryable.append(r)
            except (AttributeError, TypeError, OSError) as e:
                logger.warning("Error evaluating result for retry: %s", e)
                continue
        return retryable

    def _retry_failures(self, download_info: dict, failures: list[Any]) -> list[Any]:
        """Retry failures up to configured max attempts; return remaining failures."""
        attempt = 0
        retryable = failures
        while retryable and attempt <= self._max_track_retries:
            attempt += 1
            retryable = self._perform_retry_pass(download_info, retryable, attempt)
        return retryable

    def _perform_retry_pass(
        self, download_info: dict, current_failures: list[Any], attempt: int
    ) -> list[Any]:
        """Perform a single retry pass; return the subset that still fails."""
        remaining: list[Any] = []
        for failed in current_failures:
            try:
                retry_result = self._run_retry(download_info)
                retry_results = self._normalize_provider_results(retry_result)
                if not self._has_recovered_results(retry_results):
                    remaining.append(failed)
            except (OSError, RuntimeError, ValueError, AttributeError) as e:
                logger.warning("Retry attempt %d failed: %s", attempt, e)
                remaining.append(failed)
        return remaining

    def _run_retry(self, download_info: dict) -> Any:
        """Execute a retry by using an existing provider, creating one, or the fast path for tests."""
        provider = getattr(self, "_current_provider", None)
        download_dir = self._determine_download_directory(download_info)

        if self._loop is None and provider is None:
            return self._execute_download(None, download_info, download_dir)

        if provider is None:
            if not self._loop:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
            try:
                provider = self._create_and_authenticate_provider(download_info)
            except (AuthenticationError, OSError, RuntimeError, ValueError) as e:
                logger.warning("Retry provider setup failed: %s", e)
                return self._execute_download(None, download_info, download_dir)

        return self._execute_download(provider, download_info, download_dir)

    def _has_recovered_results(self, retry_results: list[Any]) -> bool:
        """Check if any result indicates success with a present file when provided."""
        for rr in retry_results:
            rr_success = getattr(rr, "success", False)
            rr_file = getattr(rr, "file_path", None)
            rr_exists = not rr_file or Path(str(rr_file)).exists()
            if rr_success and rr_exists:
                return True
        return False

    def _summarize_errors(self, results: list[Any], failures: list[Any]) -> str:
        """Build a concise error summary string for UI display."""
        if failures:
            parts = []
            for r in failures:
                msg = getattr(r, "error_message", None)
                parts.append(msg or "Download failed")
            return ", ".join(parts)
        if results:
            return (
                getattr(results[0], "error_message", "Download failed")
                or "Download failed"
            )
        return "Download failed"

    def _cleanup_session_manager(self):
        """Clean up the session manager."""
        if self.session_manager and self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(self.session_manager.close_all_sessions())
            except (asyncio.CancelledError, OSError, RuntimeError) as e:
                logger.warning("Failed to cleanup session manager: %s", e)

    def _cleanup_provider(self, provider):
        """Clean up the download provider."""
        if provider and self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(provider.cleanup())
            except (asyncio.CancelledError, OSError, RuntimeError) as e:
                logger.warning("Failed to cleanup provider: %s", e)

    def _cleanup(self):
        """Clean up resources when thread stops."""
        if self.session_manager and self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(self.session_manager.close_all_sessions())
            except (asyncio.CancelledError, OSError, RuntimeError) as e:
                logger.warning(
                    "Failed to cleanup session manager during thread shutdown: %s", e
                )
