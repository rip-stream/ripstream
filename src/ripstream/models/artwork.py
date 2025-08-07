# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Artwork and cover image models."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from ripstream.models.base import RipStreamBaseModel
from ripstream.models.enums import CoverSize


class CoverImage(RipStreamBaseModel):
    """Individual cover image with size and URL information."""

    url: str = Field(..., description="URL to the cover image")
    size: CoverSize = Field(..., description="Size category of the image")
    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")
    format: str | None = Field(None, description="Image format (e.g., JPEG, PNG)")
    file_size_bytes: int | None = Field(None, description="File size in bytes")
    local_path: str | None = Field(None, description="Local file path after download")

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int | None) -> int | None:
        """Validate image dimensions are positive."""
        if v is not None and v <= 0:
            msg = "Image dimensions must be positive"
            raise ValueError(msg)
        return v

    @property
    def aspect_ratio(self) -> float | None:
        """Calculate aspect ratio (width/height)."""
        if self.width is None or self.height is None or self.height == 0:
            return None
        return self.width / self.height

    @property
    def is_square(self) -> bool:
        """Check if the image is square."""
        return self.aspect_ratio == 1.0 if self.aspect_ratio is not None else False

    @property
    def file_size_kb(self) -> float | None:
        """Get file size in kilobytes."""
        if self.file_size_bytes is None:
            return None
        return round(self.file_size_bytes / 1024, 2)

    def get_filename(self, prefix: str = "cover") -> str:
        """Generate a filename for the cover image."""
        extension = self.format.lower() if self.format else "jpg"

        # Handle both enum and string values for size
        if hasattr(self.size, "value"):
            size_value = self.size.value
            is_original = self.size == CoverSize.ORIGINAL
        else:
            size_value = str(self.size)
            is_original = size_value.lower() == "original"

        size_suffix = f"_{size_value}" if not is_original else ""
        return f"{prefix}{size_suffix}.{extension}"


class Covers(RipStreamBaseModel):
    """Collection of cover images in different sizes."""

    images: list[CoverImage] = Field(
        default_factory=list, description="List of cover images"
    )
    primary_color: str | None = Field(
        None, description="Primary color extracted from cover"
    )
    dominant_colors: list[str] = Field(
        default_factory=list, description="Dominant colors in the image"
    )

    def add_image(
        self,
        url: str,
        size: CoverSize,
        width: int | None = None,
        height: int | None = None,
        image_format: str | None = None,
        file_size_bytes: int | None = None,
        local_path: str | None = None,
    ) -> CoverImage:
        """Add a cover image to the collection."""
        image = CoverImage(
            url=url,
            size=size,
            width=width,
            height=height,
            format=image_format,
            file_size_bytes=file_size_bytes,
            local_path=local_path,
        )
        self.images.append(image)
        return image

    def get_image(self, size: CoverSize) -> CoverImage | None:
        """Get cover image by size."""
        for image in self.images:
            if image.size == size:
                return image
        return None

    def get_best_image(
        self, preferred_sizes: list[CoverSize] | None = None
    ) -> CoverImage | None:
        """Get the best available cover image."""
        if not self.images:
            return None

        if preferred_sizes is None:
            preferred_sizes = [
                CoverSize.LARGE,
                CoverSize.ORIGINAL,
                CoverSize.MEDIUM,
                CoverSize.SMALL,
            ]

        # Try to find image in preferred order
        for size in preferred_sizes:
            image = self.get_image(size)
            if image:
                return image

        # Return first available image if no preferred size found
        return self.images[0]

    def get_largest_image(self) -> CoverImage | None:
        """Get the largest available cover image."""
        if not self.images:
            return None

        # Sort by size enum value (higher = larger)
        size_order = {
            CoverSize.SMALL: 1,
            CoverSize.MEDIUM: 2,
            CoverSize.LARGE: 3,
            CoverSize.ORIGINAL: 4,
        }

        return max(self.images, key=lambda img: size_order.get(img.size, 0))

    def get_smallest_image(self) -> CoverImage | None:
        """Get the smallest available cover image."""
        if not self.images:
            return None

        size_order = {
            CoverSize.SMALL: 1,
            CoverSize.MEDIUM: 2,
            CoverSize.LARGE: 3,
            CoverSize.ORIGINAL: 4,
        }

        return min(self.images, key=lambda img: size_order.get(img.size, 4))

    @property
    def has_images(self) -> bool:
        """Check if any cover images are available."""
        return len(self.images) > 0

    @property
    def available_sizes(self) -> list[CoverSize]:
        """Get list of available cover sizes."""
        return [img.size for img in self.images]

    def download_to_directory(
        self, directory: str | Path, prefix: str = "cover"
    ) -> dict[CoverSize, str]:
        """Download all cover images to a directory."""
        # This would be implemented with actual download logic
        # For now, return a placeholder mapping
        directory_path = Path(directory)
        directory_path.mkdir(parents=True, exist_ok=True)

        downloaded_paths: dict[CoverSize, str] = {}
        for image in self.images:
            filename = image.get_filename(prefix)
            file_path = directory_path / filename
            downloaded_paths[image.size] = str(file_path)
            # Actual download implementation would go here

        return downloaded_paths

    def set_color_info(
        self, primary_color: str, dominant_colors: list[str] | None = None
    ) -> None:
        """Set color information extracted from the cover."""
        self.primary_color = primary_color
        if dominant_colors:
            self.dominant_colors = dominant_colors

    @classmethod
    def from_qobuz_response(cls, qobuz_response: Any) -> "Covers":
        """Create Covers object from Qobuz API response."""
        covers = cls()

        # Extract cover URLs from the response
        urls = cls._extract_cover_urls(qobuz_response)
        if not urls:
            return covers  # Return empty covers if no image data

        # Add images to covers collection
        cls._add_images_to_covers(covers, urls)

        return covers

    @classmethod
    def _extract_cover_urls(cls, qobuz_response: Any) -> dict[str, str]:
        """Extract cover URLs from Qobuz response."""
        if hasattr(qobuz_response, "get_cover_urls"):
            return qobuz_response.get_cover_urls()

        if hasattr(qobuz_response, "image") and qobuz_response.image:
            return cls._extract_urls_from_image_dict(qobuz_response.image)

        return {}

    @classmethod
    def _extract_urls_from_image_dict(cls, img: dict[str, str]) -> dict[str, str]:
        """Extract URLs from image dictionary."""
        urls = {}

        if "large" in img:
            urls["large"] = img["large"]
            urls["original"] = "org".join(img["large"].rsplit("600", 1))

        if "small" in img:
            urls["small"] = img["small"]

        if "thumbnail" in img:
            urls["thumbnail"] = img["thumbnail"]

        return urls

    @classmethod
    def _add_images_to_covers(cls, covers: "Covers", urls: dict[str, str]) -> None:
        """Add images to covers collection using enum values directly."""
        for size, url in urls.items():
            try:
                cover_size = CoverSize(size)
                covers.add_image(url, cover_size)
            except ValueError:
                # Skip unknown size values
                continue
