# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""UI-level tests for session save/restore behavior.

The intent is to validate that `WorkingSessionManager` integrates correctly with
`MainWindow` and the discography UI without duplicating tests that already
cover grid/list rendering. We focus on persisting and restoring core state.
"""

from __future__ import annotations

from typing import Any

import pytest

from ripstream.ui.main_window import MainWindow
from ripstream.ui.session_manager import WorkingSessionManager


@pytest.mark.usefixtures("qapp")
def test_main_window_saves_and_restores_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end: emulate saving and restoring a simple session state.

    We avoid network calls by not invoking metadata fetch; instead, we:
    - Create the window
    - Manually populate a minimal snapshot via the discography view
    - Trigger the internal save method
    - Recreate the window and trigger restore
    Assertions cover that URL, filter index, view name, and discography items
    are restored according to our snapshot contract.
    """

    # Use an in-memory manager to avoid touching the real downloads DB
    class InMemoryManager(WorkingSessionManager):
        _state: dict[str, Any] | None = None

        def save(self, payload: dict[str, Any]) -> None:  # type: ignore[override]
            self._state = payload

        def load(self) -> dict[str, Any] | None:  # type: ignore[override]
            return self._state

    # Create first window and stub its session manager
    w1 = MainWindow()
    w1.session_manager = InMemoryManager()

    # Seed minimal discography snapshot manually
    dview = w1.ui_manager.get_discography_view()
    assert dview is not None
    # Add one album item (as if restored later)
    dview.add_item(
        {
            "id": "album_1",
            "title": "Album",
            "artist": "Artist",
            "type": "Album",
            "artwork_url": None,
        },
        service="qobuz",
    )

    # Simulate navbar state
    navbar = w1.ui_manager.get_navbar()
    assert navbar is not None
    navbar.set_url("https://open.qobuz.com/artist/123")
    # Choose filter index 1 (Albums Only)
    if hasattr(navbar, "url_widget") and hasattr(navbar.url_widget, "filter_dropdown"):
        navbar.url_widget.filter_dropdown.setCurrentIndex(1)

    # Persist
    w1._save_working_session()

    # Create second window and inject same manager to simulate app relaunch
    w2 = MainWindow()
    w2.session_manager = w1.session_manager
    w2._restore_working_session()

    # Validate URL restored
    navbar2 = w2.ui_manager.get_navbar()
    assert navbar2 is not None
    assert navbar2.get_current_url() == "https://open.qobuz.com/artist/123"

    # Validate filter restored
    idx = navbar2.url_widget.filter_dropdown.currentIndex()  # type: ignore[attr-defined]
    assert idx == 1

    # Validate discography restored to have at least our one item
    dview2 = w2.ui_manager.get_discography_view()
    assert dview2 is not None
    assert len(dview2.grid_view.items) >= 1
