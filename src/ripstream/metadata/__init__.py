# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Metadata handling for ripstream."""

from .artwork import download_artwork, extract_artwork_urls, remove_artwork_tempdirs
from .tagger import tag_file

__all__ = [
    "download_artwork",
    "extract_artwork_urls",
    "remove_artwork_tempdirs",
    "tag_file",
]
