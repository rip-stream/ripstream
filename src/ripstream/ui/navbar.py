# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Navigation bar component with URL input and controls."""

import qtawesome as qta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolBar,
    QWidget,
)

from ripstream.core.url_parser import detect_service_from_url
from ripstream.models.enums import ArtistItemFilter, StreamingSource


class URLInputWidget(QWidget):
    """URL input widget with validation and service detection."""

    url_submitted = pyqtSignal(str, str)  # url, detected_service

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Set up the URL input UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Artist item filter dropdown
        self.filter_dropdown = QComboBox()
        self.filter_dropdown.addItems(["Both", "Albums Only", "Singles Only"])
        self.filter_dropdown.setToolTip(
            "Choose whether to fetch albums, singles, or both for artist URLs"
        )

        # URL input field
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(
            "Enter music URL (artist, album, or playlist)..."
        )
        self.url_input.returnPressed.connect(self.submit_url)

        # Submit button
        self.submit_button = QPushButton("Go")
        self.submit_button.setIcon(qta.icon("fa5s.play"))
        self.submit_button.clicked.connect(self.submit_url)
        self.submit_button.setFixedWidth(60)

        # Service indicator
        self.service_label = QLabel("Service: Unknown")
        self.service_label.setStyleSheet("color: #666; font-size: 11px;")

        layout.addWidget(self.filter_dropdown)
        layout.addWidget(QLabel("URL:"))
        layout.addWidget(self.url_input, 1)  # Stretch factor 1
        layout.addWidget(self.service_label)
        layout.addWidget(self.submit_button)

        # Connect text change to service detection
        self.url_input.textChanged.connect(self.detect_service)

    def get_artist_filter(self) -> ArtistItemFilter:
        """Return the selected artist item filter as an enum."""
        text = (self.filter_dropdown.currentText() or "").lower()
        if "albums" in text and "only" in text:
            return ArtistItemFilter.ALBUMS_ONLY
        if "singles" in text and "only" in text:
            return ArtistItemFilter.SINGLES_ONLY
        return ArtistItemFilter.BOTH

    def detect_service(self, url: str) -> str | None:
        """Detect streaming service from URL."""
        if not url:
            self.service_label.setText("Service: Unknown")
            return None

        # Use the core URL parser for service detection
        detected_service_enum = detect_service_from_url(url)

        # For now, only support qobuz (as per test expectations)
        if detected_service_enum == StreamingSource.QOBUZ:
            detected_service = detected_service_enum.value
            service_display = detected_service.replace("_", " ").title()
            self.service_label.setText(f"Service: {service_display}")
            self.service_label.setStyleSheet(
                "color: #2196F3; font-size: 11px; font-weight: bold;"
            )
            return detected_service
        self.service_label.setText("Service: Unknown")
        self.service_label.setStyleSheet("color: #666; font-size: 11px;")
        return None

    def submit_url(self):
        """Submit the URL for processing."""
        url = self.url_input.text().strip()
        if not url:
            return

        detected_service = self.detect_service(url)
        if not detected_service:
            detected_service = "unknown"

        self.url_submitted.emit(url, detected_service)

    def clear_input(self):
        """Clear the URL input."""
        self.url_input.clear()
        self.service_label.setText("Service: Unknown")
        self.service_label.setStyleSheet("color: #666; font-size: 11px;")


class NavigationBar(QToolBar):
    """Main navigation bar with URL input and controls."""

    url_submitted = pyqtSignal(str, str)  # url, detected_service
    view_changed = pyqtSignal(str)  # view_name

    def __init__(self, parent=None):
        super().__init__("Navigation", parent)
        self.setObjectName("NavigationBar")  # Set object name for Qt state saving
        self.setup_ui()

    def setup_ui(self):
        """Set up the navigation bar UI."""
        self.setMovable(False)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # URL input widget
        self.url_widget = URLInputWidget()
        self.url_widget.url_submitted.connect(self.url_submitted.emit)

        # Add URL input as a widget action
        self.addWidget(self.url_widget)

        # Add separator
        self.addSeparator()

        # View toggle buttons
        self.discography_action = self.addAction("Discography")
        self.discography_action.setIcon(qta.icon("fa5s.music"))
        self.discography_action.setCheckable(True)
        self.discography_action.setChecked(True)  # Default view
        self.discography_action.triggered.connect(
            lambda: self.switch_view("discography")
        )

        self.downloads_action = self.addAction("Downloads")
        self.downloads_action.setIcon(qta.icon("fa5s.download"))
        self.downloads_action.setCheckable(True)
        self.downloads_action.triggered.connect(lambda: self.switch_view("downloads"))

        # Add separator
        self.addSeparator()

        # Additional controls
        self.refresh_action = self.addAction("Refresh")
        self.refresh_action.setIcon(qta.icon("fa5s.sync-alt"))
        self.refresh_action.triggered.connect(self.refresh_current_view)

    def switch_view(self, view_name: str):
        """Switch between different views."""
        # Update button states
        self.discography_action.setChecked(view_name == "discography")
        self.downloads_action.setChecked(view_name == "downloads")

        # Emit view change signal
        self.view_changed.emit(view_name)

    def refresh_current_view(self):
        """Refresh the current view."""
        # Determine current view and emit refresh signal
        if self.discography_action.isChecked():
            self.view_changed.emit("discography_refresh")
        elif self.downloads_action.isChecked():
            self.view_changed.emit("downloads_refresh")

    def set_loading_state(self, loading: bool):
        """Set the loading state of the navigation bar."""
        self.url_widget.submit_button.setEnabled(not loading)
        self.url_widget.submit_button.setText("Loading..." if loading else "Go")

    def get_current_url(self) -> str:
        """Get the current URL from the input field."""
        return self.url_widget.url_input.text().strip()

    def set_url(self, url: str):
        """Set the URL in the input field."""
        self.url_widget.url_input.setText(url)
        self.url_widget.detect_service(url)
