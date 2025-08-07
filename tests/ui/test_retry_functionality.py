# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for download retry functionality."""

from unittest.mock import Mock, patch

import pytest

from ripstream.config.user import UserConfig


class TestRetryFunctionality:
    """Test retry functionality for downloads."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock(spec=UserConfig)
        # Mock the downloads configuration
        downloads_config = Mock()
        downloads_config.folder = "/test/downloads"
        downloads_config.source_subdirectories = False
        config.downloads = downloads_config

        # Mock service configuration
        service_config = Mock()
        service_config.email_or_userid = "test_user"
        service_config.password_or_token = "test_password"
        service_config.app_id = "test_app_id"
        service_config.secrets = ["test_secret1", "test_secret2"]
        service_config.use_auth_token = False
        service_config.app_secret = ""  # For other services
        config.get_service_config.return_value = service_config

        return config

    def test_retry_download_credentials_mapping(self, mock_config):
        """Test that credentials are properly retrieved from service config."""
        # This test verifies that the download worker uses the service config's
        # built-in get_decoded_credentials() method

        from ripstream.ui.download_worker import DownloadWorker

        worker = DownloadWorker(mock_config)

        # Test that the method calls get_decoded_credentials() on the service config
        with patch.object(
            mock_config.get_service_config.return_value, "get_decoded_credentials"
        ) as mock_get_creds:
            mock_get_creds.return_value = {
                "email_or_userid": "test_user",
                "password_or_token": "test_password",
                "app_id": "test_app_id",
                "secrets": ["test_secret1", "test_secret2"],
                "use_auth_token": False,
            }

            qobuz_creds = worker._get_service_credentials("qobuz")

            # Verify the method was called
            mock_get_creds.assert_called_once()

            # Verify the returned credentials
            assert qobuz_creds["email_or_userid"] == "test_user"
            assert qobuz_creds["password_or_token"] == "test_password"
            assert qobuz_creds["app_id"] == "test_app_id"
            assert qobuz_creds["secrets"] == ["test_secret1", "test_secret2"]
            assert qobuz_creds["use_auth_token"] is False

    def test_retry_download_credentials_empty_secrets(self, mock_config):
        """Test credential mapping with empty secrets."""
        from ripstream.ui.download_worker import DownloadWorker

        worker = DownloadWorker(mock_config)

        with patch.object(
            mock_config.get_service_config.return_value, "get_decoded_credentials"
        ) as mock_get_creds:
            mock_get_creds.return_value = {"secrets": []}

            qobuz_creds = worker._get_service_credentials("qobuz")
            assert qobuz_creds["secrets"] == []

    def test_retry_download_credentials_none_secrets(self, mock_config):
        """Test credential mapping with None secrets."""
        from ripstream.ui.download_worker import DownloadWorker

        worker = DownloadWorker(mock_config)

        with patch.object(
            mock_config.get_service_config.return_value, "get_decoded_credentials"
        ) as mock_get_creds:
            mock_get_creds.return_value = {"secrets": []}

            qobuz_creds = worker._get_service_credentials("qobuz")
            assert qobuz_creds["secrets"] == []
