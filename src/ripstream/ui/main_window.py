# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Main application window for ripstream."""

import logging
import sys

from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
)

from ripstream.config.user import UserConfig
from ripstream.core.url_parser import URLParser, parse_music_url
from ripstream.ui.config_manager import ConfigManager
from ripstream.ui.download_handler import DownloadHandler
from ripstream.ui.metadata_service import MetadataService
from ripstream.ui.preferences import PreferencesDialog
from ripstream.ui.resources import get_application_icon
from ripstream.ui.ui_manager import UIManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Initialize managers
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()

        # Initialize URL parser and metadata service
        self.url_parser = URLParser()
        self.metadata_service = MetadataService(self.config)
        self._connect_metadata_signals()

        # Setup UI
        self.setWindowTitle("Ripstream - Music Downloader")
        self.setGeometry(100, 100, 1200, 800)

        # Set window icon
        self.setWindowIcon(get_application_icon())

        # Initialize UI manager
        self.ui_manager = UIManager(self, self.config, self.config_manager)
        self.ui_manager.setup_ui()

        # Initialize download handler
        self.download_handler = DownloadHandler(
            self.config,
            self.ui_manager.get_downloads_view(),
            self.ui_manager.status_label,
        )

        # Connect UI signals to handlers
        self._connect_ui_signals()

        # Setup menus and restore geometry
        self.setup_menus()
        self.ui_manager.restore_geometry()

    def _connect_metadata_signals(self):
        """Connect metadata service signals to handlers."""
        self.metadata_service.metadata_ready.connect(self.handle_metadata_ready)
        self.metadata_service.album_ready.connect(self.handle_album_ready)
        self.metadata_service.artwork_ready.connect(self.handle_artwork_ready)
        self.metadata_service.progress_updated.connect(self.handle_metadata_progress)
        self.metadata_service.artist_progress_updated.connect(
            self.handle_artist_progress
        )
        self.metadata_service.error_occurred.connect(self.handle_metadata_error)

    def _connect_ui_signals(self):
        """Connect UI component signals to their respective handlers."""
        self._connect_navbar_signals()
        self._connect_discography_signals()
        self._connect_downloads_signals()
        self._connect_download_handler_signals()
        self._setup_main_panel_views()

        # After all signals are connected, emit the downloaded albums signal
        # to update the discography view with current download status
        downloads_view = self.ui_manager.get_downloads_view()
        if downloads_view:
            downloads_view.emit_downloaded_albums_signal()

    def _connect_download_handler_signals(self):
        """Connect download handler signals to handlers."""
        if self.download_handler:
            # Connect download handler's downloaded_albums_updated signal to discography view
            discography_view = self.ui_manager.get_discography_view()
            if discography_view:
                self.download_handler.downloaded_albums_updated.connect(
                    discography_view.update_downloaded_albums
                )

    def _connect_navbar_signals(self):
        """Connect navigation bar signals to handlers."""
        navbar = self.ui_manager.get_navbar()
        if navbar:
            navbar.url_submitted.connect(self.handle_url_submission)
            navbar.view_changed.connect(self.handle_view_change)

    def _connect_discography_signals(self):
        """Connect discography view signals to handlers."""
        discography_view = self.ui_manager.get_discography_view()
        if discography_view:
            discography_view.item_selected.connect(self.handle_item_selection)
            discography_view.download_requested.connect(self.handle_download_request)
            # Listen for lazy album details requests from list view
            if hasattr(discography_view, "list_view") and discography_view.list_view:
                discography_view.list_view.album_details_requested.connect(
                    self.handle_album_details_request
                )

    def _connect_downloads_signals(self):
        """Connect downloads view signals to handlers."""
        downloads_view = self.ui_manager.get_downloads_view()
        if downloads_view:
            downloads_view.retry_download.connect(self.handle_retry_download)
            downloads_view.remove_download.connect(self.handle_remove_download)
            downloads_view.clear_all_downloads.connect(self.handle_clear_all_downloads)
            downloads_view.downloaded_albums_updated.connect(
                self.handle_downloaded_albums_updated
            )

    def _setup_main_panel_views(self):
        """Configure the main panel with the appropriate view components."""
        main_panel = self.ui_manager.main_panel
        discography_view = self.ui_manager.get_discography_view()
        downloads_view = self.ui_manager.get_downloads_view()

        main_panel.set_discography_view(discography_view)
        main_panel.set_downloads_view(downloads_view)

    def setup_menus(self):
        """Set up the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        preferences_action = QAction("&Preferences...", self)
        preferences_action.setShortcut(QKeySequence.StandardKey.Preferences)
        preferences_action.setStatusTip("Open application preferences")
        preferences_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("About Ripstream")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def load_config(self):
        """Load application configuration."""
        self.config = self.config_manager.load_config()

    def save_config(self):
        """Save application configuration."""
        self.config_manager.save_config()

    def show_preferences(self):
        """Show the preferences dialog."""
        dialog = PreferencesDialog(self.config, self)
        dialog.config_changed.connect(self.on_config_changed)

        if dialog.exec() == PreferencesDialog.DialogCode.Accepted:
            self.ui_manager.update_status("Preferences saved")
        else:
            self.ui_manager.update_status("Preferences cancelled")

    def on_config_changed(self, new_config: UserConfig):
        """Handle configuration changes."""
        self.config = new_config
        self.config_manager.update_config(new_config)

        # Update metadata service with new config
        if hasattr(self, "metadata_service"):
            self.metadata_service.update_config(new_config)

        self.ui_manager.update_status("Configuration updated")

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Ripstream",
            "Ripstream - Music Downloader\n\n"
            "A modern music downloading application supporting multiple streaming services.\n\n"
            "Copyright (c) 2025 ripstream and contributors.\n"
            "Licensed under the MIT license.",
        )

    def closeEvent(self, a0: QCloseEvent):  # noqa: N802
        """Handle window close event."""
        # Clean up metadata service and any running fetchers
        if hasattr(self, "metadata_service"):
            self.metadata_service.cleanup()
            # Also cleanup any running fetcher
            if (
                hasattr(self.metadata_service, "current_fetcher")
                and self.metadata_service.current_fetcher
                and self.metadata_service.current_fetcher.isRunning()
            ):
                self.metadata_service.current_fetcher.terminate()
                self.metadata_service.current_fetcher.wait(1000)  # Wait up to 1 second

        # Cleanup download handler
        if hasattr(self, "download_handler"):
            self.download_handler.cleanup()

        # Save window geometry
        self.ui_manager.save_geometry()

        a0.accept()

    def handle_url_submission(self, url: str, _detected_service: str):
        """Handle URL submission from the navigation bar."""
        self.ui_manager.update_status(f"Processing URL: {url}")
        self.ui_manager.set_loading_state(True)

        try:
            # Parse the URL
            parsed_result = parse_music_url(url)

            if not parsed_result.is_valid:
                error_msg = parsed_result.metadata.get("error", "Invalid URL")
                self.ui_manager.update_status(f"Error: {error_msg}")
                self.ui_manager.set_loading_state(False)
                return

            # Update status
            service_name = parsed_result.service.value.replace("_", " ").title()
            content_type = parsed_result.content_type.value.title()
            self.ui_manager.update_status(
                f"Found {content_type} from {service_name}: {parsed_result.content_id}"
            )

            # Switch to discography view to show results
            self.ui_manager.switch_to_view("discography")

            # Clear existing content
            discography_view = self.ui_manager.get_discography_view()
            if discography_view:
                discography_view.clear_all()

            # Start fetching metadata with artist filter preference from navbar
            navbar = self.ui_manager.get_navbar()
            artist_filter = None
            if navbar and hasattr(navbar, "url_widget"):
                artist_filter = navbar.url_widget.get_artist_filter()

            self.metadata_service.fetch_metadata(
                parsed_result, artist_item_filter=artist_filter
            )

        except (ValueError, AttributeError, RuntimeError) as e:
            self.ui_manager.update_status(f"Error processing URL: {e!s}")
            self.ui_manager.set_loading_state(False)

    def handle_view_change(self, view_name: str):
        """Handle view changes from the navigation bar."""
        if view_name.endswith("_refresh"):
            view_name = view_name.replace("_refresh", "")
            self.ui_manager.update_status(f"Refreshing {view_name} view...")
        else:
            self.ui_manager.update_status(f"Switched to {view_name} view")

        self.ui_manager.switch_to_view(view_name)

    def handle_item_selection(self, item_id: str):
        """Handle item selection in discography view."""
        self.ui_manager.update_status(f"Selected item: {item_id}")

    def handle_album_details_request(self, album_id: str):
        """Fetch full album details lazily when an album row is selected in the list view."""
        self.ui_manager.update_status(f"Loading album details: {album_id}")

        # Build a ParsedURL-like object to reuse metadata service
        from ripstream.core.url_parser import ParsedURL
        from ripstream.downloader.enums import ContentType
        from ripstream.models.enums import StreamingSource

        # Determine current service from last parsed URL if available, fallback to qobuz
        service = StreamingSource.QOBUZ
        if (
            hasattr(self, "metadata_service")
            and self.metadata_service.current_fetcher
            and hasattr(self.metadata_service.current_fetcher, "parsed_url")
        ):
            service = self.metadata_service.current_fetcher.parsed_url.service

        parsed = ParsedURL(
            service=service,
            content_type=ContentType.ALBUM,
            content_id=album_id,
            url=f"{service.value}://album/{album_id}",
            metadata={},
        )

        # Fire a one-off metadata fetch for album details; UI will merge on metadata_ready
        self.metadata_service.fetch_metadata(parsed)

    def handle_download_request(self, item_details: dict):
        """Handle download request for an item."""
        # Check if this is an album download from the grid view
        if item_details.get("type") == "Album":
            # Get tracks for this album from the discography list view
            album_id = item_details.get("id")
            if album_id:
                tracks = self._get_album_tracks(album_id)
                if tracks:
                    # Queue each track individually
                    for track in tracks:
                        self.download_handler.handle_download_request(track)
                    return

        # Handle as single item (track or fallback)
        self.download_handler.handle_download_request(item_details)

    def _get_album_tracks(self, album_id: str) -> list[dict]:
        """Get tracks for an album from the discography list view."""
        discography_view = self.ui_manager.get_discography_view()
        if discography_view and discography_view.list_view:
            # Use the new method to get tracks by album ID
            return discography_view.list_view.get_tracks_by_album_id(album_id)

        return []

    def handle_retry_download(self, download_id: str):
        """Handle retry download request."""
        try:
            # Get the original download details from the database
            download_service = self.ui_manager.get_downloads_view().download_service
            download_record = download_service.get_download_by_id(download_id)

            if download_record:
                # Create item details from the download record with fallback values
                item_details = {
                    "id": download_record.get("source_id", ""),
                    "title": download_record.get("title", "Unknown Title"),
                    "artist": download_record.get("artist", "Unknown Artist"),
                    "album": download_record.get("album", "Unknown Album"),
                    "source": download_record.get("source", "qobuz"),
                    "type": download_record.get("type", "track").lower(),
                }

                # Update status
                self.ui_manager.update_status(
                    f"Retrying download: {download_record['title']}"
                )

                # Trigger the download through the download handler with the existing download ID
                self.download_handler.handle_download_request(item_details, download_id)
            else:
                self.ui_manager.update_status(
                    f"Download record not found: {download_id}"
                )

        except (ValueError, AttributeError, RuntimeError, KeyError) as e:
            self.ui_manager.update_status(f"Failed to retry download: {e!s}")

    def handle_remove_download(self, download_id: str):
        """Handle remove download request."""
        # The downloads view has already removed the download from the database
        # Just update the status message
        self.ui_manager.update_status(f"Removed download: {download_id}")

    def handle_clear_all_downloads(self):
        """Handle clear all downloads request."""
        # The downloads view has already cleared all downloads from the database
        # Just update the status message
        self.ui_manager.update_status("Cleared all downloads")

    def handle_downloaded_albums_updated(self, downloaded_albums: set):
        """Handle updated list of downloaded albums."""
        # Update the discography view with downloaded albums info
        discography_view = self.ui_manager.get_discography_view()
        if discography_view:
            discography_view.update_downloaded_albums(downloaded_albums)

    def handle_metadata_ready(self, metadata: dict):
        """Handle metadata fetched from streaming service."""
        try:
            # Use the new set_content method to handle different content types properly
            self.ui_manager.main_panel.discography_view.set_content(metadata)

            # Update status message
            items = metadata.get("items", [])
            content_type = metadata.get("content_type", "content")
            service = metadata.get("service", "streaming service")

            # Handle album metadata with track listings
            if content_type == "album" and "album_info" in metadata:
                album_info = metadata["album_info"]
                self.ui_manager.update_status(
                    f"Loaded album '{album_info['title']}' by {album_info['artist']} "
                    f"with {len(items)} tracks from {service}"
                )
            elif content_type == "artist" and "artist_info" in metadata:
                msg = f"Loaded {metadata['artist_info']['total_items']} items by '{metadata['artist_info']['name']}' from {service}"
                self.ui_manager.update_status(msg)
            else:
                self.ui_manager.update_status(
                    f"Loaded {len(items)} {content_type}(s) from {service}"
                )

        except (ValueError, AttributeError, RuntimeError) as e:
            self.ui_manager.update_status(f"Error processing metadata: {e!s}")
        finally:
            self.ui_manager.set_loading_state(False)

    def handle_album_ready(self, album_metadata: dict):
        """Handle individual album fetched during streaming."""
        try:
            # Add the album progressively to the discography view
            discography_view = self.ui_manager.get_discography_view()
            if discography_view:
                discography_view.add_album_progressively(album_metadata)

            # Update status to show progress
            album_info = album_metadata.get("album_info", {})
            if album_info:
                album_title = album_info.get("title", "Unknown Album")
                self.ui_manager.update_status(f"Loaded album: {album_title}")

        except Exception:
            logger.exception("Failed to handle album ready")

    def handle_artwork_ready(self, item_id: str, pixmap):
        """Handle artwork fetched for an item."""
        logger.info(
            "Received artwork for item %s, pixmap size: %s", item_id, pixmap.size()
        )
        # Update the artwork in the discography view that's actually displayed
        discography_view = self.ui_manager.get_discography_view()
        if discography_view:
            discography_view.update_item_artwork(item_id, pixmap)

    def handle_metadata_progress(self, progress: int, message: str):
        """Handle metadata fetching progress updates."""
        self.ui_manager.update_status(f"{message} ({progress}%)")

    def handle_artist_progress(
        self, remaining_items: int, total_items: int, service: str
    ):
        """Handle artist album fetching progress updates."""
        if remaining_items > 0:
            completed_items = total_items - remaining_items
            self.ui_manager.update_status(
                f"Loading artist albums - {completed_items}/{total_items} completed, {remaining_items} remaining from {service}"
            )
        else:
            self.ui_manager.update_status(
                f"Completed loading {total_items} albums from {service}"
            )

    def handle_metadata_error(self, error_message: str):
        """Handle metadata fetching errors."""
        self.ui_manager.update_status(f"Error: {error_message}")
        self.ui_manager.set_loading_state(False)


def main():
    """Execute application."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("ripstream.log"),
        ],
    )

    # Set application name before creating QApplication
    import os

    if hasattr(os, "environ"):
        os.environ["QT_MAC_WANTS_LAYER"] = "1"

    # On macOS, set the application name in argv[0] to influence menu bar name
    if sys.platform == "darwin" and len(sys.argv) > 0:
        sys.argv[0] = "Ripstream"

    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Ripstream")
    app.setApplicationDisplayName("Ripstream")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ripstream")
    app.setOrganizationDomain("ripstream.app")

    # Set application icon
    app.setWindowIcon(get_application_icon())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
