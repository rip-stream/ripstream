# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for user configuration models."""

from pathlib import Path

import pytest

from ripstream.config.services import QobuzConfig, TidalConfig
from ripstream.config.user import UserConfig


class TestUserConfig:
    """Test the main UserConfig class."""

    def test_default_config_creation(self):
        """Test creating a config with default values."""
        config = UserConfig()

        # Test that all sections are created with defaults
        assert config.downloads is not None
        assert config.database is not None
        assert config.qobuz is not None
        assert config.tidal is not None
        assert config.deezer is not None
        assert config.soundcloud is not None
        assert config.youtube is not None

        # Test default values
        assert config.downloads.max_connections == 6
        assert config.qobuz.quality == 4
        assert config.tidal.quality == 3

    def test_config_validation(self):
        """Test configuration validation."""
        config = UserConfig()

        # Test valid quality settings
        config.qobuz.quality = 2
        assert config.qobuz.quality == 2

        # Test invalid quality should raise error
        with pytest.raises(ValueError, match="Qobuz quality must be between 1-4"):
            config.qobuz.quality = 5

    def test_service_config_access(self):
        """Test accessing service configurations."""
        config = UserConfig()

        # Test getting service configs
        qobuz_config = config.get_service_config("qobuz")
        assert isinstance(qobuz_config, QobuzConfig)

        tidal_config = config.get_service_config("tidal")
        assert isinstance(tidal_config, TidalConfig)

        # Test invalid service name
        with pytest.raises(ValueError, match="Unknown service"):
            config.get_service_config("invalid")

    def test_path_validation(self):
        """Test path field validation."""
        config = UserConfig()

        # Test setting path as string (via Path constructor to satisfy type checker)
        config.downloads.folder = Path("/tmp/test")
        assert isinstance(config.downloads.folder, Path)
        assert config.downloads.folder.as_posix() == "/tmp/test"

    def test_from_toml_data(self):
        """Test creating config from TOML-like data."""
        data = {
            "downloads": {
                "folder": "/custom/path",
                "max_connections": 10,
                "concurrency": False,
            },
            "qobuz": {
                "quality": 3,
                "download_booklets": False,
                "email_or_userid": "test@example.com",
            },
            "tidal": {
                "quality": 2,
                "download_videos": False,
            },
        }

        config = UserConfig.model_validate(data)

        # Test that values were set correctly
        assert config.downloads.folder.as_posix() == "/custom/path"
        assert config.downloads.max_connections == 10
        assert config.downloads.concurrency is False
        assert config.qobuz.quality == 3
        assert config.qobuz.download_booklets is False
        assert config.qobuz.email_or_userid == "test@example.com"
        assert config.tidal.quality == 2
        assert config.tidal.download_videos is False

    def test_config_serialization(self):
        """Test config serialization to dict."""
        config = UserConfig()
        config.qobuz.quality = 2
        config.downloads.max_connections = 8

        data = config.model_dump()

        # Test that data contains expected structure
        assert "downloads" in data
        assert "qobuz" in data
        assert data["downloads"]["max_connections"] == 8
        assert data["qobuz"]["quality"] == 2


class TestServiceConfigs:
    """Test individual service configurations."""

    def test_qobuz_config(self):
        """Test Qobuz configuration."""
        config = QobuzConfig()

        # Test defaults
        assert config.quality == 4
        assert config.download_booklets is True
        assert config.use_auth_token is False

        # Test validation
        with pytest.raises(ValueError, match="Qobuz quality must be between 1-4"):
            config.quality = 0
        with pytest.raises(ValueError, match="Qobuz quality must be between 1-4"):
            config.quality = 5

    def test_tidal_config(self):
        """Test Tidal configuration."""
        config = TidalConfig()

        # Test defaults
        assert config.quality == 3
        assert config.download_videos is True

        # Test validation
        with pytest.raises(ValueError, match="Tidal quality must be between 0-3"):
            config.quality = -1
        with pytest.raises(ValueError, match="Tidal quality must be between 0-3"):
            config.quality = 4

    def test_service_inheritance(self):
        """Test that services inherit from base classes correctly."""
        qobuz = QobuzConfig()

        # Test that it has ServiceConfig fields
        assert hasattr(qobuz, "quality")

        # Test that it has AuthenticatedServiceConfig fields
        assert hasattr(qobuz, "email_or_userid")
        assert hasattr(qobuz, "password_or_token")

        # Test that it has DownloadableConfig fields
        assert hasattr(qobuz, "download_booklets")


class TestConfigValidation:
    """Test configuration validation rules."""

    def test_connection_limits(self):
        """Test connection limit validation."""
        config = UserConfig()

        # Test valid values
        config.downloads.max_connections = -1  # No limit
        config.downloads.max_connections = 5  # Positive

        # Test invalid values
        with pytest.raises(
            ValueError, match="Connection limits must be -1 \\(no limit\\) or positive"
        ):
            config.downloads.max_connections = 0
        with pytest.raises(
            ValueError, match="Connection limits must be -1 \\(no limit\\) or positive"
        ):
            config.downloads.max_connections = -2

    def test_artwork_validation(self):
        """Test artwork configuration validation."""
        config = UserConfig()

        # Test valid max width values
        config.artwork.embed_max_width = -1  # No limit
        config.artwork.embed_max_width = 1000  # Positive

        # Test invalid values
        with pytest.raises(
            ValueError, match="Max width must be -1 \\(no limit\\) or positive"
        ):
            config.artwork.embed_max_width = 0
        with pytest.raises(
            ValueError, match="Max width must be -1 \\(no limit\\) or positive"
        ):
            config.artwork.embed_max_width = -2

    def test_conversion_validation(self):
        """Test conversion configuration validation."""
        config = UserConfig()

        # Test valid values
        config.conversion.sampling_rate = 48000
        config.conversion.lossy_bitrate = 320

        # Test invalid values
        with pytest.raises(ValueError, match="Sampling rate must be positive"):
            config.conversion.sampling_rate = 0
        with pytest.raises(ValueError, match="Bitrate must be positive"):
            config.conversion.lossy_bitrate = -1


if __name__ == "__main__":
    pytest.main([__file__])
