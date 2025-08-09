# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Album art widget for displaying album artwork."""

from typing import Any

import qtawesome as qta
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import (
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Size/constants (SCREAMING_CONSTANTS) for easy adjustments in one place
CARD_WIDTH = 180
CARD_HEIGHT = 260
ART_SIZE = 180
ART_CORNER_RADIUS = 4
MARGIN = 8

DOWNLOAD_BUTTON_SIZE = 36
DOWNLOAD_BUTTON_BORDER_WIDTH = 1
DOWNLOAD_BUTTON_CORNER_RADIUS = DOWNLOAD_BUTTON_SIZE // 2  # circular pill
DOWNLOAD_ICON_SIZE = 20

TRACK_COUNT_WIDTH = 24
TRACK_COUNT_HEIGHT = 20
TRACK_COUNT_CORNER_RADIUS = 10
TRACK_COUNT_FONT_SIZE = 11

EXPLICIT_BUTTON_SIZE = 20
EXPLICIT_BUTTON_CORNER_RADIUS = EXPLICIT_BUTTON_SIZE // 2
EXPLICIT_BUTTON_Y_ADJUST = 6


class AlbumArtWidget(QWidget):
    """Widget for displaying album artwork like Plex."""

    clicked = pyqtSignal(str)  # item_id
    download_requested = pyqtSignal(dict)  # item_details

    def __init__(self, item_data: dict[str, Any], parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.item_id = item_data.get("id", "")
        self.art_label = None
        # Track current status to avoid unintended resets. Values: "idle" | "queued" | "downloading" | "downloaded"
        self._status: str = "idle"
        self.setup_ui()

    def setup_ui(self):
        """Set up the album art widget."""
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)  # art + text and button
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QWidget:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)

        # Create layout for art and text
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Album art container with download button overlay
        art_container = QWidget()
        art_container.setFixedSize(ART_SIZE, ART_SIZE)
        art_container.setStyleSheet("background-color: transparent;")

        # Album art placeholder
        self.art_label = QLabel(art_container)
        self.art_label.setFixedSize(ART_SIZE, ART_SIZE)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_label.setStyleSheet("""
            QLabel {
                border: none;
                background-color: transparent;
            }
        """)

        # Load artwork or show placeholder
        self.load_artwork()

        # Download button overlay
        self.download_btn = QPushButton(art_container)
        self.download_btn.setIcon(qta.icon("fa5s.download", color="white"))
        self.download_btn.setFixedSize(DOWNLOAD_BUTTON_SIZE, DOWNLOAD_BUTTON_SIZE)
        self.download_btn.setIconSize(QSize(DOWNLOAD_ICON_SIZE, DOWNLOAD_ICON_SIZE))
        self.download_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(0, 0, 0, 0.7);
                border: {DOWNLOAD_BUTTON_BORDER_WIDTH}px solid white;
                border-radius: {DOWNLOAD_BUTTON_CORNER_RADIUS}px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.9);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 0, 0, 1.0);
            }}
        """
        )
        self.download_btn.clicked.connect(self._on_download_clicked)
        self.download_btn.setToolTip("Download")

        # Add track count indicator in top-right corner
        track_count = self.item_data.get("track_count", 0)
        if track_count > 0:
            self.track_count_label = QLabel(str(track_count), art_container)
            self.track_count_label.setFixedSize(TRACK_COUNT_WIDTH, TRACK_COUNT_HEIGHT)
            self.track_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.track_count_label.setStyleSheet(
                f"""
                QLabel {{
                    background-color: rgba(0, 0, 0, 0.7);
                    color: white;
                    border: none;
                    border-radius: {TRACK_COUNT_CORNER_RADIUS}px;
                    font-weight: bold;
                    font-size: {TRACK_COUNT_FONT_SIZE}px;
                }}
            """
            )
            # Position track count in top-right corner
            self.track_count_label.move(ART_SIZE - TRACK_COUNT_WIDTH - MARGIN, MARGIN)
            self.track_count_label.raise_()

        # Add explicit content indicator if needed
        if self.item_data.get("is_explicit", False):
            self.explicit_btn = QPushButton("E", art_container)
            self.explicit_btn.setFixedSize(EXPLICIT_BUTTON_SIZE, EXPLICIT_BUTTON_SIZE)
            self.explicit_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(230, 0, 0, 200);
                    color: white;
                    border: 1px solid black;
                    border-radius: {EXPLICIT_BUTTON_CORNER_RADIUS}px;
                    font-weight: bold;
                    font-size: 12px;
                }}
            """
            )
            # Position explicit indicator in bottom-left corner (opposite of download button)
            self.explicit_btn.move(
                MARGIN,
                ART_SIZE - DOWNLOAD_BUTTON_SIZE - MARGIN + EXPLICIT_BUTTON_Y_ADJUST,
            )
            self.explicit_btn.raise_()

        # Position download button in bottom-right corner
        self.download_btn.move(
            ART_SIZE - DOWNLOAD_BUTTON_SIZE - MARGIN,
            ART_SIZE - DOWNLOAD_BUTTON_SIZE - MARGIN,
        )
        self.download_btn.raise_()  # Ensure button is on top

        # Title and year labels
        full_title = self.item_data.get("title", "") or "Unknown Title"
        year = self.item_data.get("year", "")
        year_text = f" ({year})" if year else ""
        is_hires = bool(self.item_data.get("hires", False))

        display_title = full_title
        was_truncated = False
        if len(display_title) > 25:
            display_title = display_title[:22] + "..."
            was_truncated = True

        # Add HI-RES text if hires is true (HTML styled for label)
        hires_text = ""
        if is_hires:
            hires_text = ' <span style="font-size: 10px; font-weight: bold; color: #FFD700; text-shadow: 1px 1px 0px black, -1px -1px 0px black, 1px -1px 0px black, -1px 1px 0px black;">HI-RES</span>'

        title_label = QLabel(display_title + year_text + hires_text)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setTextFormat(
            Qt.TextFormat.RichText
        )  # Enable rich text for HTML styling
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                background-color: transparent;
                border: none;
            }
        """)
        title_label.setWordWrap(True)
        # Tooltip on the entire widget with full title, year, and HI-RES if applicable
        hires_suffix = " HI-RES" if is_hires else ""
        if was_truncated:
            self.setToolTip(f"{full_title}{year_text}{hires_suffix}")

        # Artist name label
        artist = self.item_data.get("artist", "")
        if not artist:
            artist = "Unknown Artist"

        artist_label = QLabel(artist)
        artist_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        artist_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                background-color: transparent;
                border: none;
            }
        """)
        artist_label.setWordWrap(True)

        # set qlabel size policies
        title_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        artist_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum
        )
        title_label.setMaximumHeight(15)
        artist_label.setMaximumHeight(15)

        # Text container to reduce spacing
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)  # Reduced spacing between title and artist

        text_layout.addWidget(title_label)
        text_layout.addWidget(artist_label)

        layout.addWidget(art_container)
        layout.addWidget(text_container)

    def load_artwork(self):
        """Load artwork or show placeholder with rounded corners."""
        # For now, create a placeholder with the first letter of the title
        title = self.item_data.get("title", "Unknown")
        first_letter = title[0].upper() if title else "?"

        # Create a pixmap with rounded corners
        pixmap = QPixmap(ART_SIZE, ART_SIZE)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(
            0, 0, ART_SIZE, ART_SIZE, ART_CORNER_RADIUS, ART_CORNER_RADIUS
        )

        # Set clipping path
        painter.setClipPath(path)

        # Fill with background color
        painter.fillRect(0, 0, ART_SIZE, ART_SIZE, QColor("#e0e0e0"))

        # Draw background circle
        painter.setBrush(QBrush(QColor("#2196F3")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(40, 40, 100, 100)

        # Draw letter
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setPointSize(48)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(40, 40, 100, 100, Qt.AlignmentFlag.AlignCenter, first_letter)

        painter.end()

        if self.art_label:
            self.art_label.setPixmap(pixmap)

    def _create_rounded_pixmap(self, width: int, height: int, radius: int) -> QPixmap:
        """Create a pixmap with rounded corners."""
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(0, 0, width, height, radius, radius)

        # Set clipping path
        painter.setClipPath(path)

        painter.end()
        return pixmap

    def update_artwork(self, pixmap: QPixmap):
        """Update the artwork with a new pixmap and apply rounded corners."""
        if self.art_label and pixmap and not pixmap.isNull():
            # Scale pixmap to fit the label
            scaled_pixmap = pixmap.scaled(
                ART_SIZE,
                ART_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            # Apply rounded corners to the scaled pixmap
            rounded_pixmap = self._apply_rounded_corners(
                scaled_pixmap, ART_CORNER_RADIUS
            )
            self.art_label.setPixmap(rounded_pixmap)

    def _apply_rounded_corners(self, pixmap: QPixmap, radius: int) -> QPixmap:
        """Apply rounded corners to a pixmap."""
        size = pixmap.size()
        rounded_pixmap = QPixmap(size)
        rounded_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)

        # Set clipping path and draw the original pixmap
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)

        painter.end()
        return rounded_pixmap

    def _on_download_clicked(self):
        """Handle download button click - immediately set to queued state."""
        self.set_queued_status()
        self.download_requested.emit(self.item_data)

    def set_queued_status(self):
        """Update the download button to show queued status."""
        self.download_btn.setIcon(qta.icon("fa5s.clock", color="orange"))
        self.download_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(255, 165, 0, 0.7);
                border: {DOWNLOAD_BUTTON_BORDER_WIDTH}px solid white;
                border-radius: {DOWNLOAD_BUTTON_CORNER_RADIUS}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 165, 0, 0.7);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 165, 0, 0.7);
            }}
        """
        )
        self.download_btn.setEnabled(False)
        self.download_btn.setToolTip("Queued for download")
        self._status = "queued"

    def set_downloading_status(self):
        """Update the button to show downloading (work in progress) status."""
        self.download_btn.setIcon(qta.icon("fa5s.sync-alt", color="#00BFFF"))
        self.download_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(0, 191, 255, 0.7);
                border: {DOWNLOAD_BUTTON_BORDER_WIDTH}px solid white;
                border-radius: {DOWNLOAD_BUTTON_CORNER_RADIUS}px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 191, 255, 0.85);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 191, 255, 1.0);
            }}
        """
        )
        self.download_btn.setEnabled(False)
        self.download_btn.setToolTip("Downloading...")
        self._status = "downloading"

    def set_downloaded_status(self, is_downloaded: bool):
        """Update the download button to show downloaded status."""
        if is_downloaded:
            # Replace download button with downloaded indicator
            self.download_btn.setIcon(qta.icon("fa5s.check-circle", color="green"))
            self.download_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(0, 128, 0, 0.7);
                    border: {DOWNLOAD_BUTTON_BORDER_WIDTH}px solid white;
                    border-radius: {DOWNLOAD_BUTTON_CORNER_RADIUS}px;
                }}
                QPushButton:hover {{
                    background-color: rgba(0, 128, 0, 0.9);
                }}
            """
            )
            # Disconnect the download signal and connect to no-op
            self.download_btn.clicked.disconnect()
            self.download_btn.clicked.connect(lambda: None)  # No action
            self.download_btn.setToolTip("Already downloaded")
            self._status = "downloaded"
        else:
            # Do not reset here; keep current status (queued/downloading/idle)
            return

    def set_idle_status(self):
        """Reset button to default idle (download) state."""
        self.download_btn.setIcon(qta.icon("fa5s.download", color="white"))
        self.download_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(0, 0, 0, 0.7);
                border: {DOWNLOAD_BUTTON_BORDER_WIDTH}px solid white;
                border-radius: {DOWNLOAD_BUTTON_CORNER_RADIUS}px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.9);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 0, 0, 1.0);
            }}
        """
        )
        # Reconnect the download signal and re-enable button
        from contextlib import suppress

        with suppress(TypeError):
            self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self._on_download_clicked)
        self.download_btn.setEnabled(True)
        self.download_btn.setToolTip("Download")
        self._status = "idle"

    def update_download_status_from_albums(self, downloaded_albums: set):
        """Update download status based on downloaded albums set.

        Args:
            downloaded_albums: Set of (album_id, source) tuples for downloaded albums
        """
        album_id = self.item_data.get("id")
        source = self.item_data.get("source")

        if album_id and source:
            is_downloaded = (album_id, source) in downloaded_albums
            if is_downloaded:
                self.set_downloaded_status(True)
            # If not downloaded, keep current state (queued/downloading/idle)

    def get_status(self) -> str:
        """Get current button status."""
        return self._status

    def mousePressEvent(self, a0: QMouseEvent | None):  # noqa: N802
        """Handle mouse press events."""
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item_id)
        super().mousePressEvent(a0)
