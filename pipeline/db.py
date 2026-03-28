import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shelf.db"))
DEFAULT_CROP_WIDTH = 336
DEFAULT_CROP_HEIGHT = 448
DEFAULT_OFFSET_X = 0
DEFAULT_OFFSET_Y = 0


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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS crop_settings (
            tag_id INTEGER PRIMARY KEY,
            crop_width INTEGER NOT NULL,
            crop_height INTEGER NOT NULL,
            offset_x INTEGER NOT NULL,
            offset_y INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )

    timestamp = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT OR IGNORE INTO crop_settings (tag_id, crop_width, crop_height, offset_x, offset_y, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (0, DEFAULT_CROP_WIDTH, DEFAULT_CROP_HEIGHT, DEFAULT_OFFSET_X, DEFAULT_OFFSET_Y, timestamp),
    )
    cursor.execute(
        """
        INSERT OR IGNORE INTO crop_settings (tag_id, crop_width, crop_height, offset_x, offset_y, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (1, DEFAULT_CROP_WIDTH, DEFAULT_CROP_HEIGHT, DEFAULT_OFFSET_X, DEFAULT_OFFSET_Y, timestamp),
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


def get_crop_settings(tag_id: int) -> tuple[int, int, int, int]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT crop_width, crop_height, offset_x, offset_y FROM crop_settings WHERE tag_id = ?",
        (tag_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return DEFAULT_CROP_WIDTH, DEFAULT_CROP_HEIGHT, DEFAULT_OFFSET_X, DEFAULT_OFFSET_Y

    return row


def upsert_crop_settings(tag_id: int, crop_width: int, crop_height: int, offset_x: int, offset_y: int) -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO crop_settings (tag_id, crop_width, crop_height, offset_x, offset_y, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(tag_id) DO UPDATE SET
            crop_width = excluded.crop_width,
            crop_height = excluded.crop_height,
            offset_x = excluded.offset_x,
            offset_y = excluded.offset_y,
            updated_at = excluded.updated_at
        """,
        (tag_id, crop_width, crop_height, offset_x, offset_y, datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()


init_db()
