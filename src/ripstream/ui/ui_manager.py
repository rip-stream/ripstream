# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""UI manager for handling UI operations and state management."""

import logging
from typing import Any

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QLabel, QMainWindow

from ripstream.ui.discography.view import DiscographyView
from ripstream.ui.downloads_view import DownloadsHistoryView
from ripstream.ui.main_panel import MainPanel
from ripstream.ui.navbar import NavigationBar

logger = logging.getLogger(__name__)


class UIManager:
    """Manages UI components and their interactions."""

    def __init__(self, main_window: QMainWindow, config: Any, config_manager: Any):
        self.main_window = main_window
        self.config = config
        self.config_manager = config_manager
        self.settings = QSettings("ripstream", "ripstream")

        # UI components
        self.navbar: NavigationBar | None = None
        self.main_panel: MainPanel | None = None
        self.discography_view: DiscographyView | None = None
        self.downloads_view: DownloadsHistoryView | None = None
        self.status_label: QLabel | None = None

    def setup_ui(self):
        """Set up all UI components."""
        self._setup_navbar()
        self._setup_main_panel()
        self._setup_status_bar()
        self._connect_signals()

    def _setup_navbar(self):
        """Set up the navigation bar."""
        self.navbar = NavigationBar()
        self.main_window.addToolBar(self.navbar)

    def _setup_main_panel(self):
        """Set up the main panel with views."""
        self.main_panel = MainPanel()
        self.main_window.setCentralWidget(self.main_panel)

        # Create specific views
        self.discography_view = DiscographyView()
        self.downloads_view = DownloadsHistoryView(config=self.config)

    def _setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = self.main_window.statusBar()
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Add config status
        config_path = (
            self.config_manager.config_path
            if hasattr(self.config_manager, "config_path")
            else "Unknown"
        )
        config_status = QLabel(f"Config: {config_path}")
        self.status_bar.addPermanentWidget(config_status)

    def _connect_signals(self):
        """Connect UI component signals."""
        if self.navbar:
            self.navbar.url_submitted.connect(self._handle_url_submission)
            self.navbar.view_changed.connect(self._handle_view_change)

        if self.discography_view:
            self.discography_view.item_selected.connect(self._handle_item_selection)
            self.discography_view.download_requested.connect(
                self._handle_download_request
            )

        if self.downloads_view:
            self.downloads_view.retry_download.connect(self._handle_retry_download)
            self.downloads_view.remove_download.connect(self._handle_remove_download)
            self.downloads_view.clear_all_downloads.connect(
                self._handle_clear_all_downloads
            )
            # Connect downloaded albums updates to discography view
            if self.discography_view:
                self.downloads_view.downloaded_albums_updated.connect(
                    self.discography_view.update_downloaded_albums
                )

    def _handle_url_submission(self, url: str, detected_service: str):
        """Handle URL submission from navbar."""
        logger.info("URL submitted: %s (service: %s)", url, detected_service)
        # This will be handled by the main window

    def _handle_view_change(self, view_name: str):
        """Handle view change from navbar."""
        logger.info("View changed to: %s", view_name)
        # This will be handled by the main window

    def _handle_item_selection(self, item_id: str):
        """Handle item selection in discography view."""
        logger.info("Item selected: %s", item_id)
        # This will be handled by the main window

    def _handle_download_request(self, item_details: dict):
        """Handle download request from discography view."""
        logger.info("Download requested for item: %s", item_details.get("id", ""))
        # This will be handled by the main window

    def _handle_retry_download(self, download_id: str):
        """Handle retry download request."""
        logger.info("Retry download requested for: %s", download_id)
        # This will be handled by the main window

    def _handle_remove_download(self, download_id: str):
        """Handle remove download request."""
        logger.info("Remove download requested for: %s", download_id)
        # This will be handled by the main window

    def _handle_clear_all_downloads(self):
        """Handle clear all downloads request."""
        logger.info("Clear all downloads requested")
        # This will be handled by the main window

    def update_status(self, message: str):
        """Update the status bar message."""
        if self.status_label:
            self.status_label.setText(message)

    def switch_to_view(self, view_name: str):
        """Switch to a specific view."""
        if self.main_panel:
            self.main_panel.switch_to_view(view_name)

    def set_loading_state(self, loading: bool):
        """Set the loading state of the navbar."""
        if self.navbar:
            self.navbar.set_loading_state(loading)

    def restore_geometry(self):
        """Restore window geometry from settings."""
        geometry = self.settings.value("geometry")
        if geometry:
            self.main_window.restoreGeometry(geometry)

        window_state = self.settings.value("windowState")
        if window_state:
            self.main_window.restoreState(window_state)

    def save_geometry(self):
        """Save window geometry to settings."""
        self.settings.setValue("geometry", self.main_window.saveGeometry())
        self.settings.setValue("windowState", self.main_window.saveState())

    def get_discography_view(self) -> DiscographyView | None:
        """Get the discography view."""
        return self.discography_view

    def get_downloads_view(self) -> DownloadsHistoryView | None:
        """Get the downloads view."""
        return self.downloads_view

    def get_navbar(self) -> NavigationBar | None:
        """Get the navigation bar."""
        return self.navbar
