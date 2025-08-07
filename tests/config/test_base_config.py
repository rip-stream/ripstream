# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for base configuration classes."""

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ripstream.config.base import (
    AuthenticatedServiceConfig,
    BaseConfig,
    DownloadableConfig,
    PathConfig,
    ServiceConfig,
    TokenBasedServiceConfig,
)


class TestBaseConfig:
    """Test the BaseConfig class."""

    def test_base_config_creation(self):
        """Test creating a basic config instance."""
        config = BaseConfig()
        assert config is not None

    def test_base_config_validation_on_assignment(self):
        """Test that validation occurs on assignment."""

        class TestConfig(BaseConfig):
            value: int

        config = TestConfig(value=10)
        assert config.value == 10

        # Test validation on assignment
        config.value = 20
        assert config.value == 20

    def test_base_config_forbids_extra_fields(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            BaseConfig.model_validate({"extra_field": "not allowed"})


class TestServiceConfig:
    """Test the ServiceConfig class."""

    def test_service_config_creation(self):
        """Test creating a service config with required quality field."""
        config = ServiceConfig(quality=2)
        assert config.quality == 2

    def test_service_config_requires_quality(self):
        """Test that quality field is required."""
        with pytest.raises(ValidationError, match="Field required"):
            ServiceConfig.model_validate({})


class TestAuthenticatedServiceConfig:
    """Test the AuthenticatedServiceConfig class."""

    @pytest.fixture
    def auth_config(self):
        """Create an authenticated service config for testing."""
        return AuthenticatedServiceConfig(
            quality=2, email_or_userid="test@example.com", password_or_token="secret123"
        )

    def test_authenticated_service_config_creation(self, auth_config):
        """Test creating an authenticated service config."""
        assert auth_config.quality == 2
        assert auth_config.email_or_userid == "test@example.com"
        assert auth_config.password_or_token == "secret123"

    def test_authenticated_service_config_defaults(self):
        """Test default values for authentication fields."""
        config = AuthenticatedServiceConfig(quality=1)
        assert config.email_or_userid == ""
        assert config.password_or_token == ""

    @pytest.mark.parametrize(
        ("field_name", "input_value", "expected"),
        [
            ("email_or_userid", "  test@example.com  ", "test@example.com"),
            ("email_or_userid", "user123", "user123"),
            ("password_or_token", "  secret123  ", "secret123"),
        ],
    )
    def test_auth_field_validation(self, field_name, input_value, expected):
        """Test validation of authentication fields."""
        config_data = {"quality": 1, field_name: input_value}
        config = AuthenticatedServiceConfig(**config_data)
        assert getattr(config, field_name) == expected

    @patch("ripstream.core.utils.decode_secret")
    def test_get_decoded_credentials(self, mock_decode_secret, auth_config):
        """Test getting decoded credentials."""
        # Mock the decode_secret function
        mock_decode_secret.side_effect = lambda x: f"decoded_{x}"

        credentials = auth_config.get_decoded_credentials()

        assert credentials["email_or_userid"] == "decoded_test@example.com"
        assert credentials["password_or_token"] == "decoded_secret123"
        assert mock_decode_secret.call_count == 2

    @patch("ripstream.core.utils.decode_secret")
    def test_get_decoded_credentials_with_additional_fields(self, mock_decode_secret):
        """Test getting decoded credentials with additional fields."""

        class ExtendedAuthConfig(AuthenticatedServiceConfig):
            extra_field: str = "extra_value"
            another_field: int = 42

        config = ExtendedAuthConfig(
            quality=2, email_or_userid="test@example.com", password_or_token="secret123"
        )

        mock_decode_secret.side_effect = lambda x: f"decoded_{x}"
        credentials = config.get_decoded_credentials()

        assert credentials["email_or_userid"] == "decoded_test@example.com"
        assert credentials["password_or_token"] == "decoded_secret123"
        assert credentials["extra_field"] == "extra_value"
        assert credentials["another_field"] == 42
        # Quality should not be included
        assert "quality" not in credentials


class TestTokenBasedServiceConfig:
    """Test the TokenBasedServiceConfig class."""

    @pytest.fixture
    def token_config(self):
        """Create a token-based service config for testing."""
        return TokenBasedServiceConfig(
            quality=3,
            access_token="access123",
            refresh_token="refresh456",
            token_expiry="2024-12-31T23:59:59Z",
        )

    def test_token_based_service_config_creation(self, token_config):
        """Test creating a token-based service config."""
        assert token_config.quality == 3
        assert token_config.access_token == "access123"
        assert token_config.refresh_token == "refresh456"
        assert token_config.token_expiry == "2024-12-31T23:59:59Z"

    def test_token_based_service_config_defaults(self):
        """Test default values for token fields."""
        config = TokenBasedServiceConfig(quality=1)
        assert config.access_token == ""
        assert config.refresh_token == ""
        assert config.token_expiry == ""

    @pytest.mark.parametrize(
        ("field_name", "input_value", "expected"),
        [
            ("access_token", "  token123  ", "token123"),
            ("refresh_token", "  refresh456  ", "refresh456"),
            ("token_expiry", "  2024-12-31  ", "2024-12-31"),
        ],
    )
    def test_token_field_validation(self, field_name, input_value, expected):
        """Test validation of token fields."""
        config_data = {"quality": 1, field_name: input_value}
        config = TokenBasedServiceConfig(**config_data)
        assert getattr(config, field_name) == expected

    @patch("ripstream.core.utils.decode_secret")
    def test_get_decoded_credentials(self, mock_decode_secret, token_config):
        """Test getting decoded credentials for token-based config."""

        # Mock the decode_secret function
        def mock_decode(value):
            if value in ["access123", "refresh456"]:
                return f"decoded_{value}"
            return value

        mock_decode_secret.side_effect = mock_decode

        credentials = token_config.get_decoded_credentials()

        assert credentials["access_token"] == "decoded_access123"
        assert credentials["refresh_token"] == "decoded_refresh456"
        assert credentials["token_expiry"] == "2024-12-31T23:59:59Z"  # Not decoded
        assert mock_decode_secret.call_count == 2

    @patch("ripstream.core.utils.decode_secret")
    def test_get_decoded_credentials_with_additional_fields(self, mock_decode_secret):
        """Test getting decoded credentials with additional fields."""

        class ExtendedTokenConfig(TokenBasedServiceConfig):
            extra_field: str = "extra_value"
            another_field: int = 42

        config = ExtendedTokenConfig(
            quality=2, access_token="access123", refresh_token="refresh456"
        )

        mock_decode_secret.side_effect = lambda x: f"decoded_{x}"
        credentials = config.get_decoded_credentials()

        assert credentials["access_token"] == "decoded_access123"
        assert credentials["refresh_token"] == "decoded_refresh456"
        assert credentials["extra_field"] == "extra_value"
        assert credentials["another_field"] == 42
        # Quality should not be included
        assert "quality" not in credentials


class TestPathConfig:
    """Test the PathConfig class."""

    def test_path_config_creation(self):
        """Test creating a path config."""
        config = PathConfig()
        assert config is not None

    def test_path_validation_converts_strings_to_paths(self):
        """Test that string paths are converted to Path objects."""

        class TestPathConfig(PathConfig):
            download_path: Path = Path("~/Downloads")
            regular_field: str = "not a path"

        config = TestPathConfig.model_validate({
            "download_path": "~/Music/Downloads",
            "regular_field": "still not a path",
        })

        assert isinstance(config.download_path, Path)
        assert config.download_path.is_absolute()  # Should be resolved
        assert isinstance(config.regular_field, str)
        assert config.regular_field == "still not a path"

    def test_path_validation_preserves_path_objects(self):
        """Test that existing Path objects are preserved."""

        class TestPathConfig(PathConfig):
            download_path: Path = Path("~/Downloads")

        original_path = Path("/tmp/test").resolve()
        config = TestPathConfig(download_path=original_path)

        assert config.download_path == original_path

    def test_path_validation_ignores_non_path_fields(self):
        """Test that fields without 'path' in name are not converted."""

        class TestPathConfig(PathConfig):
            folder_location: str = (
                "/some/folder"  # Contains path-like content but no 'path' in name
            )
            path_to_file: Path = Path("/some/file")  # Contains 'path' in name

        config = TestPathConfig.model_validate({
            "folder_location": "/another/folder",
            "path_to_file": "/another/file",
        })

        assert isinstance(config.folder_location, str)
        assert isinstance(config.path_to_file, Path)


class TestDownloadableConfig:
    """Test the DownloadableConfig class."""

    def test_downloadable_config_creation(self):
        """Test creating a downloadable config."""
        config = DownloadableConfig()
        assert config.download_videos is False
        assert config.download_booklets is False

    def test_downloadable_config_with_custom_values(self):
        """Test creating a downloadable config with custom values."""
        config = DownloadableConfig(download_videos=True, download_booklets=True)
        assert config.download_videos is True
        assert config.download_booklets is True

    @pytest.mark.parametrize(
        ("download_videos", "download_booklets"),
        [
            (True, False),
            (False, True),
            (True, True),
            (False, False),
        ],
    )
    def test_downloadable_config_combinations(self, download_videos, download_booklets):
        """Test different combinations of download settings."""
        config = DownloadableConfig(
            download_videos=download_videos, download_booklets=download_booklets
        )
        assert config.download_videos == download_videos
        assert config.download_booklets == download_booklets


if __name__ == "__main__":
    pytest.main([__file__])
