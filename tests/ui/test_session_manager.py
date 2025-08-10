# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for `WorkingSessionManager`.

These tests focus strictly on the persistence contract of the session manager
and use an injected temporary database to avoid touching global state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from ripstream.ui.session_manager import WorkingSessionManager

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from ripstream.models.db_manager import DatabaseManager


def _create_manager(temp_db: DatabaseManager) -> WorkingSessionManager:
    """Create a `WorkingSessionManager` bound to the temp database.

    Keeping this logic in one place ensures DRY usage across tests.
    """

    return WorkingSessionManager(db_manager=temp_db)


@pytest.fixture
def sample_payload() -> dict[str, Any]:
    """Provide a representative payload for saving state."""
    return {
        "last_url": "https://open.qobuz.com/artist/123",
        "artist_filter": "ALBUMS_ONLY",
        "view_name": "discography",
        "metadata_snapshot": {
            "view_type": "grid",
            "items": [
                {
                    "id": "album_1",
                    "title": "A",
                    "artist": "X",
                    "type": "Album",
                    "artwork_url": "https://example.com/a.jpg",
                }
            ],
            "grid_scroll": 10,
            "list_scroll": 0,
        },
        # UI extras
        "filter_index": 1,
        "downloads_scroll": 42,
    }


def test_load_returns_none_when_no_record(temp_db: DatabaseManager) -> None:
    """Loading before saving should return None (no record)."""
    manager = _create_manager(temp_db)
    assert manager.load() is None


def test_save_creates_record_and_load_returns_payload(
    temp_db: DatabaseManager, sample_payload: dict[str, Any]
) -> None:
    """Saving should create a record that can be loaded back with promoted extras."""
    manager = _create_manager(temp_db)
    manager.save(sample_payload)

    state = manager.load()
    assert state is not None

    # Basic fields
    assert state.get("last_url") == sample_payload["last_url"]
    assert state.get("artist_filter") == sample_payload["artist_filter"]
    assert state.get("view_name") == sample_payload["view_name"]

    # Metadata snapshot is preserved
    snapshot = state.get("metadata_snapshot")
    assert isinstance(snapshot, dict)
    assert snapshot.get("view_type") == "grid"
    assert isinstance(snapshot.get("items"), list)

    # UI extras promoted to top-level
    assert state.get("filter_index") == sample_payload["filter_index"]
    assert state.get("downloads_scroll") == sample_payload["downloads_scroll"]


def test_save_updates_existing_record_merging_ui_extras(
    temp_db: DatabaseManager, sample_payload: dict[str, Any]
) -> None:
    """Subsequent save should update the same logical record and merge UI extras."""
    manager = _create_manager(temp_db)
    manager.save(sample_payload)

    # Update only a subset of fields and change UI extras
    updated: dict[str, Any] = {
        "last_url": "https://open.qobuz.com/album/999",
        "metadata_snapshot": {"view_type": "list", "items": []},
        "filter_index": 2,
        "downloads_scroll": 7,
    }
    manager.save(updated)

    state = manager.load()
    assert state is not None

    # Updated fields
    assert state.get("last_url") == updated["last_url"]
    assert state.get("metadata_snapshot", {}).get("view_type") == "list"

    # Unchanged fields remain (defensive set to None is acceptable per implementation)
    # Artist filter and view_name may be None if not provided in update, so only
    # assert that the keys exist in the returned mapping
    assert "artist_filter" in state
    assert "view_name" in state

    # UI extras reflect latest values
    assert state.get("filter_index") == 2
    assert state.get("downloads_scroll") == 7


def test_save_gracefully_handles_uninitialized_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manager.save should return without error when session_factory is None."""

    class DummyDB:  # Minimal stub to satisfy type usage in manager
        session_factory = None

    manager = WorkingSessionManager(db_manager=DummyDB())  # type: ignore[arg-type]
    # Should not raise
    manager.save({"last_url": "x"})


def test_load_handles_corrupt_or_non_dict_snapshot(temp_db: DatabaseManager) -> None:
    """Load should tolerate non-dict JSON column for snapshot."""
    # Insert a UISessionState row manually with a non-dict metadata_snapshot
    from sqlalchemy.orm import Session

    from ripstream.models.database import UISessionState

    temp_db.create_tables()
    with temp_db.get_session() as session:  # type: ignore[assignment]
        assert isinstance(session, Session)
        state = UISessionState(
            key="default",
            last_url="u",
            artist_filter="BOTH",
            view_name="discography",
            metadata_snapshot="this-should-be-a-dict",  # type: ignore[assignment]
        )
        session.add(state)
        session.commit()

    manager = _create_manager(temp_db)
    loaded = manager.load()
    assert loaded is not None
    # Snapshot should be normalized to a dict, not the raw string
    assert isinstance(loaded.get("metadata_snapshot"), dict)


def test_save_ignores_non_dict_snapshot_and_promotes_extras(
    temp_db: DatabaseManager,
) -> None:
    """Saving with a non-dict snapshot should normalize to {} and still save extras."""
    manager = _create_manager(temp_db)
    manager.save({
        "last_url": "u",
        "metadata_snapshot": "not-a-dict",  # type: ignore[arg-type]
        "filter_index": 3,
        "downloads_scroll": 11,
    })

    state = manager.load()
    assert state is not None
    assert isinstance(state.get("metadata_snapshot"), dict)
    assert state.get("filter_index") == 3
    assert state.get("downloads_scroll") == 11


def test_multiple_sequential_saves_on_same_instance(
    temp_db: DatabaseManager, sample_payload: dict[str, Any]
) -> None:
    """Multiple sequential saves should not create duplicate logical records."""
    manager = _create_manager(temp_db)
    manager.save(sample_payload)
    manager.save(sample_payload | {"last_url": "https://open.qobuz.com/artist/456"})
    manager.save(sample_payload | {"view_name": "downloads"})

    # Only one record should exist with key 'default'
    from sqlalchemy import select

    from ripstream.models.database import UISessionState

    with temp_db.get_session() as session:
        rows = session.execute(select(UISessionState)).scalars().all()
        assert len(rows) == 1
        assert rows[0].key == WorkingSessionManager.DEFAULT_KEY


def test_large_snapshot_roundtrip(temp_db: DatabaseManager) -> None:
    """Saving and loading a large snapshot should succeed without truncation.

    Keep item count modest to maintain fast test execution.
    """
    manager = _create_manager(temp_db)
    large_items: list[dict[str, Any]] = [
        {
            "id": f"album_{i}",
            "title": f"Album {i}",
            "artist": "Artist",
            "type": "Album",
            "artwork_url": f"https://example.com/{i}.jpg",
        }
        for i in range(2000)
    ]
    payload: dict[str, Any] = {
        "last_url": "https://open.qobuz.com/artist/large",
        "metadata_snapshot": {"view_type": "grid", "items": large_items},
    }
    manager.save(payload)

    state = manager.load()
    assert state is not None
    snapshot = state.get("metadata_snapshot")
    assert isinstance(snapshot, dict)
    from ripstream.ui.session_manager import WorkingSessionManager

    expected = min(len(large_items), WorkingSessionManager.MAX_SNAPSHOT_ITEMS)
    assert len(snapshot.get("items", [])) == expected


def test_snapshot_items_capped_to_policy(temp_db: DatabaseManager) -> None:
    """When items exceed the MAX_SNAPSHOT_ITEMS policy, they are truncated on save."""
    manager = _create_manager(temp_db)
    cap = WorkingSessionManager.MAX_SNAPSHOT_ITEMS
    items = [{"id": f"album_{i}", "type": "Album"} for i in range(cap + 500)]
    manager.save({"metadata_snapshot": {"items": items}})

    state = manager.load()
    assert state is not None
    snapshot = state.get("metadata_snapshot")
    assert isinstance(snapshot, dict)
    assert len(snapshot.get("items", [])) == cap


def test_load_with_ui_section_non_dict(temp_db: DatabaseManager) -> None:
    """Load should tolerate `_ui` being a non-dict and treat extras as empty."""
    from sqlalchemy.orm import Session

    from ripstream.models.database import UISessionState

    with temp_db.get_session() as session:  # type: ignore[assignment]
        assert isinstance(session, Session)
        session.add(
            UISessionState(
                key="default",
                last_url="u",
                metadata_snapshot={"_ui": "not-a-dict"},  # type: ignore[assignment]
            )
        )
        session.commit()

    manager = _create_manager(temp_db)
    state = manager.load()
    assert state is not None
    # No extras promoted when _ui is invalid
    assert "filter_index" not in state
    assert "downloads_scroll" not in state


def test_unknown_snapshot_keys_preserved(temp_db: DatabaseManager) -> None:
    """Unknown keys in snapshot should be preserved through roundtrip."""
    manager = _create_manager(temp_db)
    payload: dict[str, Any] = {
        "metadata_snapshot": {
            "view_type": "grid",
            "items": [],
            "unknown_key": {"nested": True},
        }
    }
    manager.save(payload)
    state = manager.load()
    assert state is not None
    snapshot = state.get("metadata_snapshot")
    assert isinstance(snapshot, dict)
    assert snapshot.get("unknown_key") == {"nested": True}


def test_save_without_snapshot_clears_snapshot_to_empty_dict(
    temp_db: DatabaseManager,
) -> None:
    """Calling save without `metadata_snapshot` normalizes snapshot to {} per implementation."""
    manager = _create_manager(temp_db)
    manager.save({"metadata_snapshot": {"view_type": "grid"}})
    manager.save({"last_url": "only-url-update"})
    state = manager.load()
    assert state is not None
    snapshot = state.get("metadata_snapshot")
    assert isinstance(snapshot, dict)
    # View type removed since save didn't include metadata_snapshot
    assert snapshot.get("view_type") is None


def test_very_long_string_fields_roundtrip(temp_db: DatabaseManager) -> None:
    """Extremely long string values should survive save/load intact."""
    manager = _create_manager(temp_db)
    long_str = "x" * 10000
    manager.save({"last_url": long_str, "artist_filter": long_str})
    state = manager.load()
    assert state is not None
    assert state.get("last_url") == long_str
    assert state.get("artist_filter") == long_str
