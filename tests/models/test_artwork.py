# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for models/artwork.py module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ripstream.models.artwork import CoverImage, Covers
from ripstream.models.enums import CoverSize


class TestCoverImage:
    """Test the CoverImage model."""

    @pytest.fixture
    def sample_cover_image(self):
        """Sample CoverImage for testing."""
        return CoverImage(
            url="https://example.com/cover.jpg",
            size=CoverSize.LARGE,
            width=600,
            height=600,
            format="JPEG",
            file_size_bytes=102400,
            local_path="/path/to/cover.jpg",
        )

    def test_cover_image_creation(self, sample_cover_image):
        """Test CoverImage creation with all fields."""
        assert sample_cover_image.url == "https://example.com/cover.jpg"
        assert sample_cover_image.size == CoverSize.LARGE
        assert sample_cover_image.width == 600
        assert sample_cover_image.height == 600
        assert sample_cover_image.format == "JPEG"
        assert sample_cover_image.file_size_bytes == 102400
        assert sample_cover_image.local_path == "/path/to/cover.jpg"

    def test_cover_image_minimal_creation(self):
        """Test CoverImage creation with minimal required fields."""
        image = CoverImage(url="https://example.com/minimal.jpg", size=CoverSize.SMALL)
        assert image.url == "https://example.com/minimal.jpg"
        assert image.size == CoverSize.SMALL
        assert image.width is None
        assert image.height is None
        assert image.format is None
        assert image.file_size_bytes is None
        assert image.local_path is None

    @pytest.mark.parametrize(
        ("width", "height", "expected_ratio"),
        [
            (600, 600, 1.0),
            (800, 600, 800 / 600),
            (300, 400, 0.75),
            (None, 600, None),
            (600, None, None),
        ],
    )
    def test_aspect_ratio_property(self, width, height, expected_ratio):
        """Test aspect_ratio property calculation."""
        image = CoverImage(
            url="https://example.com/test.jpg",
            size=CoverSize.MEDIUM,
            width=width,
            height=height,
        )
        assert image.aspect_ratio == expected_ratio

    def test_aspect_ratio_property_zero_height(self):
        """Test aspect_ratio property with zero height (should be None due to validation)."""
        # Zero height should fail validation, so we test that it raises an error
        with pytest.raises(ValueError, match="Image dimensions must be positive"):
            CoverImage(
                url="https://example.com/test.jpg",
                size=CoverSize.MEDIUM,
                width=600,
                height=0,
            )

    @pytest.mark.parametrize(
        ("width", "height", "expected_square"),
        [
            (600, 600, True),
            (800, 600, False),
            (None, 600, False),
            (600, None, False),
        ],
    )
    def test_is_square_property(self, width, height, expected_square):
        """Test is_square property."""
        image = CoverImage(
            url="https://example.com/test.jpg",
            size=CoverSize.MEDIUM,
            width=width,
            height=height,
        )
        assert image.is_square == expected_square

    @pytest.mark.parametrize(
        ("file_size_bytes", "expected_kb"),
        [
            (1024, 1.0),
            (2048, 2.0),
            (1536, 1.5),
            (None, None),
            (0, 0.0),
        ],
    )
    def test_file_size_kb_property(self, file_size_bytes, expected_kb):
        """Test file_size_kb property calculation."""
        image = CoverImage(
            url="https://example.com/test.jpg",
            size=CoverSize.MEDIUM,
            file_size_bytes=file_size_bytes,
        )
        assert image.file_size_kb == expected_kb

    @pytest.mark.parametrize("invalid_dimension", [-1, 0])
    def test_validate_dimensions_invalid(self, invalid_dimension):
        """Test dimension validation with invalid values."""
        with pytest.raises(ValueError, match="Image dimensions must be positive"):
            CoverImage(
                url="https://example.com/test.jpg",
                size=CoverSize.MEDIUM,
                width=invalid_dimension,
                height=600,
            )

    @pytest.mark.parametrize(
        ("size", "format_ext", "prefix", "expected"),
        [
            (CoverSize.SMALL, "JPEG", "cover", "cover_small.jpeg"),
            (CoverSize.LARGE, "PNG", "album", "album_large.png"),
            (CoverSize.ORIGINAL, "JPG", "cover", "cover.jpg"),
            (CoverSize.MEDIUM, None, "test", "test_medium.jpg"),
        ],
    )
    def test_get_filename(self, size, format_ext, prefix, expected):
        """Test get_filename method."""
        image = CoverImage(
            url="https://example.com/test.jpg", size=size, format=format_ext
        )
        assert image.get_filename(prefix) == expected

    def test_get_filename_with_different_enum_values(self):
        """Test get_filename method with different enum values."""
        # Test that the get_filename method works with all enum values
        test_cases = [
            (CoverSize.SMALL, "test_small.png"),
            (CoverSize.MEDIUM, "test_medium.png"),
            (CoverSize.LARGE, "test_large.png"),
            (CoverSize.ORIGINAL, "test.png"),
        ]

        for size, expected in test_cases:
            image = CoverImage(
                url="https://example.com/test.jpg", size=size, format="PNG"
            )
            result = image.get_filename("test")
            assert result == expected

    def test_get_filename_original_string_size(self):
        """Test get_filename with 'original' string size."""
        image = CoverImage(
            url="https://example.com/test.jpg", size=CoverSize.ORIGINAL, format="PNG"
        )

        # Mock the size to test the original string handling
        image.size = "original"  # type: ignore
        result = image.get_filename("test")
        assert result == "test.png"


class TestCovers:
    """Test the Covers model."""

    @pytest.fixture
    def sample_covers(self):
        """Sample Covers collection for testing."""
        covers = Covers()
        covers.add_image("https://example.com/small.jpg", CoverSize.SMALL, 150, 150)
        covers.add_image("https://example.com/medium.jpg", CoverSize.MEDIUM, 300, 300)
        covers.add_image("https://example.com/large.jpg", CoverSize.LARGE, 600, 600)
        return covers

    def test_covers_creation_empty(self):
        """Test Covers creation with default values."""
        covers = Covers()
        assert covers.images == []
        assert covers.primary_color is None
        assert covers.dominant_colors == []

    def test_covers_creation_with_data(self):
        """Test Covers creation with initial data."""
        covers = Covers(
            primary_color="#FF0000", dominant_colors=["#FF0000", "#00FF00", "#0000FF"]
        )
        assert covers.primary_color == "#FF0000"
        assert covers.dominant_colors == ["#FF0000", "#00FF00", "#0000FF"]

    def test_add_image_method(self):
        """Test add_image method."""
        covers = Covers()
        image = covers.add_image(
            url="https://example.com/test.jpg",
            size=CoverSize.LARGE,
            width=600,
            height=600,
            image_format="JPEG",
            file_size_bytes=102400,
            local_path="/path/to/test.jpg",
        )

        assert len(covers.images) == 1
        assert isinstance(image, CoverImage)
        assert image.url == "https://example.com/test.jpg"
        assert image.size == CoverSize.LARGE
        assert image.width == 600
        assert image.height == 600
        assert image.format == "JPEG"
        assert image.file_size_bytes == 102400
        assert image.local_path == "/path/to/test.jpg"

    def test_get_image_by_size(self, sample_covers):
        """Test get_image method."""
        large_image = sample_covers.get_image(CoverSize.LARGE)
        assert large_image is not None
        assert large_image.size == CoverSize.LARGE
        assert large_image.url == "https://example.com/large.jpg"

        # Test non-existent size
        original_image = sample_covers.get_image(CoverSize.ORIGINAL)
        assert original_image is None

    def test_get_best_image_default_preferences(self, sample_covers):
        """Test get_best_image with default preferences."""
        best_image = sample_covers.get_best_image()
        assert best_image is not None
        assert best_image.size == CoverSize.LARGE  # Should prefer LARGE first

    def test_get_best_image_custom_preferences(self, sample_covers):
        """Test get_best_image with custom preferences."""
        preferred_sizes = [CoverSize.SMALL, CoverSize.MEDIUM]
        best_image = sample_covers.get_best_image(preferred_sizes)
        assert best_image is not None
        assert best_image.size == CoverSize.SMALL  # Should prefer SMALL first

    def test_get_best_image_empty_covers(self):
        """Test get_best_image with empty covers."""
        covers = Covers()
        best_image = covers.get_best_image()
        assert best_image is None

    def test_get_best_image_fallback_to_first(self):
        """Test get_best_image falls back to first image when no preferred size found."""
        covers = Covers()
        covers.add_image("https://example.com/original.jpg", CoverSize.ORIGINAL)

        # Request sizes that don't exist
        preferred_sizes = [CoverSize.SMALL, CoverSize.MEDIUM]
        best_image = covers.get_best_image(preferred_sizes)
        assert best_image is not None
        assert best_image.size == CoverSize.ORIGINAL

    def test_get_largest_image(self, sample_covers):
        """Test get_largest_image method."""
        # Add an ORIGINAL image which should be largest
        sample_covers.add_image("https://example.com/original.jpg", CoverSize.ORIGINAL)

        largest_image = sample_covers.get_largest_image()
        assert largest_image is not None
        assert largest_image.size == CoverSize.ORIGINAL

    def test_get_largest_image_empty_covers(self):
        """Test get_largest_image with empty covers."""
        covers = Covers()
        largest_image = covers.get_largest_image()
        assert largest_image is None

    def test_get_smallest_image(self, sample_covers):
        """Test get_smallest_image method."""
        smallest_image = sample_covers.get_smallest_image()
        assert smallest_image is not None
        assert smallest_image.size == CoverSize.SMALL

    def test_get_smallest_image_empty_covers(self):
        """Test get_smallest_image with empty covers."""
        covers = Covers()
        smallest_image = covers.get_smallest_image()
        assert smallest_image is None

    def test_has_images_property(self, sample_covers):
        """Test has_images property."""
        assert sample_covers.has_images is True

        empty_covers = Covers()
        assert empty_covers.has_images is False

    def test_available_sizes_property(self, sample_covers):
        """Test available_sizes property."""
        sizes = sample_covers.available_sizes
        expected_sizes = [CoverSize.SMALL, CoverSize.MEDIUM, CoverSize.LARGE]
        assert sizes == expected_sizes

    @patch("pathlib.Path.mkdir")
    def test_download_to_directory(self, mock_mkdir, sample_covers):
        """Test download_to_directory method."""
        test_directory = "/test/directory"

        result = sample_covers.download_to_directory(test_directory, "album")

        # Verify directory creation
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify returned paths
        assert len(result) == 3
        assert CoverSize.SMALL in result
        assert CoverSize.MEDIUM in result
        assert CoverSize.LARGE in result

        # Check path format
        assert result[CoverSize.SMALL].endswith("album_small.jpg")
        assert result[CoverSize.MEDIUM].endswith("album_medium.jpg")
        assert result[CoverSize.LARGE].endswith("album_large.jpg")

    def test_set_color_info(self):
        """Test set_color_info method."""
        covers = Covers()
        covers.set_color_info("#FF0000", ["#FF0000", "#00FF00"])

        assert covers.primary_color == "#FF0000"
        assert covers.dominant_colors == ["#FF0000", "#00FF00"]

    def test_set_color_info_no_dominant_colors(self):
        """Test set_color_info with only primary color."""
        covers = Covers()
        covers.set_color_info("#FF0000")

        assert covers.primary_color == "#FF0000"
        assert covers.dominant_colors == []  # Should remain empty


class TestCoversQobuzIntegration:
    """Test Covers integration with Qobuz response parsing."""

    def test_from_qobuz_response_with_get_cover_urls_method(self):
        """Test from_qobuz_response with object that has get_cover_urls method."""
        mock_response = Mock()
        mock_response.get_cover_urls.return_value = {
            "small": "https://example.com/small.jpg",
            "large": "https://example.com/large.jpg",
        }

        covers = Covers.from_qobuz_response(mock_response)

        assert len(covers.images) == 2
        small_image = covers.get_image(CoverSize.SMALL)
        large_image = covers.get_image(CoverSize.LARGE)

        assert small_image is not None
        assert small_image.url == "https://example.com/small.jpg"
        assert large_image is not None
        assert large_image.url == "https://example.com/large.jpg"

    def test_from_qobuz_response_with_image_attribute(self):
        """Test from_qobuz_response with object that has image attribute."""
        mock_response = Mock()
        mock_response.image = {
            "large": "https://example.com/600.jpg",
            "small": "https://example.com/150.jpg",
            "thumbnail": "https://example.com/50.jpg",
        }
        # Remove get_cover_urls method to test fallback
        del mock_response.get_cover_urls

        covers = Covers.from_qobuz_response(mock_response)

        # Should have 4 images: large, small, thumbnail, and generated original
        assert len(covers.images) == 4
        # Check that original URL is generated from large URL
        original_image = covers.get_image(CoverSize.ORIGINAL)
        assert original_image is not None
        assert "org" in original_image.url

    def test_from_qobuz_response_no_image_data(self):
        """Test from_qobuz_response with no image data."""
        mock_response = Mock()
        # Remove both get_cover_urls method and image attribute
        del mock_response.get_cover_urls
        mock_response.image = None

        covers = Covers.from_qobuz_response(mock_response)

        assert len(covers.images) == 0
        assert not covers.has_images

    def test_extract_cover_urls_no_methods(self):
        """Test _extract_cover_urls with object that has no relevant methods."""
        mock_response = Mock()
        # Remove both methods/attributes
        del mock_response.get_cover_urls
        del mock_response.image

        urls = Covers._extract_cover_urls(mock_response)
        assert urls == {}

    def test_extract_urls_from_image_dict_complete(self):
        """Test _extract_urls_from_image_dict with complete image data."""
        image_dict = {
            "large": "https://example.com/600.jpg",
            "small": "https://example.com/150.jpg",
            "thumbnail": "https://example.com/50.jpg",
        }

        urls = Covers._extract_urls_from_image_dict(image_dict)

        assert "large" in urls
        assert "small" in urls
        assert "thumbnail" in urls
        assert "original" in urls
        # Check that original URL is generated correctly
        assert urls["original"] == "https://example.com/org.jpg"

    def test_extract_urls_from_image_dict_partial(self):
        """Test _extract_urls_from_image_dict with partial image data."""
        image_dict = {"small": "https://example.com/150.jpg"}

        urls = Covers._extract_urls_from_image_dict(image_dict)

        assert "small" in urls
        assert "large" not in urls
        assert "original" not in urls

    def test_add_images_to_covers_valid_sizes(self):
        """Test _add_images_to_covers with valid size values."""
        covers = Covers()
        urls = {
            "small": "https://example.com/small.jpg",
            "large": "https://example.com/large.jpg",
        }

        Covers._add_images_to_covers(covers, urls)

        assert len(covers.images) == 2
        assert covers.get_image(CoverSize.SMALL) is not None
        assert covers.get_image(CoverSize.LARGE) is not None

    def test_add_images_to_covers_invalid_sizes(self):
        """Test _add_images_to_covers skips invalid size values."""
        covers = Covers()
        urls = {
            "small": "https://example.com/small.jpg",
            "invalid_size": "https://example.com/invalid.jpg",
            "large": "https://example.com/large.jpg",
        }

        Covers._add_images_to_covers(covers, urls)

        # Should only add valid sizes, skip invalid ones
        assert len(covers.images) == 2
        assert covers.get_image(CoverSize.SMALL) is not None
        assert covers.get_image(CoverSize.LARGE) is not None

    def test_from_qobuz_response_integration(self):
        """Test complete from_qobuz_response integration."""
        mock_response = Mock()
        mock_response.image = {
            "large": "https://example.com/600.jpg",
            "small": "https://example.com/150.jpg",
        }
        del mock_response.get_cover_urls

        covers = Covers.from_qobuz_response(mock_response)

        # Verify the complete flow worked
        assert covers.has_images
        assert len(covers.available_sizes) >= 2

        # Test that we can get images by size
        small_image = covers.get_image(CoverSize.SMALL)
        large_image = covers.get_image(CoverSize.LARGE)
        original_image = covers.get_image(CoverSize.ORIGINAL)

        assert small_image is not None
        assert large_image is not None
        assert original_image is not None  # Should be generated from large


class TestCoversEdgeCases:
    """Test edge cases and error conditions for Covers."""

    def test_get_largest_image_unknown_size(self):
        """Test get_largest_image with unknown size enum values."""
        covers = Covers()
        # Add image with mock size that's not in the size_order dict
        mock_image = Mock()
        mock_image.size = "unknown_size"
        covers.images.append(mock_image)

        result = covers.get_largest_image()
        assert result == mock_image  # Should return the image even with unknown size

    def test_get_smallest_image_unknown_size(self):
        """Test get_smallest_image with unknown size enum values."""
        covers = Covers()
        # Add image with mock size that's not in the size_order dict
        mock_image = Mock()
        mock_image.size = "unknown_size"
        covers.images.append(mock_image)

        result = covers.get_smallest_image()
        assert result == mock_image  # Should return the image even with unknown size

    def test_download_to_directory_with_pathlib_path(self):
        """Test download_to_directory with pathlib.Path object."""
        covers = Covers()
        covers.add_image("https://example.com/test.jpg", CoverSize.MEDIUM)

        test_path = Path("/test/path")

        with patch.object(Path, "mkdir") as mock_mkdir:
            result = covers.download_to_directory(test_path)

            # Verify Path.mkdir was called
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            assert len(result) == 1
            assert CoverSize.MEDIUM in result
