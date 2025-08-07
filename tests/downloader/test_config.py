# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for downloader configuration classes."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ripstream.downloader.config import DownloadBehaviorSettings, DownloaderConfig
from ripstream.downloader.enums import RetryStrategy


class TestDownloadBehaviorSettings:
    """Test the DownloadBehaviorSettings class."""

    @pytest.fixture
    def default_settings(self):
        """Create default download behavior settings."""
        return DownloadBehaviorSettings()

    def test_download_behavior_settings_defaults(self, default_settings):
        """Test DownloadBehaviorSettings with default values."""
        assert default_settings.timeout_seconds == 30.0
        assert default_settings.chunk_size == 8192
        assert default_settings.max_concurrent_chunks == 1
        assert default_settings.max_retries == 3
        assert default_settings.retry_strategy == RetryStrategy.EXPONENTIAL
        assert default_settings.retry_delay == 1.0
        assert default_settings.retry_backoff_factor == 2.0
        assert default_settings.max_requests_per_second == 10.0
        assert default_settings.rate_limit_burst == 5
        assert default_settings.overwrite_existing is False
        assert default_settings.create_directories is True
        assert default_settings.temp_file_suffix == ".tmp"
        assert default_settings.verify_checksums is True
        assert default_settings.verify_file_size is True

    def test_download_behavior_settings_custom_values(self):
        """Test DownloadBehaviorSettings with custom values."""
        settings = DownloadBehaviorSettings(
            timeout_seconds=60.0,
            chunk_size=16384,
            max_concurrent_chunks=4,
            max_retries=5,
            retry_strategy=RetryStrategy.LINEAR,
            retry_delay=2.0,
            retry_backoff_factor=3.0,
            max_requests_per_second=20.0,
            rate_limit_burst=10,
            overwrite_existing=True,
            create_directories=False,
            temp_file_suffix=".download",
            verify_checksums=False,
            verify_file_size=False,
        )

        assert settings.timeout_seconds == 60.0
        assert settings.chunk_size == 16384
        assert settings.max_concurrent_chunks == 4
        assert settings.max_retries == 5
        assert settings.retry_strategy == RetryStrategy.LINEAR
        assert settings.retry_delay == 2.0
        assert settings.retry_backoff_factor == 3.0
        assert settings.max_requests_per_second == 20.0
        assert settings.rate_limit_burst == 10
        assert settings.overwrite_existing is True
        assert settings.create_directories is False
        assert settings.temp_file_suffix == ".download"
        assert settings.verify_checksums is False
        assert settings.verify_file_size is False

    @pytest.mark.parametrize(
        ("field_name", "invalid_value", "expected_error"),
        [
            ("timeout_seconds", 0.0, "Time values must be positive"),
            ("timeout_seconds", -1.0, "Time values must be positive"),
            ("retry_delay", 0.0, "Time values must be positive"),
            ("retry_delay", -5.0, "Time values must be positive"),
            ("chunk_size", 0, "Integer values must be positive"),
            ("chunk_size", -1, "Integer values must be positive"),
            ("max_concurrent_chunks", 0, "Integer values must be positive"),
            ("max_concurrent_chunks", -5, "Integer values must be positive"),
            ("max_retries", 0, "Integer values must be positive"),
            ("max_retries", -3, "Integer values must be positive"),
            ("max_requests_per_second", 0.0, "Rate limit must be positive"),
            ("max_requests_per_second", -10.0, "Rate limit must be positive"),
        ],
    )
    def test_download_settings_validation_errors(
        self, field_name, invalid_value, expected_error
    ):
        """Test that invalid values raise appropriate errors."""
        with pytest.raises(ValueError, match=expected_error):
            DownloadBehaviorSettings(**{field_name: invalid_value})

    @pytest.mark.parametrize(
        ("field_name", "valid_value"),
        [
            ("timeout_seconds", 1.0),
            ("timeout_seconds", 300.0),
            ("retry_delay", 0.1),
            ("retry_delay", 60.0),
            ("chunk_size", 1),
            ("chunk_size", 65536),
            ("max_concurrent_chunks", 1),
            ("max_concurrent_chunks", 10),
            ("max_retries", 1),
            ("max_retries", 10),
            ("max_requests_per_second", 0.1),
            ("max_requests_per_second", 100.0),
        ],
    )
    def test_download_settings_valid_values(self, field_name, valid_value):
        """Test that valid values are accepted."""
        settings = DownloadBehaviorSettings(**{field_name: valid_value})
        assert getattr(settings, field_name) == valid_value


class TestDownloaderConfig:
    """Test the DownloaderConfig class."""

    @pytest.fixture
    def default_config(self):
        """Create default downloader config."""
        return DownloaderConfig()

    def test_downloader_config_defaults(self, default_config):
        """Test DownloaderConfig with default values."""
        assert default_config.download_directory == Path("./downloads")
        assert default_config.temp_directory == Path("./temp")
        assert default_config.max_concurrent_downloads == 3
        assert default_config.queue_size_limit == 1000
        assert isinstance(default_config.default_behavior, DownloadBehaviorSettings)
        assert default_config.user_agent == "RipStream/1.0"
        assert default_config.session_timeout == 300.0
        assert default_config.min_free_space_mb == 100
        assert default_config.cleanup_temp_files is True
        assert default_config.log_progress_interval == 1.0
        assert default_config.log_level == "INFO"
        assert default_config.enable_resume is True
        assert default_config.enable_compression is True
        assert default_config.verify_ssl is True
        assert default_config.custom_headers == {}
        assert default_config.source_settings == {}

    def test_downloader_config_custom_values(self):
        """Test DownloaderConfig with custom values."""
        config = DownloaderConfig(
            download_directory=Path("/custom/downloads"),
            temp_directory=Path("/custom/temp"),
            max_concurrent_downloads=5,
            queue_size_limit=500,
            user_agent="CustomAgent/2.0",
            session_timeout=600.0,
            min_free_space_mb=200,
            cleanup_temp_files=False,
            log_progress_interval=2.0,
            log_level="DEBUG",
            enable_resume=False,
            enable_compression=False,
            verify_ssl=False,
            custom_headers={"X-Custom": "value"},
            source_settings={"qobuz": {"timeout": 60}},
        )

        assert config.download_directory == Path("/custom/downloads")
        assert config.temp_directory == Path("/custom/temp")
        assert config.max_concurrent_downloads == 5
        assert config.queue_size_limit == 500
        assert config.user_agent == "CustomAgent/2.0"
        assert config.session_timeout == 600.0
        assert config.min_free_space_mb == 200
        assert config.cleanup_temp_files is False
        assert config.log_progress_interval == 2.0
        assert config.log_level == "DEBUG"
        assert config.enable_resume is False
        assert config.enable_compression is False
        assert config.verify_ssl is False
        assert config.custom_headers == {"X-Custom": "value"}
        assert config.source_settings == {"qobuz": {"timeout": 60}}

    @pytest.mark.parametrize(
        ("field_name", "invalid_value", "expected_error"),
        [
            ("max_concurrent_downloads", 0, "Integer values must be positive"),
            ("max_concurrent_downloads", -1, "Integer values must be positive"),
            ("queue_size_limit", 0, "Integer values must be positive"),
            ("queue_size_limit", -5, "Integer values must be positive"),
            ("min_free_space_mb", 0, "Integer values must be positive"),
            ("min_free_space_mb", -10, "Integer values must be positive"),
            ("session_timeout", 0.0, "Time values must be positive"),
            ("session_timeout", -1.0, "Time values must be positive"),
            ("log_progress_interval", 0.0, "Time values must be positive"),
            ("log_progress_interval", -5.0, "Time values must be positive"),
        ],
    )
    def test_download_config_validation_errors(
        self, field_name, invalid_value, expected_error
    ):
        """Test that invalid values raise appropriate errors."""
        with pytest.raises(ValueError, match=expected_error):
            DownloaderConfig(**{field_name: invalid_value})

    @pytest.mark.parametrize(
        ("log_level", "expected"),
        [
            ("debug", "DEBUG"),
            ("INFO", "INFO"),
            ("warning", "WARNING"),
            ("ERROR", "ERROR"),
            ("critical", "CRITICAL"),
        ],
    )
    def test_download_config_log_level_validation(self, log_level, expected):
        """Test log level validation and normalization."""
        config = DownloaderConfig(log_level=log_level)
        assert config.log_level == expected

    @pytest.mark.parametrize("invalid_log_level", ["INVALID", "test", "LOG", ""])
    def test_download_config_invalid_log_level(self, invalid_log_level):
        """Test that invalid log levels raise errors."""
        with pytest.raises(ValueError, match="Log level must be one of"):
            DownloaderConfig(log_level=invalid_log_level)

    def test_get_behavior_for_source_default(self, default_config):
        """Test getting default behavior settings for a source."""
        settings = default_config.get_behavior_for_source("unknown_source")
        assert isinstance(settings, DownloadBehaviorSettings)
        assert settings.timeout_seconds == 30.0  # Default value

    def test_get_behavior_for_source_with_overrides(self, default_config):
        """Test getting behavior settings for a source with overrides."""
        default_config.source_settings["qobuz"] = {
            "timeout_seconds": 60.0,
            "max_retries": 5,
            "verify_checksums": False,
        }

        settings = default_config.get_behavior_for_source("qobuz")
        assert settings.timeout_seconds == 60.0
        assert settings.max_retries == 5
        assert settings.verify_checksums is False
        # Other settings should remain default
        assert settings.chunk_size == 8192
        assert settings.retry_strategy == RetryStrategy.EXPONENTIAL

    def test_get_behavior_for_source_unknown_field(self, default_config):
        """Test that unknown fields in source settings are ignored."""
        default_config.source_settings["test"] = {
            "unknown_field": "value",
            "timeout_seconds": 45.0,
        }

        settings = default_config.get_behavior_for_source("test")
        assert settings.timeout_seconds == 45.0
        # Should not have unknown_field attribute
        assert not hasattr(settings, "unknown_field")

    @patch("pathlib.Path.mkdir")
    def test_ensure_directories(self, mock_mkdir, default_config):
        """Test ensuring directories exist."""
        default_config.ensure_directories()

        # Should call mkdir on both directories
        assert mock_mkdir.call_count == 2
        mock_mkdir.assert_any_call(parents=True, exist_ok=True)

    @pytest.mark.parametrize(
        ("filename", "subfolder", "expected_path"),
        [
            ("test.mp3", None, Path("./downloads/test.mp3")),
            ("album.flac", "Artist/Album", Path("./downloads/Artist/Album/album.flac")),
            ("track.wav", "Music", Path("./downloads/Music/track.wav")),
        ],
    )
    def test_get_download_path(
        self, default_config, filename, subfolder, expected_path
    ):
        """Test getting download path for files."""
        result = default_config.get_download_path(filename, subfolder)
        assert result == expected_path

    @pytest.mark.parametrize(
        ("filename", "expected_path"),
        [
            ("test.mp3", Path("./temp/test.mp3.tmp")),
            ("album.flac", Path("./temp/album.flac.tmp")),
            ("track.wav", Path("./temp/track.wav.tmp")),
        ],
    )
    def test_get_temp_path(self, default_config, filename, expected_path):
        """Test getting temporary file path."""
        result = default_config.get_temp_path(filename)
        assert result == expected_path

    def test_add_source_setting_new_source(self, default_config):
        """Test adding a setting for a new source."""
        default_config.add_source_setting("qobuz", "timeout", 60)
        assert default_config.source_settings["qobuz"]["timeout"] == 60

    def test_add_source_setting_existing_source(self, default_config):
        """Test adding a setting for an existing source."""
        default_config.source_settings["qobuz"] = {"existing": "value"}
        default_config.add_source_setting("qobuz", "timeout", 60)

        assert default_config.source_settings["qobuz"]["existing"] == "value"
        assert default_config.source_settings["qobuz"]["timeout"] == 60

    def test_remove_source_setting_specific_key(self, default_config):
        """Test removing a specific setting from a source."""
        default_config.source_settings["qobuz"] = {
            "timeout": 60,
            "retries": 3,
        }

        default_config.remove_source_setting("qobuz", "timeout")

        assert "timeout" not in default_config.source_settings["qobuz"]
        assert "retries" in default_config.source_settings["qobuz"]

    def test_remove_source_setting_all_keys(self, default_config):
        """Test removing all settings for a source."""
        default_config.source_settings["qobuz"] = {
            "timeout": 60,
            "retries": 3,
        }

        default_config.remove_source_setting("qobuz")

        assert "qobuz" not in default_config.source_settings

    def test_remove_source_setting_cleanup_empty(self, default_config):
        """Test that empty source configs are cleaned up."""
        default_config.source_settings["qobuz"] = {"timeout": 60}

        default_config.remove_source_setting("qobuz", "timeout")

        assert "qobuz" not in default_config.source_settings

    def test_remove_source_setting_nonexistent(self, default_config):
        """Test removing settings from non-existent sources."""
        # Should not raise any errors
        default_config.remove_source_setting("nonexistent", "key")
        default_config.remove_source_setting("nonexistent")

    def test_to_dict(self, default_config):
        """Test converting config to dictionary."""
        config_dict = default_config.to_dict()

        assert isinstance(config_dict, dict)
        assert "download_directory" in config_dict
        assert "temp_directory" in config_dict
        assert "max_concurrent_downloads" in config_dict
        assert "default_behavior" in config_dict

    def test_from_dict(self, default_config):
        """Test creating config from dictionary."""
        config_dict = default_config.to_dict()
        new_config = DownloaderConfig.from_dict(config_dict)

        assert new_config.download_directory == default_config.download_directory
        assert new_config.temp_directory == default_config.temp_directory
        assert (
            new_config.max_concurrent_downloads
            == default_config.max_concurrent_downloads
        )
        assert new_config.log_level == default_config.log_level

    def test_from_dict_custom_values(self):
        """Test creating config from dictionary with custom values."""
        config_dict = {
            "download_directory": "./custom/downloads",
            "temp_directory": "./custom/temp",
            "max_concurrent_downloads": 5,
            "log_level": "DEBUG",
            "source_settings": {"qobuz": {"timeout": 60}},
        }

        config = DownloaderConfig.from_dict(config_dict)

        assert config.download_directory == Path("./custom/downloads")
        assert config.temp_directory == Path("./custom/temp")
        assert config.max_concurrent_downloads == 5
        assert config.log_level == "DEBUG"
        assert config.source_settings == {"qobuz": {"timeout": 60}}
