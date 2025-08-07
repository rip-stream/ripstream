# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Utility functions for the downloader module."""


def raise_error(
    error_type: type[Exception],
    msg: str,
    base_error: Exception | None = None,
    **kwargs: object,
) -> None:
    """
    Raise an error with the specified type and message.

    Args:
        error_type: The exception class to raise
        msg: The error message
        base_error: Optional base exception to chain from
        **kwargs: Additional keyword arguments to pass to the exception constructor
    """
    if base_error is not None:
        raise error_type(msg, **kwargs) from base_error
    raise error_type(msg, **kwargs)
