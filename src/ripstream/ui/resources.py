# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Resource management utilities for the ripstream application."""

from pathlib import Path

from PyQt6.QtGui import QIcon, QPixmap


def get_project_root() -> Path:
    """Get the project root directory."""
    # Navigate up from src/ripstream/ui/resources.py to project root
    return Path(__file__).parent.parent.parent.parent


def get_icon_path() -> str:
    """Get the path to the application icon."""
    project_root = get_project_root()
    icon_path = project_root / "images" / "icon.png"
    return str(icon_path)


def get_application_icon() -> QIcon:
    """Get the application icon as a QIcon object."""
    icon_path = get_icon_path()
    if Path(icon_path).exists():
        return QIcon(icon_path)
    # Return empty icon if file doesn't exist
    return QIcon()


def get_application_pixmap() -> QPixmap:
    """Get the application icon as a QPixmap object."""
    icon_path = get_icon_path()
    if Path(icon_path).exists():
        return QPixmap(icon_path)
    # Return empty pixmap if file doesn't exist
    return QPixmap()
