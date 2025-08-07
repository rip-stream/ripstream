# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Main panel component with view switching between discography and downloads."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class MainPanel(QWidget):
    """Main panel that switches between different views."""

    content_requested = pyqtSignal(str, str)  # url, service

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_view = "discography"
        self.setup_ui()

    def setup_ui(self):
        """Set up the main panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget to hold different views
        self.stacked_widget = QStackedWidget()

        # Create placeholder views (will be replaced with actual implementations)
        self.discography_view = self.create_placeholder_view("Discography View")
        self.downloads_view = self.create_placeholder_view("Downloads History View")

        # Add views to stack
        self.stacked_widget.addWidget(self.discography_view)
        self.stacked_widget.addWidget(self.downloads_view)

        layout.addWidget(self.stacked_widget)

        # Set default view
        self.switch_to_view("discography")

    def create_placeholder_view(self, title: str) -> QWidget:
        """Create a placeholder view widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                margin: 20px;
            }
        """)

        # Placeholder content
        content_label = QLabel("Content will be displayed here")
        content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666;
                margin: 10px;
            }
        """)

        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(content_label)
        layout.addStretch()

        return widget

    def switch_to_view(self, view_name: str):
        """Switch to the specified view."""
        self.current_view = view_name

        if view_name == "discography":
            self.stacked_widget.setCurrentWidget(self.discography_view)
        elif view_name == "downloads":
            self.stacked_widget.setCurrentWidget(self.downloads_view)
        elif view_name == "discography_refresh":
            self.refresh_discography_view()
        elif view_name == "downloads_refresh":
            self.refresh_downloads_view()

    def refresh_discography_view(self):
        """Refresh the discography view."""
        # Placeholder for refresh logic

    def refresh_downloads_view(self):
        """Refresh the downloads view."""
        # Placeholder for refresh logic

    def set_discography_view(self, view_widget: QWidget):
        """Replace the placeholder discography view with actual implementation."""
        old_widget = self.discography_view
        self.discography_view = view_widget

        # Replace in stacked widget
        index = self.stacked_widget.indexOf(old_widget)
        self.stacked_widget.removeWidget(old_widget)
        self.stacked_widget.insertWidget(index, view_widget)
        old_widget.deleteLater()

        # Switch to new view if it was current
        if self.current_view == "discography":
            self.stacked_widget.setCurrentWidget(view_widget)

    def set_downloads_view(self, view_widget: QWidget):
        """Replace the placeholder downloads view with actual implementation."""
        old_widget = self.downloads_view
        self.downloads_view = view_widget

        # Replace in stacked widget
        index = self.stacked_widget.indexOf(old_widget)
        self.stacked_widget.removeWidget(old_widget)
        self.stacked_widget.insertWidget(index, view_widget)
        old_widget.deleteLater()

        # Switch to new view if it was current
        if self.current_view == "downloads":
            self.stacked_widget.setCurrentWidget(view_widget)

    def get_current_view_name(self) -> str:
        """Get the name of the current view."""
        return self.current_view

    def show_loading_state(self, loading: bool = True):
        """Show or hide loading state for current view."""
        # This could be enhanced to show a loading overlay
        current_widget = self.stacked_widget.currentWidget()
        current_widget.setEnabled(not loading)

    def show_error_message(self, message: str):
        """Show an error message in the current view."""
        # Placeholder for error display logic

    def clear_content(self):
        """Clear content from all views."""
        # This would clear the content from both views
        # For now, just reset to placeholder views
        self.discography_view = self.create_placeholder_view("Discography View")
        self.downloads_view = self.create_placeholder_view("Downloads History View")

        # Update stacked widget
        while self.stacked_widget.count() > 0:
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()

        self.stacked_widget.addWidget(self.discography_view)
        self.stacked_widget.addWidget(self.downloads_view)

        # Switch back to current view
        self.switch_to_view(self.current_view)
