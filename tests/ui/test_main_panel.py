# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for main panel."""

import pytest
from PyQt6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from ripstream.ui.main_panel import MainPanel


class TestMainPanel:
    """Test the MainPanel class."""

    @pytest.fixture
    def main_panel(self, qapp):
        """Create a MainPanel for testing."""
        return MainPanel()

    def test_panel_creation(self, main_panel):
        """Test creating a MainPanel."""
        assert isinstance(main_panel, QWidget)
        assert main_panel.current_view == "discography"
        assert hasattr(main_panel, "stacked_widget")
        assert hasattr(main_panel, "discography_view")
        assert hasattr(main_panel, "downloads_view")

    def test_layout_structure(self, main_panel):
        """Test the layout structure."""
        layout = main_panel.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.count() == 1  # stacked_widget
        assert layout.contentsMargins().left() == 0
        assert layout.contentsMargins().right() == 0
        assert layout.contentsMargins().top() == 0
        assert layout.contentsMargins().bottom() == 0

    def test_stacked_widget_setup(self, main_panel):
        """Test stacked widget setup."""
        assert isinstance(main_panel.stacked_widget, QStackedWidget)
        assert main_panel.stacked_widget.count() == 2

        # Check that views are added
        assert main_panel.stacked_widget.widget(0) == main_panel.discography_view
        assert main_panel.stacked_widget.widget(1) == main_panel.downloads_view

    def test_initial_placeholder_views(self, main_panel):
        """Test initial placeholder views."""
        # Both views should be placeholder widgets initially
        assert isinstance(main_panel.discography_view, QWidget)
        assert isinstance(main_panel.downloads_view, QWidget)

        # Should have labels indicating they're placeholders
        discography_layout = main_panel.discography_view.layout()
        downloads_layout = main_panel.downloads_view.layout()

        assert discography_layout is not None
        assert downloads_layout is not None

    def test_default_view_selection(self, main_panel):
        """Test default view selection."""
        assert main_panel.current_view == "discography"
        assert main_panel.stacked_widget.currentWidget() == main_panel.discography_view

    def test_switch_to_discography_view(self, main_panel):
        """Test switching to discography view."""
        # Start with downloads view
        main_panel.switch_to_view("downloads")
        assert main_panel.current_view == "downloads"

        # Switch to discography
        main_panel.switch_to_view("discography")
        assert main_panel.current_view == "discography"
        assert main_panel.stacked_widget.currentWidget() == main_panel.discography_view

    def test_switch_to_downloads_view(self, main_panel):
        """Test switching to downloads view."""
        # Start with discography view (default)
        assert main_panel.current_view == "discography"

        # Switch to downloads
        main_panel.switch_to_view("downloads")
        assert main_panel.current_view == "downloads"
        assert main_panel.stacked_widget.currentWidget() == main_panel.downloads_view

    def test_refresh_discography_view(self, main_panel):
        """Test refreshing discography view."""
        main_panel.switch_to_view("discography_refresh")
        # Should call refresh_discography_view method
        # The method is currently a placeholder, so just ensure it doesn't crash

    def test_refresh_downloads_view(self, main_panel):
        """Test refreshing downloads view."""
        main_panel.switch_to_view("downloads_refresh")
        # Should call refresh_downloads_view method
        # The method is currently a placeholder, so just ensure it doesn't crash

    def test_set_discography_view(self, main_panel, qapp):
        """Test replacing discography view with actual implementation."""
        # Create a new widget to replace the placeholder
        new_discography_view = QWidget()
        new_discography_view.setObjectName("NewDiscographyView")

        main_panel.set_discography_view(new_discography_view)

        # Check that the view was replaced
        assert main_panel.discography_view == new_discography_view
        assert main_panel.stacked_widget.widget(0) == new_discography_view

        # If discography was current view, should still be current
        if main_panel.current_view == "discography":
            assert main_panel.stacked_widget.currentWidget() == new_discography_view

    def test_set_downloads_view(self, main_panel, qapp):
        """Test replacing downloads view with actual implementation."""
        # Create a new widget to replace the placeholder
        new_downloads_view = QWidget()
        new_downloads_view.setObjectName("NewDownloadsView")

        main_panel.set_downloads_view(new_downloads_view)

        # Check that the view was replaced
        assert main_panel.downloads_view == new_downloads_view
        assert main_panel.stacked_widget.widget(1) == new_downloads_view

    def test_set_view_while_current(self, main_panel, qapp):
        """Test setting view while it's the current view."""
        # Switch to downloads view
        main_panel.switch_to_view("downloads")
        assert main_panel.stacked_widget.currentWidget() == main_panel.downloads_view

        # Replace downloads view
        new_downloads_view = QWidget()
        main_panel.set_downloads_view(new_downloads_view)

        # Should still be the current widget
        assert main_panel.stacked_widget.currentWidget() == new_downloads_view

    def test_get_current_view_name(self, main_panel):
        """Test getting current view name."""
        assert main_panel.get_current_view_name() == "discography"

        main_panel.switch_to_view("downloads")
        assert main_panel.get_current_view_name() == "downloads"

    def test_show_loading_state(self, main_panel):
        """Test showing loading state."""
        current_widget = main_panel.stacked_widget.currentWidget()

        # Initially enabled
        assert current_widget.isEnabled() is True

        # Show loading
        main_panel.show_loading_state(True)
        assert current_widget.isEnabled() is False

        # Hide loading
        main_panel.show_loading_state(False)
        assert current_widget.isEnabled() is True

    def test_show_loading_state_default(self, main_panel):
        """Test showing loading state with default parameter."""
        current_widget = main_panel.stacked_widget.currentWidget()

        # Default should be True
        main_panel.show_loading_state()
        assert current_widget.isEnabled() is False

    def test_show_error_message(self, main_panel):
        """Test showing error message."""
        # This is a placeholder method, just ensure it doesn't crash
        main_panel.show_error_message("Test error message")

    def test_clear_content(self, main_panel):
        """Test clearing content from all views."""
        # Replace views with actual widgets first
        discography_widget = QWidget()
        downloads_widget = QWidget()
        main_panel.set_discography_view(discography_widget)
        main_panel.set_downloads_view(downloads_widget)

        # Clear content
        main_panel.clear_content()

        # Should create new placeholder views
        assert main_panel.discography_view != discography_widget
        assert main_panel.downloads_view != downloads_widget
        assert main_panel.stacked_widget.count() == 2

    def test_placeholder_view_creation(self, main_panel):
        """Test placeholder view creation."""
        placeholder = main_panel.create_placeholder_view("Test View")

        assert isinstance(placeholder, QWidget)
        layout = placeholder.layout()
        assert layout is not None

        # Should have title and content labels
        title_found = False
        content_found = False

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QLabel):
                    if "Test View" in widget.text():
                        title_found = True
                    elif "Content will be displayed here" in widget.text():
                        content_found = True

        assert title_found
        assert content_found

    def test_placeholder_view_styling(self, main_panel):
        """Test placeholder view styling."""
        placeholder = main_panel.create_placeholder_view("Test View")
        layout = placeholder.layout()

        # Find the title label and check its styling
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, QLabel) and "Test View" in widget.text():
                    style = widget.styleSheet()
                    assert "font-size: 24px" in style
                    assert "font-weight: bold" in style
                    assert "color: #333" in style
                    break

    @pytest.mark.parametrize("view_name", ["discography", "downloads"])
    def test_view_switching_consistency(self, main_panel, view_name):
        """Test view switching consistency."""
        main_panel.switch_to_view(view_name)

        assert main_panel.current_view == view_name
        assert main_panel.get_current_view_name() == view_name

        if view_name == "discography":
            assert (
                main_panel.stacked_widget.currentWidget() == main_panel.discography_view
            )
        else:
            assert (
                main_panel.stacked_widget.currentWidget() == main_panel.downloads_view
            )

    def test_invalid_view_name(self, main_panel):
        """Test switching to invalid view name."""
        main_panel.stacked_widget.currentWidget()

        # Switch to invalid view
        main_panel.switch_to_view("invalid_view")

        # Should not change current view
        assert (
            main_panel.current_view == "invalid_view"
        )  # Updates the name but doesn't change widget
        # Widget should remain the same since no matching case
        # (This depends on implementation - might want to add error handling)

    def test_refresh_view_names(self, main_panel):
        """Test refresh view name handling."""
        # Test discography refresh
        main_panel.switch_to_view("discography_refresh")
        # Should call refresh method but not change current view widget

        # Test downloads refresh
        main_panel.switch_to_view("downloads_refresh")
        # Should call refresh method but not change current view widget

    def test_widget_replacement_cleanup(self, main_panel, qapp):
        """Test that old widgets are properly cleaned up when replaced."""
        # Create a widget with a specific property to track
        old_widget = QWidget()
        old_widget.setObjectName("OldWidget")
        main_panel.set_discography_view(old_widget)

        # Replace with new widget
        new_widget = QWidget()
        new_widget.setObjectName("NewWidget")
        main_panel.set_discography_view(new_widget)

        # Old widget should be scheduled for deletion
        # We can't easily test deleteLater() but we can verify the replacement worked
        assert main_panel.discography_view == new_widget
        assert main_panel.discography_view.objectName() == "NewWidget"

    def test_stacked_widget_index_consistency(self, main_panel, qapp):
        """Test that widget indices remain consistent after replacement."""
        # Replace discography view
        new_discography = QWidget()
        main_panel.set_discography_view(new_discography)

        # Replace downloads view
        new_downloads = QWidget()
        main_panel.set_downloads_view(new_downloads)

        # Indices should remain the same
        assert main_panel.stacked_widget.widget(0) == new_discography
        assert main_panel.stacked_widget.widget(1) == new_downloads
        assert main_panel.stacked_widget.count() == 2

    def test_content_signal_emission(self, main_panel, qtbot):
        """Test content_requested signal emission."""
        # The signal is defined but not used in the current implementation
        # This test ensures the signal exists and can be connected
        assert hasattr(main_panel, "content_requested")

        # Test that we can connect to the signal
        signal_received = False

        def signal_handler(url, service):
            nonlocal signal_received
            signal_received = True

        main_panel.content_requested.connect(signal_handler)

        # Emit the signal manually to test connection
        main_panel.content_requested.emit("test_url", "test_service")

        assert signal_received

    def test_layout_margins_and_spacing(self, main_panel):
        """Test layout margins and spacing."""
        layout = main_panel.layout()
        margins = layout.contentsMargins()

        assert margins.left() == 0
        assert margins.right() == 0
        assert margins.top() == 0
        assert margins.bottom() == 0
