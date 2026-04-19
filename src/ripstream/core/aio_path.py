# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Async wrappers for blocking ``pathlib`` operations.

Wrap blocking filesystem calls so they can be safely awaited from
``async`` functions without blocking the event loop, satisfying ``ASYNC240``.
"""

import asyncio
import os
from pathlib import Path


async def path_exists(path: str | os.PathLike[str]) -> bool:
    """Return ``True`` if ``path`` exists on disk."""
    return await asyncio.to_thread(Path(path).exists)


async def path_is_file(path: str | os.PathLike[str]) -> bool:
    """Return ``True`` if ``path`` exists and is a regular file."""
    return await asyncio.to_thread(Path(path).is_file)


async def path_is_dir(path: str | os.PathLike[str]) -> bool:
    """Return ``True`` if ``path`` exists and is a directory."""
    return await asyncio.to_thread(Path(path).is_dir)


async def path_mkdir(
    path: str | os.PathLike[str],
    *,
    parents: bool = False,
    exist_ok: bool = False,
) -> None:
    """Create ``path`` (and parents) on disk."""
    await asyncio.to_thread(Path(path).mkdir, parents=parents, exist_ok=exist_ok)


async def path_unlink(
    path: str | os.PathLike[str], *, missing_ok: bool = False
) -> None:
    """Remove the file at ``path``."""
    await asyncio.to_thread(Path(path).unlink, missing_ok=missing_ok)


async def path_stat(path: str | os.PathLike[str]) -> os.stat_result:
    """Return ``os.stat_result`` for ``path``."""
    return await asyncio.to_thread(Path(path).stat)


async def path_size(path: str | os.PathLike[str]) -> int:
    """Return the size in bytes of ``path``."""
    stat = await path_stat(path)
    return stat.st_size
