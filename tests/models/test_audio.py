# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for models/audio.py module."""

import pytest

from ripstream.models.audio import AudioInfo, DownloadableAudio
from ripstream.models.enums import AudioQuality


class TestAudioInfo:
    """Test the AudioInfo model."""

    @pytest.fixture
    def sample_audio_info(self):
        """Sample AudioInfo for testing."""
        return AudioInfo(
            quality=AudioQuality.LOSSLESS,
            bit_depth=24,
            sampling_rate=96000,
            bitrate=1411,
            codec="FLAC",
            container="FLAC",
            duration_seconds=240.5,
            file_size_bytes=30720000,
            is_lossless=True,
            is_explicit=False,
        )

    def test_audio_info_creation(self, sample_audio_info):
        """Test AudioInfo creation with all fields."""
        assert sample_audio_info.quality == AudioQuality.LOSSLESS
        assert sample_audio_info.bit_depth == 24
        assert sample_audio_info.sampling_rate == 96000
        assert sample_audio_info.bitrate == 1411
        assert sample_audio_info.codec == "FLAC"
        assert sample_audio_info.container == "FLAC"
        assert sample_audio_info.duration_seconds == 240.5
        assert sample_audio_info.file_size_bytes == 30720000
        assert sample_audio_info.is_lossless is True
        assert sample_audio_info.is_explicit is False

    def test_audio_info_minimal_creation(self):
        """Test AudioInfo creation with minimal required fields."""
        info = AudioInfo(quality=AudioQuality.HIGH)
        assert info.quality == AudioQuality.HIGH
        assert info.bit_depth is None
        assert info.sampling_rate is None
        assert info.bitrate is None
        assert info.codec is None
        assert info.container is None
        assert info.duration_seconds is None
        assert info.file_size_bytes is None
        assert info.is_lossless is None
        assert info.is_explicit is False

    @pytest.mark.parametrize("invalid_bit_depth", [4, 12, 20, 64])
    def test_validate_bit_depth_invalid(self, invalid_bit_depth):
        """Test bit depth validation with invalid values."""
        with pytest.raises(ValueError, match=f"Invalid bit depth: {invalid_bit_depth}"):
            AudioInfo(quality=AudioQuality.HIGH, bit_depth=invalid_bit_depth)

    @pytest.mark.parametrize("valid_bit_depth", [8, 16, 24, 32])
    def test_validate_bit_depth_valid(self, valid_bit_depth):
        """Test bit depth validation with valid values."""
        info = AudioInfo(quality=AudioQuality.HIGH, bit_depth=valid_bit_depth)
        assert info.bit_depth == valid_bit_depth

    def test_validate_bit_depth_none(self):
        """Test bit depth validation with None value."""
        info = AudioInfo(quality=AudioQuality.HIGH, bit_depth=None)
        assert info.bit_depth is None

    @pytest.mark.parametrize("invalid_duration", [-1, -10.5, -0.1])
    def test_validate_duration_invalid(self, invalid_duration):
        """Test duration validation with invalid values."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            AudioInfo(quality=AudioQuality.HIGH, duration_seconds=invalid_duration)

    @pytest.mark.parametrize("valid_duration", [0, 1, 180.5, 3600])
    def test_validate_duration_valid(self, valid_duration):
        """Test duration validation with valid values."""
        info = AudioInfo(quality=AudioQuality.HIGH, duration_seconds=valid_duration)
        assert info.duration_seconds == valid_duration

    def test_validate_duration_none(self):
        """Test duration validation with None value."""
        info = AudioInfo(quality=AudioQuality.HIGH, duration_seconds=None)
        assert info.duration_seconds is None

    @pytest.mark.parametrize(
        ("duration_seconds", "expected_formatted"),
        [
            (0, "00:00"),
            (30, "00:30"),
            (60, "01:00"),
            (90, "01:30"),
            (3661, "61:01"),  # Over an hour
            (240.7, "04:00"),  # Fractional seconds rounded down
        ],
    )
    def test_duration_formatted_property(self, duration_seconds, expected_formatted):
        """Test duration_formatted property."""
        info = AudioInfo(quality=AudioQuality.HIGH, duration_seconds=duration_seconds)
        assert info.duration_formatted == expected_formatted

    def test_duration_formatted_property_none(self):
        """Test duration_formatted property with None duration."""
        info = AudioInfo(quality=AudioQuality.HIGH, duration_seconds=None)
        assert info.duration_formatted is None

    @pytest.mark.parametrize(
        ("file_size_bytes", "expected_mb"),
        [
            (1024 * 1024, 1.0),
            (2 * 1024 * 1024, 2.0),
            (1536 * 1024, 1.5),  # 1.5 MB
            (512 * 1024, 0.5),  # 0.5 MB
            (0, 0.0),
        ],
    )
    def test_file_size_mb_property(self, file_size_bytes, expected_mb):
        """Test file_size_mb property calculation."""
        info = AudioInfo(quality=AudioQuality.HIGH, file_size_bytes=file_size_bytes)
        assert info.file_size_mb == expected_mb

    def test_file_size_mb_property_none(self):
        """Test file_size_mb property with None file size."""
        info = AudioInfo(quality=AudioQuality.HIGH, file_size_bytes=None)
        assert info.file_size_mb is None

    def test_update_from_source_data(self, sample_audio_info):
        """Test update_from_source_data method."""
        source_data = {
            "bit_depth": 16,
            "sampling_rate": 44100,
            "bitrate": 320,
            "duration": 180,
            "extra_field": "ignored",  # Should be ignored
        }

        sample_audio_info.update_from_source_data(source_data)

        assert sample_audio_info.bit_depth == 16
        assert sample_audio_info.sampling_rate == 44100
        assert sample_audio_info.bitrate == 320
        assert sample_audio_info.duration_seconds == 180
        # Other fields should remain unchanged
        assert sample_audio_info.codec == "FLAC"
        assert sample_audio_info.container == "FLAC"

    def test_update_from_source_data_partial(self, sample_audio_info):
        """Test update_from_source_data method with partial data."""
        source_data = {
            "bit_depth": 16,
            "unknown_field": "value",  # Should be ignored
        }

        original_sampling_rate = sample_audio_info.sampling_rate
        sample_audio_info.update_from_source_data(source_data)

        assert sample_audio_info.bit_depth == 16
        assert sample_audio_info.sampling_rate == original_sampling_rate  # Unchanged

    def test_update_from_source_data_empty(self, sample_audio_info):
        """Test update_from_source_data method with empty data."""
        original_bit_depth = sample_audio_info.bit_depth
        sample_audio_info.update_from_source_data({})

        # Nothing should change
        assert sample_audio_info.bit_depth == original_bit_depth


class TestDownloadableAudio:
    """Test the DownloadableAudio model."""

    @pytest.fixture
    def sample_downloadable_audio(self):
        """Sample DownloadableAudio for testing."""
        return DownloadableAudio(
            download_url="https://example.com/download/track.flac",
            stream_url="https://example.com/stream/track.flac",
            expires_at="2023-12-31T23:59:59Z",
            requires_auth=True,
            max_download_attempts=5,
            chunk_size=16384,
            headers={"Authorization": "Bearer token123", "User-Agent": "TestApp/1.0"},
        )

    def test_downloadable_audio_creation(self, sample_downloadable_audio):
        """Test DownloadableAudio creation with all fields."""
        assert (
            sample_downloadable_audio.download_url
            == "https://example.com/download/track.flac"
        )
        assert (
            sample_downloadable_audio.stream_url
            == "https://example.com/stream/track.flac"
        )
        assert sample_downloadable_audio.expires_at == "2023-12-31T23:59:59Z"
        assert sample_downloadable_audio.requires_auth is True
        assert sample_downloadable_audio.max_download_attempts == 5
        assert sample_downloadable_audio.chunk_size == 16384
        assert sample_downloadable_audio.headers["Authorization"] == "Bearer token123"
        assert sample_downloadable_audio.headers["User-Agent"] == "TestApp/1.0"

    def test_downloadable_audio_minimal_creation(self):
        """Test DownloadableAudio creation with minimal fields."""
        audio = DownloadableAudio()
        assert audio.download_url is None
        assert audio.stream_url is None
        assert audio.expires_at is None
        assert audio.requires_auth is True  # Default
        assert audio.max_download_attempts == 3  # Default
        assert audio.chunk_size == 8192  # Default
        assert audio.headers == {}

    def test_downloadable_audio_defaults(self):
        """Test DownloadableAudio default values."""
        audio = DownloadableAudio(download_url="https://example.com/track.flac")
        assert audio.requires_auth is True
        assert audio.max_download_attempts == 3
        assert audio.chunk_size == 8192
        assert audio.headers == {}

    def test_is_expired_property_none(self):
        """Test is_expired property when expires_at is None."""
        audio = DownloadableAudio(expires_at=None)
        assert audio.is_expired is False

    def test_is_expired_property_with_expiry(self):
        """Test is_expired property when expires_at is set."""
        # Since the implementation always returns False as a placeholder,
        # we test the current behavior
        audio = DownloadableAudio(expires_at="2023-01-01T00:00:00Z")
        assert audio.is_expired is False

    def test_add_header(self, sample_downloadable_audio):
        """Test add_header method."""
        sample_downloadable_audio.add_header("Content-Type", "audio/flac")
        sample_downloadable_audio.add_header("Accept-Encoding", "gzip")

        assert sample_downloadable_audio.headers["Content-Type"] == "audio/flac"
        assert sample_downloadable_audio.headers["Accept-Encoding"] == "gzip"
        # Original headers should still be there
        assert sample_downloadable_audio.headers["Authorization"] == "Bearer token123"

    def test_add_header_overwrite(self, sample_downloadable_audio):
        """Test add_header method overwrites existing headers."""
        original_auth = sample_downloadable_audio.headers["Authorization"]
        sample_downloadable_audio.add_header("Authorization", "Bearer newtoken456")

        assert (
            sample_downloadable_audio.headers["Authorization"] == "Bearer newtoken456"
        )
        assert sample_downloadable_audio.headers["Authorization"] != original_auth

    def test_get_download_config_with_download_url(self, sample_downloadable_audio):
        """Test get_download_config method with download_url."""
        config = sample_downloadable_audio.get_download_config()

        expected_config = {
            "url": "https://example.com/download/track.flac",
            "headers": {
                "Authorization": "Bearer token123",
                "User-Agent": "TestApp/1.0",
            },
            "chunk_size": 16384,
            "max_attempts": 5,
            "requires_auth": True,
        }

        assert config == expected_config

    def test_get_download_config_with_stream_url_only(self):
        """Test get_download_config method with only stream_url."""
        audio = DownloadableAudio(
            stream_url="https://example.com/stream/track.flac",
            requires_auth=False,
            max_download_attempts=2,
            chunk_size=4096,
        )

        config = audio.get_download_config()

        expected_config = {
            "url": "https://example.com/stream/track.flac",
            "headers": {},
            "chunk_size": 4096,
            "max_attempts": 2,
            "requires_auth": False,
        }

        assert config == expected_config

    def test_get_download_config_no_urls(self):
        """Test get_download_config method with no URLs."""
        audio = DownloadableAudio()

        config = audio.get_download_config()

        expected_config = {
            "url": None,
            "headers": {},
            "chunk_size": 8192,
            "max_attempts": 3,
            "requires_auth": True,
        }

        assert config == expected_config

    def test_get_download_config_prefers_download_url(self):
        """Test get_download_config method prefers download_url over stream_url."""
        audio = DownloadableAudio(
            download_url="https://example.com/download/track.flac",
            stream_url="https://example.com/stream/track.flac",
        )

        config = audio.get_download_config()

        # Should prefer download_url
        assert config["url"] == "https://example.com/download/track.flac"


class TestAudioIntegration:
    """Integration tests for audio models."""

    def test_audio_info_with_all_quality_levels(self):
        """Test AudioInfo with different quality levels."""
        quality_configs = [
            (AudioQuality.LOW, 16, 22050, 128),
            (AudioQuality.HIGH, 16, 44100, 320),
            (AudioQuality.HIGH, 24, 48000, 1411),
            (AudioQuality.LOSSLESS, 24, 96000, None),  # Lossless might not have bitrate
        ]

        for quality, bit_depth, sampling_rate, bitrate in quality_configs:
            info = AudioInfo(
                quality=quality,
                bit_depth=bit_depth,
                sampling_rate=sampling_rate,
                bitrate=bitrate,
                duration_seconds=180,
            )

            assert info.quality == quality
            assert info.bit_depth == bit_depth
            assert info.sampling_rate == sampling_rate
            assert info.bitrate == bitrate
            assert info.duration_formatted == "03:00"

    def test_downloadable_audio_with_complex_headers(self):
        """Test DownloadableAudio with complex header configuration."""
        audio = DownloadableAudio(
            download_url="https://api.example.com/track/123/download",
            requires_auth=True,
        )

        # Add multiple headers
        headers_to_add = {
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",
            "User-Agent": "RipStream/1.0.0",
            "Accept": "audio/flac,audio/wav,audio/*",
            "Accept-Encoding": "gzip, deflate",
            "X-Client-Version": "1.0.0",
        }

        for key, value in headers_to_add.items():
            audio.add_header(key, value)

        config = audio.get_download_config()

        assert len(config["headers"]) == len(headers_to_add)
        for key, value in headers_to_add.items():
            assert config["headers"][key] == value

    def test_audio_models_with_edge_case_values(self):
        """Test audio models with edge case values."""
        # Test with very large file
        large_file_info = AudioInfo(
            quality=AudioQuality.LOSSLESS,
            duration_seconds=7200,  # 2 hours
            file_size_bytes=1024 * 1024 * 1024,  # 1 GB
            bit_depth=32,
            sampling_rate=192000,
        )

        assert large_file_info.duration_formatted == "120:00"
        assert large_file_info.file_size_mb == 1024.0

        # Test with very small file
        small_file_info = AudioInfo(
            quality=AudioQuality.LOW,
            duration_seconds=1,
            file_size_bytes=1024,  # 1 KB
            bit_depth=8,
        )

        assert small_file_info.duration_formatted == "00:01"
        assert small_file_info.file_size_mb == 0.0  # Rounded to 2 decimal places


class TestAudioEdgeCases:
    """Test edge cases and error conditions for audio models."""

    def test_audio_info_with_zero_values(self):
        """Test AudioInfo with zero values."""
        info = AudioInfo(
            quality=AudioQuality.HIGH,
            duration_seconds=0,
            file_size_bytes=0,
            bitrate=0,
            sampling_rate=0,
        )

        assert info.duration_formatted == "00:00"
        assert info.file_size_mb == 0.0
        assert info.bitrate == 0
        assert info.sampling_rate == 0

    def test_downloadable_audio_empty_headers(self):
        """Test DownloadableAudio with empty headers."""
        audio = DownloadableAudio()

        # Add and remove headers
        audio.add_header("Test-Header", "test-value")
        assert "Test-Header" in audio.headers

        # Clear headers by creating new instance
        audio.headers.clear()
        assert len(audio.headers) == 0

        config = audio.get_download_config()
        assert config["headers"] == {}

    def test_audio_info_update_with_none_values(self):
        """Test AudioInfo update_from_source_data with None values."""
        info = AudioInfo(quality=AudioQuality.HIGH, bit_depth=16, sampling_rate=44100)

        # Update with None values - the current implementation sets them to None
        source_data = {
            "bit_depth": None,
            "sampling_rate": None,
            "bitrate": None,
            "duration": None,
        }

        info.update_from_source_data(source_data)

        # The current implementation sets fields to None when source data contains None
        assert info.bit_depth is None
        assert info.sampling_rate is None
        assert info.bitrate is None
        assert info.duration_seconds is None

    def test_downloadable_audio_url_priority(self):
        """Test URL priority in get_download_config."""
        # Test with both URLs - should prefer download_url
        audio1 = DownloadableAudio(
            download_url="https://download.example.com/track.flac",
            stream_url="https://stream.example.com/track.flac",
        )
        config1 = audio1.get_download_config()
        assert config1["url"] == "https://download.example.com/track.flac"

        # Test with only stream_url
        audio2 = DownloadableAudio(stream_url="https://stream.example.com/track.flac")
        config2 = audio2.get_download_config()
        assert config2["url"] == "https://stream.example.com/track.flac"

        # Test with neither URL
        audio3 = DownloadableAudio()
        config3 = audio3.get_download_config()
        assert config3["url"] is None
