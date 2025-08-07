# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Database manager for SQLAlchemy operations."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

from ripstream.models.database import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_path: Path | str) -> None:
        """Initialize database manager.

        Args:
            database_path: Path to the SQLite database file
        """
        self.database_path = Path(database_path)
        self.engine: Engine | None = None
        self.session_factory: sessionmaker[Session] | None = None

    def initialize(self) -> None:
        """Initialize the database connection and create tables."""
        # Ensure parent directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with SQLite-specific settings
        database_url = f"sqlite:///{self.database_path}"
        self.engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            connect_args={"check_same_thread": False},  # Allow multi-threading
        )

        # Enable foreign key constraints for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create session factory
        self.session_factory = sessionmaker(bind=self.engine)

        # Create all tables
        self.create_tables()

        logger.info("Database initialized at %s", self.database_path)

    def create_tables(self) -> None:
        """Create all database tables."""
        if self.engine is None:
            msg = "Database engine not initialized"
            raise RuntimeError(msg)

        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

    def drop_tables(self) -> None:
        """Drop all database tables (use with caution)."""
        if self.engine is None:
            msg = "Database engine not initialized"
            raise RuntimeError(msg)

        Base.metadata.drop_all(self.engine)
        logger.warning("All database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.

        Yields
        ------
            SQLAlchemy session

        Example:
            with db_manager.get_session() as session:
                session.add(record)
                session.commit()
        """
        if self.session_factory is None:
            msg = "Database not initialized"
            raise RuntimeError(msg)

        session = self.session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session_sync(self) -> Session:
        """Get a database session (caller responsible for cleanup).

        Returns
        -------
            SQLAlchemy session

        Note:
            Caller must call session.close() when done
        """
        if self.session_factory is None:
            msg = "Database not initialized"
            raise RuntimeError(msg)

        return self.session_factory()

    def close(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.session_factory = None
            logger.info("Database connection closed")

    def vacuum(self) -> None:
        """Vacuum the database to reclaim space."""
        if self.engine is None:
            msg = "Database engine not initialized"
            raise RuntimeError(msg)

        with self.engine.connect() as conn:
            conn.execute(text("VACUUM"))
        logger.info("Database vacuumed")

    def get_database_size(self) -> int:
        """Get the size of the database file in bytes.

        Returns
        -------
            Database file size in bytes, or 0 if file doesn't exist
        """
        if self.database_path.exists():
            return self.database_path.stat().st_size
        return 0

    def backup_database(self, backup_path: Path | str) -> None:
        """Create a backup of the database.

        Args:
            backup_path: Path where to save the backup
        """
        import shutil

        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if self.database_path.exists():
            shutil.copy2(self.database_path, backup_path)
            logger.info("Database backed up to %s", backup_path)
        else:
            logger.warning("Database file does not exist, cannot create backup")


# Global database managers for different databases
_downloads_db: DatabaseManager | None = None


def get_downloads_db() -> DatabaseManager:
    """Get the downloads database manager (singleton).

    Returns
    -------
        DatabaseManager instance for downloads
    """
    global _downloads_db
    if _downloads_db is None:
        from ripstream.config.user import UserConfig

        config = UserConfig()
        _downloads_db = DatabaseManager(config.database.database_path)
        if config.database.downloads_enabled:
            _downloads_db.initialize()
    return _downloads_db


def initialize_databases() -> None:
    """Initialize all databases based on user configuration."""
    from ripstream.config.user import UserConfig

    config = UserConfig()

    if config.database.downloads_enabled:
        downloads_db = get_downloads_db()
        if downloads_db.engine is None:
            downloads_db.initialize()

    logger.info("All databases initialized")


def close_databases() -> None:
    """Close all database connections."""
    global _downloads_db

    if _downloads_db:
        _downloads_db.close()
        _downloads_db = None

    logger.info("All database connections closed")
