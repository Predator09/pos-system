import sqlite3
from pathlib import Path


class DatabaseConnection:
    def __init__(self):
        self.connection = None
        from app.services.shop_context import apply_stored_shop, database_path, ensure_legacy_migrated

        ensure_legacy_migrated()
        apply_stored_shop()
        self.db_path = database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def reconfigure(self, db_path: str | Path) -> None:
        """Close and point at another SQLite file (e.g. when switching shops)."""
        self.close()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        """Create SQLite connection."""
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        return self.connection

    def close(self):
        """Close connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self, query: str, params: tuple = ()):
        """Execute query."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        return cursor

    def fetchall(self, query: str, params: tuple = ()):
        """Fetch all results."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def fetchone(self, query: str, params: tuple = ()):
        """Fetch one result."""
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global connection instance (path follows active shop in ``shop_context``).
db = DatabaseConnection()
