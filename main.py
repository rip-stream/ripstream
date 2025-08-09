# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Main entry point for the ripstream application."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from ripstream.ui.main_window import MainWindow
from ripstream.ui.resources import get_application_icon

logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)


def main() -> None:
    """Execute main function to run the ripstream application."""
    # On Windows, set the app user model ID to ensure proper taskbar icon
    if sys.platform == "win32":
        try:
            import ctypes

            # Set the app user model ID to make Windows treat this as a unique application
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "ripstream.music.downloader"
            )
        except (ImportError, AttributeError):
            pass  # Ignore if ctypes is not available or on non-Windows systems

    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Ripstream")
    app.setApplicationDisplayName("Ripstream - Music Downloader")
    app.setApplicationVersion("0.1.0")
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
