# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Exceptions for the downloader module."""

from typing import Any


class DownloadError(Exception):
    """Base exception for download-related errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NetworkError(DownloadError):
    """Exception raised for network-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.status_code = status_code


class DownloadTimeoutError(DownloadError):
    """Exception raised when download times out."""

    def __init__(
        self,
        message: str,
        timeout_seconds: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.timeout_seconds = timeout_seconds


class InvalidContentError(DownloadError):
    """Exception raised when downloaded content is invalid."""

    def __init__(
        self,
        message: str,
        content_type: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.content_type = content_type


class RetryExhaustedError(DownloadError):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(
        self,
        message: str,
        retry_count: int,
        last_error: Exception | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.retry_count = retry_count
        self.last_error = last_error


class AuthenticationError(DownloadError):
    """Exception raised for authentication-related errors."""

    def __init__(
        self,
        message: str,
        source: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.source = source


class RateLimitError(DownloadError):
    """Exception raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.retry_after = retry_after


class InsufficientStorageError(DownloadError):
    """Exception raised when there's insufficient storage space."""

    def __init__(
        self,
        message: str,
        required_bytes: int | None = None,
        available_bytes: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes


class ContentNotFoundError(DownloadError):
    """Exception raised when content is not found."""

    def __init__(
        self,
        message: str,
        content_id: str | None = None,
        source: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.content_id = content_id
        self.source = source


class DownloadPermissionError(DownloadError):
    """Exception raised for download permission-related errors."""

    def __init__(
        self,
        message: str,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.path = path
