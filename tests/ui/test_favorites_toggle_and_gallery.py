# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

from unittest.mock import patch

import pytest

from ripstream.models.enums import StreamingSource
from ripstream.ui.discography.view import (
    FAVORITES_ICON_HEIGHT_PX,
    FAVORITES_ICON_WIDTH_PX,
)
from ripstream.ui.main_window import MainWindow, _ActionData


@pytest.fixture
def window(qapp):
    return MainWindow()


@pytest.fixture
def make_parsed_url():
    def _make(artist_id: str):
        with patch("ripstream.core.url_parser.parse_music_url") as pmu:
            from ripstream.core.url_parser import ParsedURL
            from ripstream.downloader.enums import ContentType

            pmu.return_value = ParsedURL(
                service=StreamingSource.QOBUZ,
                content_type=ContentType.ARTIST,
                content_id=artist_id,
                url=f"qobuz://artist/{artist_id}",
                metadata={},
            )
            return pmu.return_value

    return _make


def _toggle_button(win: MainWindow):
    view = win.ui_manager.get_discography_view()
    assert view is not None
    return view.favorite_toggle_btn


@pytest.mark.parametrize("exists", [False, True])
def test_toggle_label_and_enablement(window: MainWindow, make_parsed_url, exists: bool):
    parsed = make_parsed_url("123")

    # Stub FavoritesService.is_favorite
    with patch.object(window, "favorites_service") as fav:
        fav.is_favorite.return_value = exists
        window._update_add_favorite_enabled(parsed)

    btn = _toggle_button(window)
    assert btn.isEnabled() is True  # enabled for Add or Remove
    txt = btn.text().strip().lower()
    if exists:
        assert "remove" in txt
    else:
        assert "add" in txt


def test_gallery_populates_thumbnails(window: MainWindow):
    # Seed favorites list with fake one having a pixmap in pending cache
    view = window.ui_manager.get_discography_view()
    assert view is not None
    artist_id = "abc"

    # Fake pixmap
    from PyQt6.QtGui import QPixmap

    pm = QPixmap(50, 50)
    view.pending_artwork[artist_id] = pm

    with patch.object(window, "favorites_service") as fav:
        fav.list_favorites.return_value = [
            {
                "id": "fav1",
                "source": StreamingSource.QOBUZ,
                "artist_id": artist_id,
                "name": "Artist",
                "artist_url": "qobuz://artist/abc",
                "photo_url": "https://example/abc.jpg",
            }
        ]

        window._refresh_favorites_menu()

    # The menu should be built with a QWidgetAction holding the gallery
    menu = view.favorites_menu
    assert menu is not None
    assert menu.actions()


@pytest.mark.parametrize("exists", [False, True])
def test_toggle_clicks_add_or_remove(window: MainWindow, make_parsed_url, exists: bool):
    parsed = make_parsed_url("xyz")

    with (
        patch.object(window, "favorites_service") as fav,
        patch.object(
            window.metadata_service, "get_last_parsed_url", return_value=parsed
        ) as _,
    ):
        fav.is_favorite.return_value = exists
        fav.add_favorite_artist.return_value = True
        fav.remove_favorite.return_value = True
        fav.list_favorites.return_value = []

        # Prime toggle
        window._update_add_favorite_enabled(parsed)
        btn = _toggle_button(window)
        assert btn.isEnabled() is True

        # Click
        btn.click()

        if exists:
            fav.remove_favorite.assert_called_once()
        else:
            fav.add_favorite_artist.assert_called_once()


def test_restore_session_sets_remove_state(window: MainWindow, monkeypatch):
    # Simulate saved state with last_url of an artist
    state = {
        "last_url": "https://play.qobuz.com/artist/abc",
        "metadata_snapshot": {},
    }

    class DummySM:
        def load(self):
            return state

    window.session_manager = DummySM()

    # Stub URL parser and favorites
    from ripstream.core.url_parser import ParsedURL
    from ripstream.downloader.enums import ContentType

    with (
        patch("ripstream.ui.main_window.parse_music_url") as pmu,
        patch.object(window, "favorites_service") as fav,
    ):
        pmu.return_value = ParsedURL(
            service=StreamingSource.QOBUZ,
            content_type=ContentType.ARTIST,
            content_id="abc",
            url="qobuz://artist/abc",
            metadata={},
        )
        fav.is_favorite.return_value = True

        # Run restore logic
        window._restore_working_session()

        btn = _toggle_button(window)
        assert btn.isEnabled() is True
        assert "remove" in btn.text().lower()


def test_gallery_icon_size_uses_constants(window: MainWindow):
    view = window.ui_manager.get_discography_view()
    assert view is not None

    # Seed one favorite with pixmap so a button appears
    from PyQt6.QtGui import QPixmap

    artist_id = "icn"
    view.pending_artwork[artist_id] = QPixmap(
        FAVORITES_ICON_WIDTH_PX, FAVORITES_ICON_HEIGHT_PX
    )

    with patch.object(window, "favorites_service") as fav:
        fav.list_favorites.return_value = [
            {
                "id": "favIcn",
                "source": StreamingSource.QOBUZ,
                "artist_id": artist_id,
                "name": "Icn",
                "artist_url": "qobuz://artist/icn",
                "photo_url": "https://example/icn.jpg",
            }
        ]
        window._refresh_favorites_menu()

    # Find the first toolbutton in the gallery widget action
    actions = view.favorites_menu.actions()
    assert actions
    gallery_widget = actions[0].defaultWidget()
    from PyQt6.QtWidgets import QToolButton

    buttons = gallery_widget.findChildren(QToolButton)
    assert buttons
    size = buttons[0].iconSize()
    assert size.width() == FAVORITES_ICON_WIDTH_PX
    assert size.height() == FAVORITES_ICON_HEIGHT_PX


def test_remove_from_gallery_calls_service(window: MainWindow):
    # Directly invoke handler with payload to simulate click on [x] in old UI
    payload = {
        "remove": True,
        "favorite_id": "id1",
        "source": StreamingSource.QOBUZ,
        "artist_id": "gone",
    }
    with patch.object(window, "favorites_service") as fav:
        fav.remove_favorite_by_id.return_value = True
        window._on_favorite_selected(_ActionData(payload))
        fav.remove_favorite_by_id.assert_called_once_with("id1")
