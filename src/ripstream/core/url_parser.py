# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""URL parsing and service detection for music streaming services."""

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from ripstream.downloader.enums import ContentType
from ripstream.models.enums import StreamingSource


@dataclass
class ParsedURL:
    """Result of URL parsing."""

    service: StreamingSource
    content_type: ContentType
    content_id: str
    url: str
    metadata: dict[str, str]

    @property
    def is_valid(self) -> bool:
        """Check if the parsed URL is valid."""
        return (
            self.service != StreamingSource.UNKNOWN
            and self.content_type != ContentType.UNKNOWN
            and bool(self.content_id)
        )


class URLParser:
    """Parser for music streaming service URLs."""

    def __init__(self):
        self.service_patterns = self._build_service_patterns()

    def _build_service_patterns(self) -> dict[str, dict[str, list[str]]]:
        """Build regex patterns for each streaming service."""
        return {
            "qobuz": {
                "domains": [r"qobuz\.com", r"open\.qobuz\.com"],
                "artist": [
                    r"/artist/([^/]+)",
                    r"/interpreter/([^/]+)",
                ],
                "album": [
                    r"/album/([^/]+)",
                    r"/album/([^/\?]+)",
                ],
                "track": [
                    r"/track/([^/]+)",
                    r"/track/([^/\?]+)",
                ],
                "playlist": [
                    r"/playlist/([^/]+)",
                    r"/user-playlists/([^/]+)",
                ],
            },
            "spotify": {
                "domains": [r"spotify\.com", r"open\.spotify\.com"],
                "artist": [
                    r"/artist/([a-zA-Z0-9]+)",
                ],
                "album": [
                    r"/album/([a-zA-Z0-9]+)",
                ],
                "track": [
                    r"/track/([a-zA-Z0-9]+)",
                ],
                "playlist": [
                    r"/playlist/([a-zA-Z0-9]+)",
                ],
            },
            "tidal": {
                "domains": [r"tidal\.com", r"listen\.tidal\.com"],
                "artist": [
                    r"/artist/(\d+)",
                    r"/browse/artist/(\d+)",
                ],
                "album": [
                    r"/album/(\d+)",
                    r"/browse/album/(\d+)",
                ],
                "track": [
                    r"/track/(\d+)",
                    r"/browse/track/(\d+)",
                ],
                "playlist": [
                    r"/playlist/([a-zA-Z0-9-]+)",
                    r"/browse/playlist/([a-zA-Z0-9-]+)",
                ],
            },
            "deezer": {
                "domains": [r"deezer\.com", r"www\.deezer\.com"],
                "artist": [
                    r"/artist/(\d+)",
                ],
                "album": [
                    r"/album/(\d+)",
                ],
                "track": [
                    r"/track/(\d+)",
                ],
                "playlist": [
                    r"/playlist/(\d+)",
                ],
            },
            "apple_music": {
                "domains": [r"music\.apple\.com", r"itunes\.apple\.com"],
                "artist": [
                    r"/artist/[^/]+/(\d+)",
                ],
                "album": [
                    r"/album/[^/]+/(\d+)",
                ],
                "track": [
                    r"/album/[^/]+/(\d+)\?i=(\d+)",
                ],
                "playlist": [
                    r"/playlist/[^/]+/(pl\.[a-zA-Z0-9]+)",
                ],
            },
            "youtube_music": {
                "domains": [r"music\.youtube\.com", r"youtu\.be", r"youtube\.com"],
                "artist": [
                    r"/channel/([a-zA-Z0-9_-]+)",
                    r"/c/([a-zA-Z0-9_-]+)",
                ],
                "album": [
                    r"/playlist\?list=([a-zA-Z0-9_-]+)",
                ],
                "track": [
                    r"/watch\?v=([a-zA-Z0-9_-]+)",
                    r"/([a-zA-Z0-9_-]+)",  # For youtu.be
                ],
                "playlist": [
                    r"/playlist\?list=([a-zA-Z0-9_-]+)",
                ],
            },
            "soundcloud": {
                "domains": [r"soundcloud\.com"],
                "artist": [
                    r"/([^/]+)/?$",
                ],
                "album": [
                    r"/([^/]+)/sets/([^/]+)",
                ],
                "track": [
                    r"/([^/]+)/([^/]+)/?$",
                ],
                "playlist": [
                    r"/([^/]+)/sets/([^/]+)",
                ],
            },
        }

    def parse_url(self, url: str) -> ParsedURL:
        """Parse a music streaming URL."""
        if not url:
            return self._create_invalid_result(url, "Empty URL")

        # Clean and normalize URL
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            parsed = urlparse(url)
        except ValueError as e:
            return self._create_invalid_result(url, f"Invalid URL format: {e}")

        # Detect service
        service = self._detect_service(parsed.netloc)
        if service == StreamingSource.UNKNOWN:
            return self._create_invalid_result(url, "Unknown streaming service")

        # Parse content type and ID
        content_type, content_id, metadata = self._parse_content(service, parsed)

        return ParsedURL(
            service=service,
            content_type=content_type,
            content_id=content_id,
            url=url,
            metadata=metadata,
        )

    def _detect_service(self, domain: str) -> StreamingSource:
        """Detect streaming service from domain."""
        domain_lower = domain.lower()

        for service_str, patterns in self.service_patterns.items():
            for domain_pattern in patterns["domains"]:
                if re.search(domain_pattern, domain_lower):
                    return StreamingSource(service_str)

        return StreamingSource.UNKNOWN

    def _parse_content(
        self, service: StreamingSource, parsed_url
    ) -> tuple[ContentType, str, dict[str, str]]:
        """Parse content type and ID from URL path."""
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        metadata = {}

        service_patterns = self.service_patterns.get(service.value, {})

        # Try to match each content type
        for content_type_str in ["artist", "album", "track", "playlist"]:
            content_type = ContentType(content_type_str)
            patterns = service_patterns.get(content_type_str, [])

            for pattern in patterns:
                match = re.search(pattern, path)
                if match:
                    content_id = match.group(1)

                    # Handle special cases
                    if (
                        service == StreamingSource.APPLE_MUSIC
                        and content_type == ContentType.TRACK
                    ):
                        # Apple Music tracks have both album ID and track ID
                        if len(match.groups()) >= 2:
                            metadata["album_id"] = match.group(1)
                            content_id = match.group(2)

                    elif (
                        service == StreamingSource.SOUNDCLOUD
                        and len(match.groups()) >= 2
                        and (
                            content_type == ContentType.TRACK
                            or content_type in [ContentType.ALBUM, ContentType.PLAYLIST]
                        )
                    ):
                        # SoundCloud URLs need special handling
                        metadata["artist"] = match.group(1)
                        content_id = match.group(2)

                    # Add query parameters to metadata
                    for key, values in query_params.items():
                        if values:
                            metadata[key] = values[0]

                    return content_type, content_id, metadata

        return ContentType.UNKNOWN, "", metadata

    def _create_invalid_result(self, url: str, reason: str) -> ParsedURL:
        """Create an invalid ParsedURL result."""
        return ParsedURL(
            service=StreamingSource.UNKNOWN,
            content_type=ContentType.UNKNOWN,
            content_id="",
            url=url,
            metadata={"error": reason},
        )

    def is_supported_service(self, url: str) -> bool:
        """Check if the URL is from a supported streaming service."""
        parsed_result = self.parse_url(url)
        return parsed_result.service != StreamingSource.UNKNOWN

    def get_supported_services(self) -> list[StreamingSource]:
        """Get list of supported streaming services."""
        return [StreamingSource(service) for service in self.service_patterns]

    def get_service_info(self, service: StreamingSource) -> dict[str, list[str]]:
        """Get information about a specific service's URL patterns."""
        return self.service_patterns.get(service.value, {})


class URLValidator:
    """Validator for music streaming URLs."""

    def __init__(self):
        self.parser = URLParser()

    def validate_url(self, url: str) -> tuple[bool, str]:
        """Validate a music streaming URL."""
        if not url:
            return False, "URL cannot be empty"

        if not isinstance(url, str):
            return False, "URL must be a string"

        # Basic URL format check
        url = url.strip()
        if not url:
            return False, "URL cannot be empty"

        # Parse the URL
        parsed_result = self.parser.parse_url(url)

        if not parsed_result.is_valid:
            error_msg = parsed_result.metadata.get("error", "Invalid URL")
            return False, error_msg

        return True, "Valid URL"

    def get_url_info(self, url: str) -> dict[str, str]:
        """Get information about a URL."""
        parsed_result = self.parser.parse_url(url)

        return {
            "service": parsed_result.service.value
            if parsed_result.service != StreamingSource.UNKNOWN
            else "unknown",
            "content_type": parsed_result.content_type.value,
            "content_id": parsed_result.content_id,
            "is_valid": str(parsed_result.is_valid),
            "metadata": str(parsed_result.metadata),
        }


# Convenience functions
def parse_music_url(url: str) -> ParsedURL:
    """Parse a music streaming URL."""
    parser = URLParser()
    return parser.parse_url(url)


def validate_music_url(url: str) -> tuple[bool, str]:
    """Validate a music streaming URL."""
    validator = URLValidator()
    return validator.validate_url(url)


def detect_service_from_url(url: str) -> StreamingSource:
    """Detect streaming service from URL."""
    parsed_result = parse_music_url(url)
    return parsed_result.service


def get_content_type_from_url(url: str) -> ContentType:
    """Get content type from URL."""
    parsed_result = parse_music_url(url)
    return parsed_result.content_type
