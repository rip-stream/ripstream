# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

import pytest

from ripstream.models.db_manager import DatabaseManager
from ripstream.models.download_service import FavoritesService
from ripstream.models.enums import StreamingSource


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "favorites.db"
    dbm = DatabaseManager(db_path)
    dbm.initialize()

    # Patch global getter used by FavoritesService
    from ripstream.models import download_service as ds

    monkeypatch.setattr(ds, "get_downloads_db", lambda: dbm, raising=True)
    return dbm


@pytest.fixture
def favorites(temp_db):
    return FavoritesService()


def test_add_and_is_favorite(favorites: FavoritesService):
    ok = favorites.add_favorite_artist(
        source=StreamingSource.QOBUZ,
        artist_id="artist_1",
        name="Test Artist",
        artist_url="qobuz://artist/artist_1",
        photo_url="https://example.com/a.jpg",
    )
    assert ok is True
    assert favorites.is_favorite(StreamingSource.QOBUZ, "artist_1") is True


def test_list_and_remove_by_id_and_key(favorites: FavoritesService):
    # Seed two favorites
    for idx in ("a1", "a2"):
        assert favorites.add_favorite_artist(
            source=StreamingSource.QOBUZ,
            artist_id=idx,
            name=f"A-{idx}",
            artist_url=f"qobuz://artist/{idx}",
            photo_url=f"https://example.com/{idx}.jpg",
        )

    items = favorites.list_favorites()
    assert len(items) == 2

    # Remove by id
    ok = favorites.remove_favorite_by_id(items[0]["id"])
    assert ok is True
    assert favorites.is_favorite(StreamingSource.QOBUZ, items[0]["artist_id"]) is False

    # Remove by key
    ok2 = favorites.remove_favorite(StreamingSource.QOBUZ, items[1]["artist_id"])
    assert ok2 is True
    assert favorites.list_favorites() == []
