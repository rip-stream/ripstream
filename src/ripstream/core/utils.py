# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Core utility functions for ripstream."""

import base64


def encode_secret(value: str) -> str:
    """Encode a secret value using base64."""
    if not value:
        return ""
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def decode_secret(encoded_value: str) -> str:
    """Decode a base64-encoded secret value."""
    if not encoded_value:
        return ""
    try:
        return base64.b64decode(encoded_value.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""
