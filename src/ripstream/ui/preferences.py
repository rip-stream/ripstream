# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Preferences dialog for ripstream application."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ripstream.config.user import UserConfig


class PreferencesDialog(QDialog):
    """Main preferences dialog with tabbed interface."""

    config_changed = pyqtSignal(UserConfig)

    def __init__(self, config: UserConfig, parent=None):
        super().__init__(parent)
        self.config = config.model_copy(deep=True)  # Work with a copy
        self.original_config = config

        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(800, 600)

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        """Set up the main UI layout."""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_tabs()

        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )

        button_box.accepted.connect(self.accept_changes)
        button_box.rejected.connect(self.reject)

        # Connect Apply button to apply without closing
        apply_button = button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self.apply_changes)

        # Connect RestoreDefaults button if it exists
        restore_button = button_box.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        if restore_button is not None:
            restore_button.clicked.connect(self.restore_defaults)

        layout.addWidget(button_box)

    def create_tabs(self):
        """Create all preference tabs."""
        from ripstream.ui.preferences_tabs import (
            AdvancedTab,
            AudioTab,
            DownloadsTab,
            GeneralTab,
            ServicesTab,
        )

        # General settings
        self.general_tab = GeneralTab(self.config)
        self.tab_widget.addTab(self.general_tab, "General")

        # Service authentication
        self.services_tab = ServicesTab(self.config)
        self.tab_widget.addTab(self.services_tab, "Services")

        # Download settings
        self.downloads_tab = DownloadsTab(self.config)
        self.tab_widget.addTab(self.downloads_tab, "Downloads")

        # Audio settings
        self.audio_tab = AudioTab(self.config)
        self.tab_widget.addTab(self.audio_tab, "Audio")

        # Advanced settings
        self.advanced_tab = AdvancedTab(self.config)
        self.tab_widget.addTab(self.advanced_tab, "Advanced")

    def load_config(self):
        """Load configuration into all tabs."""
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if tab is not None and hasattr(tab, "load_config"):
                tab.load_config()  # type: ignore

    def save_config(self):
        """Save configuration from all tabs."""
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if tab is not None and hasattr(tab, "save_config"):
                tab.save_config()  # type: ignore

    def apply_changes(self):
        """Apply changes without closing dialog."""
        self.save_config()
        self.config_changed.emit(self.config)

    def accept_changes(self):
        """Accept and apply changes, then close dialog."""
        self.save_config()
        self.config_changed.emit(self.config)
        self.accept()

    def restore_defaults(self):
        """Restore all settings to defaults."""
        self.config = UserConfig()
        self.load_config()


class BasePreferenceTab(QWidget):
    """Base class for preference tabs."""

    def __init__(self, config: UserConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        """Set up the tab UI. Override in subclasses."""

    def load_config(self):
        """Load configuration values into widgets. Override in subclasses."""

    def save_config(self):
        """Save widget values to configuration. Override in subclasses."""
