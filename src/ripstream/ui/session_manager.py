# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Working session persistence for UI state and content snapshots."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select

from ripstream.config.user import UserConfig
from ripstream.models.database import UISessionState
from ripstream.models.db_manager import DatabaseManager, get_downloads_db

logger = logging.getLogger(__name__)


class WorkingSessionManager:
    """Persist and restore a single working session snapshot.

    Single responsibility: provide a minimal API to save/load the session snapshot
    into the existing SQLite database via SQLAlchemy.
    """

    DEFAULT_KEY: str = "default"
    MAX_SNAPSHOT_ITEMS: int = 1000

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        """Create a working session manager.

        Args:
            db_manager: Optional database manager to use (useful for testing). If
                omitted, the global downloads database will be used.
        """
        self._db_manager = db_manager

    def save(self, payload: dict[str, Any]) -> None:
        """Save the payload as the current working session.

        Args:
            payload: Dictionary containing keys like 'last_url', 'artist_filter',
                'view_name', and 'metadata_snapshot'. All values must be
                JSON-serializable for storage.
        """
        db = self._db_manager or get_downloads_db()
        if db.session_factory is None:
            return
        with db.get_session() as session:
            # Find existing record
            existing = session.execute(
                select(UISessionState).where(UISessionState.key == self.DEFAULT_KEY)
            ).scalar_one_or_none()

            if existing is None:
                existing = UISessionState(key=self.DEFAULT_KEY)
                session.add(existing)

            # Update fields defensively
            existing.last_url = str(payload.get("last_url") or "") or None
            existing.artist_filter = str(payload.get("artist_filter") or "") or None
            existing.view_name = str(payload.get("view_name") or "") or None
            existing.search_query = None  # reserved for future use

            # Merge additional UI state into metadata snapshot under _ui
            raw_snapshot = payload.get("metadata_snapshot")
            snapshot: dict[str, Any] = (
                dict(raw_snapshot) if isinstance(raw_snapshot, dict) else {}
            )
            # Enforce snapshot size cap for items to prevent oversized records
            # Load cap from user config (0 or None means unlimited)
            cap = self._resolve_items_cap()
            items = snapshot.get("items")
            if (
                isinstance(items, list)
                and cap is not None
                and cap > 0
                and len(items) > cap
            ):
                snapshot["items"] = items[:cap]
            ui_extras: dict[str, Any] = {}
            for key in ("filter_index", "downloads_scroll"):
                val = payload.get(key)
                if val is not None:
                    ui_extras[key] = val
            if ui_extras:
                snapshot["_ui"] = ui_extras
            existing.metadata_snapshot = snapshot or None

            session.commit()

    def load(self) -> dict[str, Any] | None:
        """Load the current working session if present.

        Returns a dictionary with the same shape used by save(), or None if no
        record exists.
        """
        db = self._db_manager or get_downloads_db()
        if db.session_factory is None:
            return None
        with db.get_session() as session:
            row = session.execute(
                select(UISessionState).where(UISessionState.key == self.DEFAULT_KEY)
            ).scalar_one_or_none()

            if row is None:
                return None

            raw_snapshot = row.metadata_snapshot
            snapshot: dict[str, Any] = (
                raw_snapshot if isinstance(raw_snapshot, dict) else {}
            )
            raw_ui_extras = snapshot.get("_ui")
            ui_extras: dict[str, Any] = (
                raw_ui_extras if isinstance(raw_ui_extras, dict) else {}
            )
            state: dict[str, Any] = {
                "last_url": row.last_url,
                "artist_filter": row.artist_filter,
                "view_name": row.view_name,
                "search_query": row.search_query,
                "metadata_snapshot": snapshot,
            }
            # Promote extras to top-level for convenience
            for key in ("filter_index", "downloads_scroll"):
                if key in ui_extras:
                    state[key] = ui_extras.get(key)
            return state

    def _resolve_items_cap(self) -> int | None:
        """Resolve snapshot items cap from user configuration.

        Returns None for unlimited. Falls back to class default if config is missing.
        """
        config = UserConfig()
        cap = getattr(
            config.database, "session_snapshot_items_cap", self.MAX_SNAPSHOT_ITEMS
        )
        try:
            cap_int = int(cap)
        except (TypeError, ValueError):
            return self.MAX_SNAPSHOT_ITEMS
        if cap_int in (None, 0):  # type: ignore[comparison-overlap]
            return None
        return cap_int
