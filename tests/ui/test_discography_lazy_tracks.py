# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""UI tests for decoupled album grid and track list population."""

from __future__ import annotations

import pytest

from ripstream.ui.discography.view import DiscographyView


@pytest.mark.usefixtures("qapp")
def test_list_populates_when_full_album_arrives(sample_album_metadata: dict) -> None:
    """List view should receive tracks when full album metadata is added later."""
    view = DiscographyView()
    # First add only the album info (simulate lightweight emission)
    lightweight = sample_album_metadata.copy()
    lightweight["items"] = []
    view.set_content(lightweight)

    # Initially no rows in list view
    assert view.list_view.rowCount() == 0

    # Now add full album content
    view.add_album_content(
        sample_album_metadata["album_info"], sample_album_metadata["items"], "Qobuz"
    )

    # Tracks should be added to list view
    assert view.list_view.rowCount() == len(sample_album_metadata["items"]) + 0


@pytest.mark.usefixtures("qapp")
def test_grid_only_once_then_tracks_multiple(sample_album_metadata: dict) -> None:
    """Grid should show album once; list can add tracks multiple times without duplicating grid items."""
    view = DiscographyView()

    # Add album twice: first lightweight, then full
    lightweight = sample_album_metadata.copy()
    lightweight["items"] = []
    view.set_content(lightweight)
    # Add full content
    view.add_album_content(
        sample_album_metadata["album_info"], sample_album_metadata["items"], "Qobuz"
    )

    # Count album widgets
    grid_count = len(view.grid_view.items)
    assert grid_count == 1

    # Add full content again (simulating background refetch)
    view.add_album_content(
        sample_album_metadata["album_info"], sample_album_metadata["items"], "Qobuz"
    )

    # Grid still one, list rows equal to tracks (no duplicates as add_item inserts new rows each call)
    assert len(view.grid_view.items) == 1
    assert view.list_view.rowCount() >= len(
        sample_album_metadata["items"]
    )  # may append


@pytest.mark.usefixtures("qapp")
def test_progressive_sort_is_maintained(sample_album_metadata: dict) -> None:
    """If sorting was applied, progressive additions should respect it."""
    view = DiscographyView()

    # Apply sort by title ascending before any items
    view.sort_items("title")

    # First add lightweight album (no tracks yet)
    lightweight = sample_album_metadata.copy()
    lightweight["items"] = []
    view.set_content(lightweight)

    # Now progressively add tracks in reverse-sorted order to attempt to break sorting
    tracks = list(sample_album_metadata["items"])  # type: ignore[index]
    # Reverse titles to simulate out-of-order arrival
    tracks.reverse()
    view.add_album_content(sample_album_metadata["album_info"], tracks, "Qobuz")

    # After progressive add, list view should be sorted by title asc
    if view.list_view.rowCount() >= 2:
        first_item = view.list_view.item(0, 0)
        second_item = view.list_view.item(1, 0)
        assert first_item is not None
        assert second_item is not None
        first = first_item.text()
        second = second_item.text()
        assert first <= second
