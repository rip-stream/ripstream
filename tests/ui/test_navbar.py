# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for navigation bar."""

from unittest.mock import patch

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolBar,
    QWidget,
)

from ripstream.ui.navbar import NavigationBar, URLInputWidget


class TestURLInputWidget:
    """Test the URLInputWidget class."""

    @pytest.fixture
    def url_widget(self, qapp):
        """Create a URLInputWidget for testing."""
        with patch("ripstream.ui.navbar.qta") as mock_qta:
            mock_qta.icon.return_value = QIcon()
            return URLInputWidget()

    def test_widget_creation(self, url_widget):
        """Test creating a URLInputWidget."""
        assert isinstance(url_widget, QWidget)
        assert hasattr(url_widget, "url_input")
        assert hasattr(url_widget, "submit_button")
        assert hasattr(url_widget, "service_label")

    def test_layout_structure(self, url_widget):
        """Test the layout structure."""
        layout = url_widget.layout()
        assert isinstance(layout, QHBoxLayout)
        assert layout.count() == 4  # URL label, input, service label, button

    def test_url_input_properties(self, url_widget):
        """Test URL input field properties."""
        assert isinstance(url_widget.url_input, QLineEdit)
        placeholder = url_widget.url_input.placeholderText()
        assert "music url" in placeholder.lower()

    def test_submit_button_properties(self, url_widget):
        """Test submit button properties."""
        assert isinstance(url_widget.submit_button, QPushButton)
        assert url_widget.submit_button.text() == "Go"
        assert url_widget.submit_button.width() == 60

    def test_service_label_properties(self, url_widget):
        """Test service label properties."""
        assert isinstance(url_widget.service_label, QLabel)
        assert url_widget.service_label.text() == "Service: Unknown"

    @pytest.mark.parametrize(
        ("url", "expected_service"),
        [
            ("https://open.qobuz.com/album/123", "qobuz"),
            ("https://qobuz.com/album/456", "qobuz"),
            ("https://tidal.com/album/789", None),  # Not implemented
            ("https://example.com/test", None),
            ("", None),
            ("invalid-url", None),
        ],
    )
    def test_service_detection(self, url_widget, url, expected_service):
        """Test service detection from URLs."""
        detected = url_widget.detect_service(url)
        if expected_service:
            assert detected == expected_service
            assert "Service:" in url_widget.service_label.text()
        else:
            assert detected is None
            assert url_widget.service_label.text() == "Service: Unknown"

    def test_service_label_styling(self, url_widget):
        """Test service label styling changes."""
        # Test unknown service styling
        url_widget.detect_service("")
        style = url_widget.service_label.styleSheet()
        assert "color: #666" in style

        # Test detected service styling
        url_widget.detect_service("https://open.qobuz.com/album/123")
        style = url_widget.service_label.styleSheet()
        assert "color: #2196F3" in style
        assert "font-weight: bold" in style

    def test_submit_url_signal(self, url_widget, qtbot):
        """Test URL submission signal."""
        test_url = "https://open.qobuz.com/album/123"
        url_widget.url_input.setText(test_url)

        with qtbot.waitSignal(url_widget.url_submitted, timeout=1000) as blocker:
            url_widget.submit_url()

        assert blocker.args[0] == test_url
        assert blocker.args[1] == "qobuz"

    def test_submit_empty_url(self, url_widget, qtbot):
        """Test submitting empty URL doesn't emit signal."""
        url_widget.url_input.setText("")

        # Should not emit signal
        with (
            pytest.raises(qtbot.TimeoutError),
            qtbot.waitSignal(url_widget.url_submitted, timeout=100),
        ):
            url_widget.submit_url()

    def test_submit_unknown_service(self, url_widget, qtbot):
        """Test submitting URL with unknown service."""
        test_url = "https://example.com/test"
        url_widget.url_input.setText(test_url)

        with qtbot.waitSignal(url_widget.url_submitted, timeout=1000) as blocker:
            url_widget.submit_url()

        assert blocker.args[0] == test_url
        assert blocker.args[1] == "unknown"

    def test_return_key_submission(self, url_widget, qtbot):
        """Test URL submission via return key."""
        test_url = "https://open.qobuz.com/album/123"
        url_widget.url_input.setText(test_url)

        with qtbot.waitSignal(url_widget.url_submitted, timeout=1000) as blocker:
            qtbot.keyPress(url_widget.url_input, Qt.Key.Key_Return)

        assert blocker.args[0] == test_url

    def test_clear_input(self, url_widget):
        """Test clearing the input field."""
        url_widget.url_input.setText("https://open.qobuz.com/album/123")
        url_widget.detect_service("https://open.qobuz.com/album/123")

        url_widget.clear_input()

        assert url_widget.url_input.text() == ""
        assert url_widget.service_label.text() == "Service: Unknown"

    def test_text_change_triggers_detection(self, url_widget):
        """Test that text changes trigger service detection."""
        # Initially unknown
        assert url_widget.service_label.text() == "Service: Unknown"

        # Type URL
        url_widget.url_input.setText("https://open.qobuz.com/album/123")

        # Should detect service
        assert "Qobuz" in url_widget.service_label.text()


class TestNavigationBar:
    """Test the NavigationBar class."""

    @pytest.fixture
    def navbar(self, qapp):
        """Create a NavigationBar for testing."""
        with patch("ripstream.ui.navbar.qta") as mock_qta:
            mock_qta.icon.return_value = QIcon()
            return NavigationBar()

    def test_navbar_creation(self, navbar):
        """Test creating a NavigationBar."""
        assert isinstance(navbar, QToolBar)
        assert navbar.windowTitle() == "Navigation"
        assert navbar.objectName() == "NavigationBar"

    def test_toolbar_properties(self, navbar):
        """Test toolbar properties."""
        assert navbar.isMovable() is False
        assert navbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextBesideIcon

    def test_url_widget_integration(self, navbar):
        """Test URL widget integration."""
        assert hasattr(navbar, "url_widget")
        assert isinstance(navbar.url_widget, URLInputWidget)

    def test_view_toggle_actions(self, navbar):
        """Test view toggle actions."""
        assert hasattr(navbar, "discography_action")
        assert hasattr(navbar, "downloads_action")

        # Check initial state
        assert navbar.discography_action.isChecked() is True
        assert navbar.downloads_action.isChecked() is False

        # Check they're checkable
        assert navbar.discography_action.isCheckable() is True
        assert navbar.downloads_action.isCheckable() is True

    def test_refresh_action(self, navbar):
        """Test refresh action."""
        assert hasattr(navbar, "refresh_action")
        assert navbar.refresh_action.text() == "Refresh"

    def test_url_signal_forwarding(self, navbar, qtbot):
        """Test URL signal forwarding."""
        test_url = "https://open.qobuz.com/album/123"

        with qtbot.waitSignal(navbar.url_submitted, timeout=1000) as blocker:
            navbar.url_widget.url_submitted.emit(test_url, "qobuz")

        assert blocker.args == [test_url, "qobuz"]

    def test_switch_to_discography_view(self, navbar, qtbot):
        """Test switching to discography view."""
        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.switch_view("discography")

        assert blocker.args == ["discography"]
        assert navbar.discography_action.isChecked() is True
        assert navbar.downloads_action.isChecked() is False

    def test_switch_to_downloads_view(self, navbar, qtbot):
        """Test switching to downloads view."""
        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.switch_view("downloads")

        assert blocker.args == ["downloads"]
        assert navbar.discography_action.isChecked() is False
        assert navbar.downloads_action.isChecked() is True

    def test_discography_action_trigger(self, navbar, qtbot):
        """Test discography action trigger."""
        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.discography_action.trigger()

        assert blocker.args == ["discography"]

    def test_downloads_action_trigger(self, navbar, qtbot):
        """Test downloads action trigger."""
        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.downloads_action.trigger()

        assert blocker.args == ["downloads"]

    def test_refresh_current_view_discography(self, navbar, qtbot):
        """Test refreshing current view when discography is active."""
        navbar.switch_view("discography")

        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.refresh_current_view()

        assert blocker.args == ["discography_refresh"]

    def test_refresh_current_view_downloads(self, navbar, qtbot):
        """Test refreshing current view when downloads is active."""
        navbar.switch_view("downloads")

        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.refresh_current_view()

        assert blocker.args == ["downloads_refresh"]

    def test_refresh_action_trigger(self, navbar, qtbot):
        """Test refresh action trigger."""
        # Set to discography view first
        navbar.switch_view("discography")

        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.refresh_action.trigger()

        assert blocker.args == ["discography_refresh"]

    def test_loading_state(self, navbar):
        """Test loading state changes."""
        # Initially not loading
        assert navbar.url_widget.submit_button.isEnabled() is True
        assert navbar.url_widget.submit_button.text() == "Go"

        # Set loading state
        navbar.set_loading_state(True)
        assert navbar.url_widget.submit_button.isEnabled() is False
        assert navbar.url_widget.submit_button.text() == "Loading..."

        # Clear loading state
        navbar.set_loading_state(False)
        assert navbar.url_widget.submit_button.isEnabled() is True
        assert navbar.url_widget.submit_button.text() == "Go"

    def test_get_current_url(self, navbar):
        """Test getting current URL."""
        test_url = "https://open.qobuz.com/album/123"
        navbar.url_widget.url_input.setText(test_url)

        assert navbar.get_current_url() == test_url

    def test_set_url(self, navbar):
        """Test setting URL."""
        test_url = "https://open.qobuz.com/album/123"
        navbar.set_url(test_url)

        assert navbar.url_widget.url_input.text() == test_url
        # Should also trigger service detection
        assert "Qobuz" in navbar.url_widget.service_label.text()

    def test_toolbar_actions_order(self, navbar):
        """Test that toolbar actions are in correct order."""
        actions = navbar.actions()

        # Should have URL widget, separator, view actions, separator, refresh
        assert len(actions) >= 5

        # Check for separators
        separator_count = sum(1 for action in actions if action.isSeparator())
        assert separator_count >= 2

    def test_view_button_exclusivity(self, navbar):
        """Test that view buttons are mutually exclusive."""
        # Start with discography checked
        assert navbar.discography_action.isChecked() is True
        assert navbar.downloads_action.isChecked() is False

        # Switch to downloads
        navbar.switch_view("downloads")
        assert navbar.discography_action.isChecked() is False
        assert navbar.downloads_action.isChecked() is True

        # Switch back to discography
        navbar.switch_view("discography")
        assert navbar.discography_action.isChecked() is True
        assert navbar.downloads_action.isChecked() is False

    @pytest.mark.parametrize("view_name", ["discography", "downloads"])
    def test_view_switching_consistency(self, navbar, qtbot, view_name):
        """Test view switching consistency."""
        with qtbot.waitSignal(navbar.view_changed, timeout=1000) as blocker:
            navbar.switch_view(view_name)

        assert blocker.args == [view_name]

        if view_name == "discography":
            assert navbar.discography_action.isChecked() is True
            assert navbar.downloads_action.isChecked() is False
        else:
            assert navbar.discography_action.isChecked() is False
            assert navbar.downloads_action.isChecked() is True

    def test_empty_url_handling(self, navbar):
        """Test handling of empty URLs."""
        navbar.set_url("")
        assert navbar.get_current_url() == ""
        assert navbar.url_widget.service_label.text() == "Service: Unknown"

    def test_whitespace_url_handling(self, navbar):
        """Test handling of URLs with whitespace."""
        navbar.set_url("  https://open.qobuz.com/album/123  ")
        # get_current_url should strip whitespace
        assert navbar.get_current_url() == "https://open.qobuz.com/album/123"
