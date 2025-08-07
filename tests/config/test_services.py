# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for service-specific configuration classes."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ripstream.config.services import (
    DeezerConfig,
    QobuzConfig,
    SoundCloudConfig,
    TidalConfig,
    YouTubeConfig,
)


class TestQobuzConfig:
    """Test the QobuzConfig class."""

    @pytest.fixture
    def qobuz_config(self):
        """Create a Qobuz config for testing."""
        return QobuzConfig(
            quality=3,
            email_or_userid="test@example.com",
            password_or_token="secret123",
            download_booklets=True,
        )

    def test_qobuz_config_defaults(self):
        """Test default values for Qobuz config."""
        config = QobuzConfig()
        assert config.quality == 4
        assert config.download_booklets is True
        assert config.download_videos is False
        assert config.use_auth_token is False
        assert config.app_id == "798273057"
        assert (
            len(config.secrets) == 0
        )  # Secrets are now empty by default and populated dynamically

    @pytest.mark.parametrize("quality", [1, 2, 3, 4])
    def test_qobuz_quality_validation_valid(self, quality):
        """Test valid Qobuz quality values."""
        config = QobuzConfig(quality=quality)
        assert config.quality == quality

    @pytest.mark.parametrize("quality", [0, 5, -1, 10])
    def test_qobuz_quality_validation_invalid(self, quality):
        """Test invalid Qobuz quality values."""
        with pytest.raises(ValueError, match="Qobuz quality must be between 1-4"):
            QobuzConfig(quality=quality)

    def test_qobuz_config_inheritance(self, qobuz_config):
        """Test that QobuzConfig inherits from correct base classes."""
        # Should have AuthenticatedServiceConfig fields
        assert hasattr(qobuz_config, "email_or_userid")
        assert hasattr(qobuz_config, "password_or_token")

        # Should have DownloadableConfig fields
        assert hasattr(qobuz_config, "download_videos")
        assert hasattr(qobuz_config, "download_booklets")

        # Should have ServiceConfig fields
        assert hasattr(qobuz_config, "quality")

    def test_qobuz_config_custom_values(self):
        """Test creating Qobuz config with custom values."""
        config = QobuzConfig(
            quality=2,
            email_or_userid="custom@example.com",
            password_or_token="custom_secret",
            download_booklets=False,
            use_auth_token=True,
        )
        assert config.quality == 2
        assert config.email_or_userid == "custom@example.com"
        assert config.password_or_token == "custom_secret"
        assert config.download_booklets is False
        assert config.use_auth_token is True


class TestTidalConfig:
    """Test the TidalConfig class."""

    @pytest.fixture
    def tidal_config(self):
        """Create a Tidal config for testing."""
        return TidalConfig(
            quality=2,
            access_token="access123",
            refresh_token="refresh456",
            user_id="user123",
            country_code="US",
        )

    def test_tidal_config_defaults(self):
        """Test default values for Tidal config."""
        config = TidalConfig()
        assert config.quality == 3
        assert config.download_videos is True
        assert config.download_booklets is False
        assert config.user_id == ""
        assert config.country_code == ""

    @pytest.mark.parametrize("quality", [0, 1, 2, 3])
    def test_tidal_quality_validation_valid(self, quality):
        """Test valid Tidal quality values."""
        config = TidalConfig(quality=quality)
        assert config.quality == quality

    @pytest.mark.parametrize("quality", [-1, 4, 5, 10])
    def test_tidal_quality_validation_invalid(self, quality):
        """Test invalid Tidal quality values."""
        with pytest.raises(ValueError, match="Tidal quality must be between 0-3"):
            TidalConfig(quality=quality)

    def test_tidal_config_inheritance(self, tidal_config):
        """Test that TidalConfig inherits from correct base classes."""
        # Should have TokenBasedServiceConfig fields
        assert hasattr(tidal_config, "access_token")
        assert hasattr(tidal_config, "refresh_token")
        assert hasattr(tidal_config, "token_expiry")

        # Should have DownloadableConfig fields
        assert hasattr(tidal_config, "download_videos")
        assert hasattr(tidal_config, "download_booklets")

        # Should have ServiceConfig fields
        assert hasattr(tidal_config, "quality")

    def test_tidal_config_custom_values(self, tidal_config):
        """Test Tidal config with custom values."""
        assert tidal_config.quality == 2
        assert tidal_config.access_token == "access123"
        assert tidal_config.refresh_token == "refresh456"
        assert tidal_config.user_id == "user123"
        assert tidal_config.country_code == "US"


class TestDeezerConfig:
    """Test the DeezerConfig class."""

    @pytest.fixture
    def deezer_config(self):
        """Create a Deezer config for testing."""
        return DeezerConfig(
            quality=1,
            arl="test_arl_token",
            use_deezloader=False,
            deezloader_warnings=False,
        )

    def test_deezer_config_defaults(self):
        """Test default values for Deezer config."""
        config = DeezerConfig()
        assert config.quality == 2
        assert config.arl == ""
        assert config.use_deezloader is True
        assert config.deezloader_warnings is True

    @pytest.mark.parametrize("quality", [0, 1, 2])
    def test_deezer_quality_validation_valid(self, quality):
        """Test valid Deezer quality values."""
        config = DeezerConfig(quality=quality)
        assert config.quality == quality

    @pytest.mark.parametrize("quality", [-1, 3, 4, 10])
    def test_deezer_quality_validation_invalid(self, quality):
        """Test invalid Deezer quality values."""
        with pytest.raises(ValueError, match="Deezer quality must be between 0-2"):
            DeezerConfig(quality=quality)

    def test_deezer_config_inheritance(self, deezer_config):
        """Test that DeezerConfig inherits from ServiceConfig."""
        assert hasattr(deezer_config, "quality")

    @patch("ripstream.core.utils.decode_secret")
    def test_deezer_get_decoded_credentials(self, mock_decode_secret, deezer_config):
        """Test getting decoded credentials for Deezer."""
        mock_decode_secret.return_value = "decoded_arl_token"

        credentials = deezer_config.get_decoded_credentials()

        assert credentials["arl"] == "decoded_arl_token"
        assert credentials["use_deezloader"] is False
        assert credentials["deezloader_warnings"] is False
        assert "quality" not in credentials
        mock_decode_secret.assert_called_once_with("test_arl_token")

    def test_deezer_config_custom_values(self, deezer_config):
        """Test Deezer config with custom values."""
        assert deezer_config.quality == 1
        assert deezer_config.arl == "test_arl_token"
        assert deezer_config.use_deezloader is False
        assert deezer_config.deezloader_warnings is False


class TestSoundCloudConfig:
    """Test the SoundCloudConfig class."""

    @pytest.fixture
    def soundcloud_config(self):
        """Create a SoundCloud config for testing."""
        return SoundCloudConfig(client_id="test_client_id", app_version="1.2.3")

    def test_soundcloud_config_defaults(self):
        """Test default values for SoundCloud config."""
        config = SoundCloudConfig()
        assert config.quality == 0
        assert config.client_id == ""
        assert config.app_version == ""

    def test_soundcloud_quality_validation_valid(self):
        """Test valid SoundCloud quality value."""
        config = SoundCloudConfig(quality=0)
        assert config.quality == 0

    @pytest.mark.parametrize("quality", [-1, 1, 2, 3])
    def test_soundcloud_quality_validation_invalid(self, quality):
        """Test invalid SoundCloud quality values."""
        with pytest.raises(ValueError, match="SoundCloud quality must be 0"):
            SoundCloudConfig(quality=quality)

    def test_soundcloud_config_inheritance(self, soundcloud_config):
        """Test that SoundCloudConfig inherits from ServiceConfig."""
        assert hasattr(soundcloud_config, "quality")

    def test_soundcloud_get_decoded_credentials(self, soundcloud_config):
        """Test getting decoded credentials for SoundCloud."""
        credentials = soundcloud_config.get_decoded_credentials()

        assert credentials["client_id"] == "test_client_id"
        assert credentials["app_version"] == "1.2.3"
        assert "quality" not in credentials

    def test_soundcloud_config_custom_values(self, soundcloud_config):
        """Test SoundCloud config with custom values."""
        assert soundcloud_config.client_id == "test_client_id"
        assert soundcloud_config.app_version == "1.2.3"


class TestYouTubeConfig:
    """Test the YouTubeConfig class."""

    @pytest.fixture
    def youtube_config(self):
        """Create a YouTube config for testing."""
        return YouTubeConfig(
            download_videos=True, video_downloads_folder=Path("/custom/video/path")
        )

    def test_youtube_config_defaults(self):
        """Test default values for YouTube config."""
        config = YouTubeConfig()
        assert config.quality == 0
        assert config.download_videos is False
        assert config.download_booklets is False
        assert isinstance(config.video_downloads_folder, Path)
        assert "YouTubeVideos" in str(config.video_downloads_folder)

    def test_youtube_quality_validation_valid(self):
        """Test valid YouTube quality value."""
        config = YouTubeConfig(quality=0)
        assert config.quality == 0

    @pytest.mark.parametrize("quality", [-1, 1, 2, 3])
    def test_youtube_quality_validation_invalid(self, quality):
        """Test invalid YouTube quality values."""
        with pytest.raises(ValueError, match="YouTube quality must be 0"):
            YouTubeConfig(quality=quality)

    def test_youtube_config_inheritance(self, youtube_config):
        """Test that YouTubeConfig inherits from correct base classes."""
        # Should have ServiceConfig fields
        assert hasattr(youtube_config, "quality")

        # Should have DownloadableConfig fields
        assert hasattr(youtube_config, "download_videos")
        assert hasattr(youtube_config, "download_booklets")

    def test_youtube_video_path_validation_string(self):
        """Test that string video paths are converted to Path objects."""
        config = YouTubeConfig.model_validate({
            "video_downloads_folder": "~/Videos/YouTube"
        })
        assert isinstance(config.video_downloads_folder, Path)
        assert config.video_downloads_folder.is_absolute()

    def test_youtube_video_path_validation_path_object(self):
        """Test that Path objects are preserved."""
        original_path = Path("/tmp/videos").resolve()
        config = YouTubeConfig(video_downloads_folder=original_path)
        assert config.video_downloads_folder == original_path

    def test_youtube_get_decoded_credentials(self, youtube_config):
        """Test getting decoded credentials for YouTube."""
        credentials = youtube_config.get_decoded_credentials()

        assert credentials["download_videos"] is True
        assert credentials["download_booklets"] is False
        assert isinstance(credentials["video_downloads_folder"], Path)
        assert "quality" not in credentials

    def test_youtube_config_custom_values(self, youtube_config):
        """Test YouTube config with custom values."""
        assert youtube_config.download_videos is True
        assert isinstance(youtube_config.video_downloads_folder, Path)


class TestServiceConfigIntegration:
    """Integration tests for service configurations."""

    @pytest.mark.parametrize(
        ("config_class", "quality_range"),
        [
            (QobuzConfig, (1, 4)),
            (TidalConfig, (0, 3)),
            (DeezerConfig, (0, 2)),
            (SoundCloudConfig, (0, 0)),
            (YouTubeConfig, (0, 0)),
        ],
    )
    def test_service_quality_ranges(self, config_class, quality_range):
        """Test that each service has correct quality range validation."""
        min_quality, max_quality = quality_range

        # Test valid qualities
        for quality in range(min_quality, max_quality + 1):
            config = config_class(quality=quality)
            assert config.quality == quality

        # Test invalid qualities (below range)
        if min_quality > 0:
            with pytest.raises(ValueError, match="quality must be"):
                config_class(quality=min_quality - 1)

        # Test invalid qualities (above range)
        with pytest.raises(ValueError, match="quality must be"):
            config_class(quality=max_quality + 1)

    def test_all_services_have_quality_field(self):
        """Test that all service configs have a quality field."""
        service_classes = [
            QobuzConfig,
            TidalConfig,
            DeezerConfig,
            SoundCloudConfig,
            YouTubeConfig,
        ]

        for service_class in service_classes:
            config = service_class()
            assert hasattr(config, "quality")
            assert isinstance(config.quality, int)

    @pytest.mark.parametrize("config_class", [QobuzConfig, TidalConfig, YouTubeConfig])
    def test_downloadable_services_have_download_fields(self, config_class):
        """Test that downloadable services have download-related fields."""
        config = config_class()
        assert hasattr(config, "download_videos")
        assert hasattr(config, "download_booklets")

    @pytest.mark.parametrize(
        "config_class", [DeezerConfig, SoundCloudConfig, YouTubeConfig]
    )
    def test_services_with_custom_credentials_have_get_decoded_method(
        self, config_class
    ):
        """Test that services with custom credentials have get_decoded_credentials method."""
        config = config_class()
        assert hasattr(config, "get_decoded_credentials")
        assert callable(config.get_decoded_credentials)

        # Should return a dictionary
        credentials = config.get_decoded_credentials()
        assert isinstance(credentials, dict)


if __name__ == "__main__":
    pytest.main([__file__])
