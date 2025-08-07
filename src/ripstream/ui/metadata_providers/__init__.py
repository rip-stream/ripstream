# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Metadata providers for different streaming services."""

from .base import BaseMetadataProvider, MetadataResult
from .deezer import DeezerMetadataProvider
from .factory import MetadataProviderFactory
from .qobuz import QobuzMetadataProvider
from .tidal import TidalMetadataProvider
from .youtube import YouTubeMetadataProvider

__all__ = [
    "BaseMetadataProvider",
    "DeezerMetadataProvider",
    "MetadataProviderFactory",
    "MetadataResult",
    "QobuzMetadataProvider",
    "TidalMetadataProvider",
    "YouTubeMetadataProvider",
]
