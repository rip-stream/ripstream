# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Main entry point for the ripstream application."""

import contextlib
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from ripstream.ui.main_window import MainWindow
from ripstream.ui.resources import get_application_icon


def _prepare_webengine() -> None:
    """Initialize Qt WebEngine before ``QApplication`` is constructed.

    ``QtWebEngineWidgets`` requires either an early import or the
    ``Qt.AA_ShareOpenGLContexts`` attribute to be set before
    ``QCoreApplication`` is created. Doing both here keeps the
    browser-based Qobuz login dialog working on every platform
    (notably macOS, where the requirement is strictly enforced).
    """
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    with contextlib.suppress(ImportError):
        from PyQt6 import QtWebEngineCore, QtWebEngineWidgets

        _ = (QtWebEngineCore, QtWebEngineWidgets)


def main() -> None:
    """Execute main function to run the ripstream application."""
    # On Windows, set the app user model ID to ensure proper taskbar icon
    if sys.platform == "win32":
        with contextlib.suppress(ImportError, AttributeError):
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "ripstream.music.downloader"
            )

    _prepare_webengine()
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Ripstream")
    app.setApplicationDisplayName("Ripstream - Music Downloader")
    app.setApplicationVersion("0.2.0")
    app.setOrganizationName("ripstream")
    app.setOrganizationDomain("ripstream.app")

    # Set application icon
    app.setWindowIcon(get_application_icon())

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start the event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
