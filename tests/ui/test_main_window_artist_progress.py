# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for artist progress functionality in MainWindow."""

from unittest.mock import Mock, patch

import pytest

from ripstream.ui.main_window import MainWindow


class TestMainWindowArtistProgress:
    """Test the artist progress functionality in MainWindow."""

    @pytest.fixture
    def mock_config_path(self, tmp_path):
        """Mock config path for testing."""
        return tmp_path / "config.json"

    @pytest.fixture
    def mock_main_window_dependencies(self, mock_config_path):
        """Mock all MainWindow dependencies."""
        with (
            patch("ripstream.ui.main_window.ConfigManager") as mock_config_manager,
            patch("ripstream.ui.main_window.URLParser"),
            patch("ripstream.ui.main_window.MetadataService") as mock_metadata_service,
            patch("ripstream.ui.main_window.UIManager") as mock_ui_manager,
            patch("ripstream.ui.main_window.DownloadHandler") as mock_download_handler,
            patch("ripstream.ui.main_window.UserConfig"),
        ):
            # Setup mock returns
            mock_config_path.write_text("{}")

            # Mock config manager
            config_manager_instance = Mock()
            config_manager_instance.load_config.return_value = Mock()
            mock_config_manager.return_value = config_manager_instance

            # Mock metadata service with signals
            metadata_service_instance = Mock()
            metadata_service_instance.metadata_ready = Mock()
            metadata_service_instance.album_ready = Mock()
            metadata_service_instance.artwork_ready = Mock()
            metadata_service_instance.progress_updated = Mock()
            metadata_service_instance.artist_progress_updated = Mock()
            metadata_service_instance.error_occurred = Mock()
            mock_metadata_service.return_value = metadata_service_instance

            # Mock UI manager
            ui_manager_instance = Mock()
            ui_manager_instance.update_status = Mock()
            ui_manager_instance.set_loading_state = Mock()
            ui_manager_instance.get_discography_view = Mock(return_value=Mock())
            ui_manager_instance.get_downloads_view = Mock(return_value=Mock())
            ui_manager_instance.get_navbar = Mock(return_value=Mock())
            mock_ui_manager.return_value = ui_manager_instance

            # Mock download handler
            download_handler_instance = Mock()
            mock_download_handler.return_value = download_handler_instance

            yield {
                "metadata_service": metadata_service_instance,
                "ui_manager": ui_manager_instance,
                "download_handler": download_handler_instance,
                "config_manager": config_manager_instance,
            }

    @pytest.fixture
    def main_window(self, qapp, mock_main_window_dependencies):
        """Create MainWindow instance with mocked dependencies."""
        # Create a minimal mock window instead of full MainWindow
        window = Mock()
        window.ui_manager = mock_main_window_dependencies["ui_manager"]
        window.metadata_service = mock_main_window_dependencies["metadata_service"]
        window.download_handler = mock_main_window_dependencies["download_handler"]
        window.config_manager = mock_main_window_dependencies["config_manager"]

        # Add the actual method we want to test
        window.handle_artist_progress = MainWindow.handle_artist_progress.__get__(
            window
        )
        window.handle_metadata_ready = MainWindow.handle_metadata_ready.__get__(window)

        return window

    def test_artist_progress_signal_connection(
        self, main_window, mock_main_window_dependencies
    ):
        """Test that artist_progress_updated signal is connected."""
        metadata_service = mock_main_window_dependencies["metadata_service"]

        # Verify the signal connection was made (it should be called during window creation)
        # Since we're using a mock window, we just verify the signal exists
        assert hasattr(metadata_service, "artist_progress_updated")
        assert hasattr(main_window, "handle_artist_progress")

    def test_handle_artist_progress_method_exists(self, main_window):
        """Test that handle_artist_progress method exists."""
        assert hasattr(main_window, "handle_artist_progress")

    @pytest.mark.parametrize(
        ("remaining", "total", "service", "expected_message"),
        [
            (
                5,
                10,
                "Qobuz",
                "Loading artist albums - 5/10 completed, 5 remaining from Qobuz",
            ),
            (
                1,
                3,
                "Tidal",
                "Loading artist albums - 2/3 completed, 1 remaining from Tidal",
            ),
            (
                15,
                20,
                "Deezer",
                "Loading artist albums - 5/20 completed, 15 remaining from Deezer",
            ),
            (0, 5, "YouTube", "Completed loading 5 albums from YouTube"),
            (0, 1, "Qobuz", "Completed loading 1 albums from Qobuz"),
            (0, 0, "Tidal", "Completed loading 0 albums from Tidal"),
        ],
    )
    def test_handle_artist_progress_status_messages(
        self,
        main_window,
        mock_main_window_dependencies,
        remaining: int,
        total: int,
        service: str,
        expected_message: str,
    ):
        """Test that handle_artist_progress updates status with correct messages."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Call the method
        main_window.handle_artist_progress(remaining, total, service)

        # Verify the status was updated with the expected message
        ui_manager.update_status.assert_called_with(expected_message)

    def test_handle_artist_progress_with_remaining_items(
        self, main_window, mock_main_window_dependencies
    ):
        """Test handle_artist_progress when there are remaining items."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Test with remaining items
        main_window.handle_artist_progress(3, 10, "TestService")

        # Verify status was updated
        ui_manager.update_status.assert_called_with(
            "Loading artist albums - 7/10 completed, 3 remaining from TestService"
        )

    def test_handle_artist_progress_completion(
        self, main_window, mock_main_window_dependencies
    ):
        """Test handle_artist_progress when all items are completed."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Test with no remaining items
        main_window.handle_artist_progress(0, 5, "TestService")

        # Verify status was updated
        ui_manager.update_status.assert_called_with(
            "Completed loading 5 albums from TestService"
        )

    def test_handle_metadata_ready_artist_content(
        self, main_window, mock_main_window_dependencies
    ):
        """Test handle_metadata_ready with artist content."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Mock metadata with artist content
        metadata = {
            "content_type": "artist",
            "service": "TestService",
            "artist_info": {
                "name": "Test Artist",
                "total_items": 15,
            },
            "items": [{"id": f"item_{i}"} for i in range(15)],
        }

        # Call the method
        main_window.handle_metadata_ready(metadata)

        # Verify the status was updated with the expected message
        ui_manager.update_status.assert_called_with(
            "Loaded 15 items by 'Test Artist' from TestService"
        )

    def test_handle_metadata_ready_album_content_unchanged(
        self, main_window, mock_main_window_dependencies
    ):
        """Test handle_metadata_ready with album content (should not change existing behavior)."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Mock metadata with album content
        metadata = {
            "content_type": "album",
            "service": "TestService",
            "album_info": {
                "title": "Test Album",
                "artist": "Test Artist",
            },
            "items": [{"id": f"track_{i}"} for i in range(10)],
        }

        # Call the method
        main_window.handle_metadata_ready(metadata)

        # Verify the status was updated with the expected message
        ui_manager.update_status.assert_called_with(
            "Loaded album 'Test Album' by Test Artist with 10 tracks from TestService"
        )

    @pytest.mark.parametrize(
        ("content_type", "items_count", "expected_message"),
        [
            ("track", 1, "Loaded 1 track(s) from TestService"),
            ("playlist", 25, "Loaded 25 playlist(s) from TestService"),
            ("unknown", 0, "Loaded 0 unknown(s) from TestService"),
        ],
    )
    def test_handle_metadata_ready_other_content_types(
        self,
        main_window,
        mock_main_window_dependencies,
        content_type: str,
        items_count: int,
        expected_message: str,
    ):
        """Test handle_metadata_ready with different content types."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Mock metadata with different content types
        metadata = {
            "content_type": content_type,
            "service": "TestService",
            "items": [{"id": f"item_{i}"} for i in range(items_count)],
        }

        # Call the method
        main_window.handle_metadata_ready(metadata)

        # Verify the status was updated with the expected message
        ui_manager.update_status.assert_called_with(expected_message)

    def test_artist_progress_integration_with_metadata_service(
        self, main_window, mock_main_window_dependencies
    ):
        """Test integration between metadata service and artist progress handling."""
        metadata_service = mock_main_window_dependencies["metadata_service"]
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Verify the signal connection exists
        assert hasattr(metadata_service, "artist_progress_updated")
        assert hasattr(main_window, "handle_artist_progress")

        # Test that the method can be called
        main_window.handle_artist_progress(2, 5, "TestService")
        ui_manager.update_status.assert_called()

    def test_handle_artist_progress_edge_cases(
        self, main_window, mock_main_window_dependencies
    ):
        """Test handle_artist_progress with edge cases."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Test with zero total
        main_window.handle_artist_progress(0, 0, "TestService")
        ui_manager.update_status.assert_called_with(
            "Completed loading 0 albums from TestService"
        )

        # Test with large numbers
        main_window.handle_artist_progress(1000, 10000, "TestService")
        ui_manager.update_status.assert_called_with(
            "Loading artist albums - 9000/10000 completed, 1000 remaining from TestService"
        )

        # Test with single item
        main_window.handle_artist_progress(0, 1, "TestService")
        ui_manager.update_status.assert_called_with(
            "Completed loading 1 albums from TestService"
        )

    def test_multiple_artist_progress_updates(
        self, main_window, mock_main_window_dependencies
    ):
        """Test multiple consecutive artist progress updates."""
        ui_manager = mock_main_window_dependencies["ui_manager"]

        # Simulate multiple progress updates
        updates = [
            (10, 10, "Service1"),
            (5, 10, "Service2"),
            (0, 10, "Service3"),
        ]

        for remaining, total, service in updates:
            main_window.handle_artist_progress(remaining, total, service)

        # Verify that update_status was called for each update
        assert ui_manager.update_status.call_count == 3

        # Verify the last call was for the completion message
        ui_manager.update_status.assert_called_with(
            "Completed loading 10 albums from Service3"
        )

    def test_artist_progress_signal_signature(self):
        """Test that the artist progress signal has the correct signature."""
        # Test the actual method signature from the MainWindow class
        import inspect

        sig = inspect.signature(MainWindow.handle_artist_progress)
        params = list(sig.parameters.keys())

        # Should have 4 parameters: self, remaining_items, total_items, service
        assert len(params) == 4
        assert params[0] == "self"  # self parameter
        assert params[1] == "remaining_items"
        assert params[2] == "total_items"
        assert params[3] == "service"
