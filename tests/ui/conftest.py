# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Shared fixtures and utilities for UI tests."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

# Import qtbot from pytest-qt if available
try:
    from pytestqt.qtbot import QtBot
except ImportError:
    QtBot = None  # type: ignore[misc]  # Intentional shadowing for optional dependency

from ripstream.config.user import UserConfig
from ripstream.core.url_parser import ParsedURL
from ripstream.downloader.enums import ContentType
from ripstream.models.db_manager import DatabaseManager
from ripstream.models.download_service import DownloadService
from ripstream.models.enums import StreamingSource


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
        app.setApplicationName("RipstreamTest")
        app.setOrganizationName("ripstream-test")
        yield app
        app.quit()
    else:
        yield QApplication.instance()


# qtbot fixture is provided by pytest-qt plugin


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()

    yield db_manager

    db_manager.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def mock_download_service(temp_db):
    """Create a download service with temporary database."""
    # Mock the database managers
    import ripstream.models.db_manager as db_manager_module

    original_downloads_db = db_manager_module._downloads_db

    db_manager_module._downloads_db = temp_db

    service = DownloadService()

    yield service

    # Restore original state
    db_manager_module._downloads_db = original_downloads_db


@pytest.fixture
def mock_qsettings(monkeypatch):
    """Mock QSettings to avoid file system operations."""
    mock_settings = MagicMock(spec=QSettings)
    mock_settings.value.return_value = None
    mock_settings.setValue.return_value = None
    monkeypatch.setattr("PyQt6.QtCore.QSettings", lambda *args: mock_settings)
    return mock_settings


@pytest.fixture
def sample_user_config():
    """Create a sample UserConfig for testing."""
    return UserConfig()


@pytest.fixture
def sample_pixmap():
    """Create a sample QPixmap for testing."""
    pixmap = QPixmap(100, 100)
    pixmap.fill()
    return pixmap


@pytest.fixture
def sample_album_item():
    """Sample album item data."""
    return {
        "id": "album_123",
        "title": "Test Album",
        "artist": "Test Artist",
        "type": "Album",
        "year": 2023,
        "duration_formatted": "45:30",
        "track_count": 12,
        "quality": "FLAC",
        "artwork_url": "https://example.com/artwork.jpg",
    }


@pytest.fixture
def sample_track_item():
    """Sample track item data."""
    return {
        "id": "track_456",
        "title": "Test Track",
        "artist": "Test Artist",
        "type": "Track",
        "year": 2023,
        "duration_formatted": "3:45",
        "track_count": 1,
        "track_number": 1,
        "album": "Test Album",
        "quality": "FLAC",
        "artwork_url": "https://example.com/artwork.jpg",
    }


@pytest.fixture
def sample_playlist_item():
    """Sample playlist item data."""
    return {
        "id": "playlist_789",
        "title": "Test Playlist",
        "artist": "Test User",
        "type": "Playlist",
        "year": 2023,
        "duration_formatted": "120:00",
        "track_count": 30,
        "quality": "Mixed",
        "artwork_url": None,
    }


@pytest.fixture
def sample_album_metadata():
    """Sample album metadata for testing."""
    return {
        "content_type": "album",
        "service": "Qobuz",
        "album_info": {
            "id": "album_123",
            "title": "Test Album",
            "artist": "Test Artist",
            "year": 2023,
            "total_tracks": 3,
            "total_duration": "12:30",
            "quality": "FLAC",
            "artwork_thumbnail": "https://example.com/thumb.jpg",
        },
        "items": [
            {
                "id": "track_1",
                "title": "Track One",
                "artist": "Test Artist",
                "type": "Track",
                "year": 2023,
                "duration_formatted": "4:10",
                "track_count": 1,
                "track_number": 1,
                "album": "Test Album",
                "quality": "FLAC",
                "artwork_url": "https://example.com/artwork.jpg",
            },
            {
                "id": "track_2",
                "title": "Track Two",
                "artist": "Test Artist",
                "type": "Track",
                "year": 2023,
                "duration_formatted": "4:20",
                "track_count": 1,
                "track_number": 2,
                "album": "Test Album",
                "quality": "FLAC",
                "artwork_url": "https://example.com/artwork.jpg",
            },
        ],
    }


@pytest.fixture
def sample_download_item():
    """Sample download item for testing."""
    from datetime import UTC, datetime

    return {
        "download_id": "download_123",
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "type": "Track",
        "media_type": "TRACK",
        "source": "QOBUZ",
        "source_id": "test_track_123",
        "status": "completed",
        "progress": 100,
        "started_at": datetime.now(UTC),
        "completed_at": datetime.now(UTC),
    }


@pytest.fixture
def sample_parsed_url():
    """Sample ParsedURL for testing."""
    return ParsedURL(
        service=StreamingSource.QOBUZ,
        content_type=ContentType.ALBUM,
        content_id="123",
        url="https://open.qobuz.com/album/123",
        metadata={"title": "Test Album"},
    )


@pytest.fixture
def mock_metadata_service():
    """Mock MetadataService for testing."""
    service = Mock()
    service.metadata_ready = Mock()
    service.artwork_ready = Mock()
    service.progress_updated = Mock()
    service.error_occurred = Mock()
    service.fetch_metadata = Mock()
    service.update_config = Mock()
    service.cleanup = Mock()
    return service


@pytest.fixture
def mock_url_parser():
    """Mock URLParser for testing."""
    parser = Mock()
    parser.parse_url = Mock()
    return parser


@pytest.fixture(params=["album", "track", "playlist"])
def sample_item_by_type(
    request, sample_album_item, sample_track_item, sample_playlist_item
):
    """Parametrized fixture for different item types."""
    if request.param == "album":
        return sample_album_item
    if request.param == "track":
        return sample_track_item
    return sample_playlist_item


@pytest.fixture
def mock_config_path(tmp_path):
    """Mock config path for testing."""
    return tmp_path / "config.json"


class MockSignal:
    """Mock PyQt signal for testing."""

    def __init__(self):
        self.connected_slots = []

    def connect(self, slot):
        """Connect a slot to this signal."""
        self.connected_slots.append(slot)

    def emit(self, *args, **kwargs):
        """Emit the signal to all connected slots."""
        for slot in self.connected_slots:
            slot(*args, **kwargs)

    def disconnect(self, slot=None):
        """Disconnect slot(s) from this signal."""
        if slot is None:
            self.connected_slots.clear()
        elif slot in self.connected_slots:
            self.connected_slots.remove(slot)


@pytest.fixture
def mock_signal():
    """Create a mock PyQt signal."""
    return MockSignal()


# Utility functions for testing
def create_test_pixmap(width=100, height=100, color="blue"):
    """Create a test pixmap with specified dimensions and color."""
    from PyQt6.QtGui import QColor

    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(color))
    return pixmap


def assert_widget_properties(widget, expected_properties):
    """Assert that a widget has the expected properties."""
    for prop_name, expected_value in expected_properties.items():
        actual_value = getattr(widget, prop_name, None)
        if callable(actual_value):
            actual_value = actual_value()
        assert actual_value == expected_value, (
            f"Property {prop_name}: expected {expected_value}, got {actual_value}"
        )


def simulate_signal_emission(signal_mock, *args, **kwargs):
    """Simulate signal emission for testing."""
    if hasattr(signal_mock, "emit"):
        signal_mock.emit(*args, **kwargs)
    elif hasattr(signal_mock, "connected_slots"):
        for slot in signal_mock.connected_slots:
            slot(*args, **kwargs)
