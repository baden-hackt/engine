import sqlite3
from datetime import datetime


DB_PATH = "../shelf.db"


def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fill_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_id INTEGER NOT NULL,
            fill_level INTEGER NOT NULL,
            timestamp TEXT NOT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            tags_detected INTEGER NOT NULL,
            change_detected INTEGER NOT NULL
        );
        """
    )

    conn.commit()
    conn.close()


def write_fill_level(tag_id: int, fill_level: int) -> None:
    """Insert one row into fill_levels. Timestamp is datetime.now().isoformat()."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO fill_levels (tag_id, fill_level, timestamp) VALUES (?, ?, ?)",
        (tag_id, fill_level, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()


def write_scan_log(tags_detected: int, change_detected: bool) -> None:
    """Insert one row into scan_log. change_detected stored as 1 or 0."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO scan_log (timestamp, tags_detected, change_detected) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), tags_detected, 1 if change_detected else 0),
    )

    conn.commit()
    conn.close()


init_db()
