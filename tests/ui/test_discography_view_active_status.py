# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for active album statuses integration in DiscographyView."""

from __future__ import annotations

import pytest

from ripstream.ui.discography.view import DiscographyView


class TestDiscographyViewActiveStatuses:
    """Ensure DiscographyView applies active statuses to grid items."""

    @pytest.fixture
    def view(self, qapp) -> DiscographyView:
        return DiscographyView()

    def test_update_active_album_statuses(
        self, view: DiscographyView, sample_album_item
    ):
        # Add an album to grid
        view.grid_view.add_item(sample_album_item)
        widget = view.grid_view.items[0]

        # Mark as downloading
        view.update_active_album_statuses({sample_album_item["id"]}, set())
        assert widget.get_status() == "downloading"

        # Mark as queued
        view.update_active_album_statuses(set(), {sample_album_item["id"]})
        assert widget.get_status() == "queued"

        # Clear statuses restores idle when not downloaded
        view.update_active_album_statuses(set(), set())
        assert widget.get_status() == "idle"

    def test_downloaded_state_is_sticky(self, view: DiscographyView, sample_album_item):
        # Add an album and mark it downloaded
        sample_album_item_with_source = sample_album_item | {"source": "qobuz"}
        view.grid_view.add_item(sample_album_item_with_source)
        view.update_downloaded_albums({(sample_album_item_with_source["id"], "qobuz")})
        widget = view.grid_view.items[0]
        assert widget.get_status() == "downloaded"

        # Active status updates should not override downloaded
        view.update_active_album_statuses({sample_album_item_with_source["id"]}, set())
        assert widget.get_status() == "downloaded"
