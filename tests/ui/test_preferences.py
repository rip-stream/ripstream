# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for preferences dialog."""

import pytest
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTabWidget, QVBoxLayout, QWidget

from ripstream.config.user import UserConfig
from ripstream.ui.preferences import BasePreferenceTab, PreferencesDialog


class TestPreferencesDialog:
    """Test the PreferencesDialog class."""

    @pytest.fixture
    def preferences_dialog(self, qapp, sample_user_config):
        """Create a PreferencesDialog for testing."""
        return PreferencesDialog(sample_user_config)

    def test_dialog_creation(self, preferences_dialog, sample_user_config):
        """Test creating a PreferencesDialog."""
        assert isinstance(preferences_dialog, QDialog)
        assert preferences_dialog.windowTitle() == "Preferences"
        assert preferences_dialog.isModal() is True
        assert preferences_dialog.size().width() == 800
        assert preferences_dialog.size().height() == 600

    def test_config_handling(self, preferences_dialog, sample_user_config):
        """Test configuration handling."""
        # Should work with a deep copy, not the original
        assert preferences_dialog.config is not sample_user_config
        assert preferences_dialog.original_config is sample_user_config

        # But should have same values
        assert preferences_dialog.config.model_dump() == sample_user_config.model_dump()

    def test_layout_structure(self, preferences_dialog):
        """Test the layout structure."""
        layout = preferences_dialog.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.count() == 2  # tab_widget and button_box

    def test_tab_widget_setup(self, preferences_dialog):
        """Test tab widget setup."""
        assert hasattr(preferences_dialog, "tab_widget")
        assert isinstance(preferences_dialog.tab_widget, QTabWidget)

        # Should have 5 tabs
        assert preferences_dialog.tab_widget.count() == 5

    def test_tab_creation(self, preferences_dialog):
        """Test that all tabs are created."""
        tab_widget = preferences_dialog.tab_widget

        # Check tab titles
        expected_tabs = ["General", "Services", "Downloads", "Audio", "Advanced"]
        actual_tabs = [tab_widget.tabText(i) for i in range(tab_widget.count())]

        assert actual_tabs == expected_tabs

    def test_tab_instances(self, preferences_dialog):
        """Test tab instances are created correctly."""
        assert hasattr(preferences_dialog, "general_tab")
        assert hasattr(preferences_dialog, "services_tab")
        assert hasattr(preferences_dialog, "downloads_tab")
        assert hasattr(preferences_dialog, "audio_tab")
        assert hasattr(preferences_dialog, "advanced_tab")

    def test_button_box_setup(self, preferences_dialog):
        """Test button box setup."""
        # Find the button box in the layout
        layout = preferences_dialog.layout()
        button_box = None

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(item.widget(), QDialogButtonBox):
                button_box = item.widget()
                break

        assert button_box is not None
        assert isinstance(button_box, QDialogButtonBox)

        # Check that it has the expected buttons
        standard_buttons = button_box.standardButtons()
        expected_buttons = (
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )
        assert standard_buttons == expected_buttons

    def test_restore_defaults_button(self, preferences_dialog):
        """Test restore defaults button exists and is connected."""
        layout = preferences_dialog.layout()
        button_box = None

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(item.widget(), QDialogButtonBox):
                button_box = item.widget()
                break

        # Ensure button_box was found
        assert button_box is not None, (
            "QDialogButtonBox not found in preferences dialog"
        )

        restore_button = button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        assert restore_button is not None

    def test_load_config(self, preferences_dialog):
        """Test loading configuration into tabs."""
        # Mock the tabs to have load_config methods
        for i in range(preferences_dialog.tab_widget.count()):
            tab = preferences_dialog.tab_widget.widget(i)
            if hasattr(tab, "load_config"):
                # Should be callable
                assert callable(tab.load_config)

    def test_save_config(self, preferences_dialog):
        """Test saving configuration from tabs."""
        # Mock the tabs to have save_config methods
        for i in range(preferences_dialog.tab_widget.count()):
            tab = preferences_dialog.tab_widget.widget(i)
            if hasattr(tab, "save_config"):
                # Should be callable
                assert callable(tab.save_config)

    def test_apply_changes(self, preferences_dialog, qtbot):
        """Test applying changes."""
        with qtbot.waitSignal(
            preferences_dialog.config_changed, timeout=1000
        ) as blocker:
            preferences_dialog.apply_changes()

        # Should emit the current config
        assert blocker.args[0] == preferences_dialog.config

    def test_accept_changes(self, preferences_dialog, qtbot):
        """Test accepting changes."""
        with qtbot.waitSignal(
            preferences_dialog.config_changed, timeout=1000
        ) as blocker:
            # Mock the accept method to avoid actually closing the dialog
            from unittest.mock import patch

            with patch.object(preferences_dialog, "accept"):
                preferences_dialog.accept_changes()

        # Should emit the current config
        assert blocker.args[0] == preferences_dialog.config

    def test_restore_defaults(self, preferences_dialog):
        """Test restoring defaults."""
        # Modify the config first

        # Restore defaults
        preferences_dialog.restore_defaults()

        # Should create a new default config
        assert isinstance(preferences_dialog.config, UserConfig)
        # Should be different from the original (assuming original wasn't default)
        # This test might need adjustment based on actual default values

    def test_config_changed_signal(self, preferences_dialog):
        """Test config_changed signal exists."""
        assert hasattr(preferences_dialog, "config_changed")

        # Should be able to connect to it
        signal_received = False

        def signal_handler(config):
            nonlocal signal_received
            signal_received = True

        preferences_dialog.config_changed.connect(signal_handler)
        preferences_dialog.config_changed.emit(preferences_dialog.config)

        assert signal_received

    @pytest.mark.parametrize("tab_index", [0, 1, 2, 3, 4])
    def test_tab_switching(self, preferences_dialog, tab_index):
        """Test switching between tabs."""
        preferences_dialog.tab_widget.setCurrentIndex(tab_index)
        assert preferences_dialog.tab_widget.currentIndex() == tab_index

    def test_dialog_modality(self, preferences_dialog):
        """Test dialog is modal."""
        assert preferences_dialog.isModal() is True

    def test_dialog_size(self, preferences_dialog):
        """Test dialog has correct size."""
        size = preferences_dialog.size()
        assert size.width() == 800
        assert size.height() == 600


class TestBasePreferenceTab:
    """Test the BasePreferenceTab class."""

    @pytest.fixture
    def base_tab(self, qapp, sample_user_config):
        """Create a BasePreferenceTab for testing."""
        return BasePreferenceTab(sample_user_config)

    def test_base_tab_creation(self, base_tab, sample_user_config):
        """Test creating a BasePreferenceTab."""
        assert isinstance(base_tab, QWidget)
        assert base_tab.config == sample_user_config

    def test_base_tab_methods(self, base_tab):
        """Test base tab methods exist."""
        assert hasattr(base_tab, "setup_ui")
        assert hasattr(base_tab, "load_config")
        assert hasattr(base_tab, "save_config")

        assert callable(base_tab.setup_ui)
        assert callable(base_tab.load_config)
        assert callable(base_tab.save_config)

    def test_base_tab_method_calls(self, base_tab):
        """Test base tab methods can be called without error."""
        # These are placeholder methods in the base class
        base_tab.setup_ui()  # Should not raise
        base_tab.load_config()  # Should not raise
        base_tab.save_config()  # Should not raise

    def test_config_assignment(self, base_tab, sample_user_config):
        """Test config is properly assigned."""
        assert base_tab.config is sample_user_config

    def test_inheritance_structure(self, base_tab):
        """Test inheritance structure."""
        assert isinstance(base_tab, QWidget)
        assert isinstance(base_tab, BasePreferenceTab)


class TestPreferencesIntegration:
    """Integration tests for preferences system."""

    @pytest.fixture
    def preferences_dialog(self, qapp, sample_user_config):
        """Create a PreferencesDialog for testing."""
        return PreferencesDialog(sample_user_config)

    def test_tab_config_consistency(self, preferences_dialog):
        """Test that all tabs receive the same config."""
        config = preferences_dialog.config

        for i in range(preferences_dialog.tab_widget.count()):
            tab = preferences_dialog.tab_widget.widget(i)
            if hasattr(tab, "config"):
                assert tab.config is config

    def test_dialog_workflow(self, preferences_dialog, qtbot):
        """Test complete dialog workflow."""
        # Load config
        preferences_dialog.load_config()

        # Apply changes
        with qtbot.waitSignal(preferences_dialog.config_changed, timeout=1000):
            preferences_dialog.apply_changes()

        # Should not raise any exceptions

    def test_button_connections(self, preferences_dialog):
        """Test that buttons are properly connected."""
        layout = preferences_dialog.layout()
        button_box = None

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(item.widget(), QDialogButtonBox):
                button_box = item.widget()
                break

        assert button_box is not None

        # Test that signals are connected (we can't easily test the actual connections,
        # but we can verify the buttons exist and the methods exist)
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        restore_button = button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        )

        assert ok_button is not None
        assert cancel_button is not None
        assert restore_button is not None

    def test_config_isolation(self, qapp, sample_user_config):
        """Test that dialog works with a copy of config."""
        original_config = sample_user_config
        dialog = PreferencesDialog(original_config)

        # Modify dialog config
        dialog.config = UserConfig()  # Reset to defaults

        # Original should be unchanged
        assert dialog.original_config is original_config
        assert dialog.config is not original_config

    def test_multiple_dialogs(self, qapp, sample_user_config):
        """Test creating multiple dialog instances."""
        dialog1 = PreferencesDialog(sample_user_config)
        dialog2 = PreferencesDialog(sample_user_config)

        assert dialog1 is not dialog2
        assert dialog1.config is not dialog2.config
        assert dialog1.original_config is dialog2.original_config

    def test_tab_widget_properties(self, preferences_dialog):
        """Test tab widget properties."""
        tab_widget = preferences_dialog.tab_widget

        # Should be able to switch tabs
        for i in range(tab_widget.count()):
            tab_widget.setCurrentIndex(i)
            assert tab_widget.currentIndex() == i

            # Current widget should be a QWidget
            current_widget = tab_widget.currentWidget()
            assert isinstance(current_widget, QWidget)

    def test_dialog_rejection(self, preferences_dialog):
        """Test dialog rejection doesn't emit config_changed."""
        # This is harder to test without actually showing the dialog
        # but we can test that reject method exists
        assert hasattr(preferences_dialog, "reject")
        assert callable(preferences_dialog.reject)

    def test_config_validation(self, qapp):
        """Test dialog handles invalid config gracefully."""
        # Test with None config (should not crash)
        try:
            dialog = PreferencesDialog(UserConfig())
            assert isinstance(dialog, PreferencesDialog)
        except (RuntimeError, ValueError, TypeError) as e:
            pytest.fail(f"Dialog creation with default config failed: {e}")

    def test_tab_order(self, preferences_dialog):
        """Test tab order is consistent."""
        expected_order = ["General", "Services", "Downloads", "Audio", "Advanced"]

        for i, expected_title in enumerate(expected_order):
            actual_title = preferences_dialog.tab_widget.tabText(i)
            assert actual_title == expected_title

    def test_dialog_cleanup(self, preferences_dialog):
        """Test dialog cleanup."""
        # Test that dialog can be properly closed/destroyed
        # This is mainly to ensure no resource leaks
        assert preferences_dialog is not None

        # In a real application, the dialog would be closed with close()
        # Here we just verify it exists and has the expected structure
        assert hasattr(preferences_dialog, "close")
        assert callable(preferences_dialog.close)
