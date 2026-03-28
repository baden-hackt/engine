import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shelf.db"))


def init_orders_table() -> None:
	"""Create the orders table if it doesn't exist."""
	conn = sqlite3.connect(DB_PATH)
	conn.execute(
		"""
		CREATE TABLE IF NOT EXISTS orders (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tag_id INTEGER NOT NULL,
			product_id TEXT NOT NULL,
			product_name TEXT NOT NULL,
			supplier_name TEXT NOT NULL,
			supplier_email TEXT NOT NULL,
			quantity INTEGER NOT NULL,
			unit TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'pending',
			created_at TEXT NOT NULL,
			csv_filename TEXT
		)
		"""
	)
	conn.commit()
	conn.close()


def has_pending_order(tag_id: int) -> bool:
	"""
	Check if there is already a pending order for this tag_id.
	Return True if a row exists with status='pending' for this tag_id.
	"""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.execute(
		"SELECT COUNT(*) FROM orders WHERE tag_id = ? AND status = 'pending'",
		(tag_id,),
	)
	count = cursor.fetchone()[0]
	conn.close()
	return count > 0


def create_order(tag_id: int, product: dict, csv_filename: str) -> int:
	"""
	Insert a new order row with status='pending'.
	Return the order ID.
	"""
	conn = sqlite3.connect(DB_PATH)
	cursor = conn.execute(
		"""INSERT INTO orders (tag_id, product_id, product_name, supplier_name,
		   supplier_email, quantity, unit, status, created_at, csv_filename)
		   VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
		(
			tag_id,
			product["product_id"],
			product["product_name"],
			product["supplier_name"],
			product["supplier_email"],
			product["reorder_quantity"],
			product["unit"],
			datetime.now().isoformat(),
			csv_filename,
		),
	)
	conn.commit()
	order_id = cursor.lastrowid
	conn.close()
	return order_id


def mark_delivered(tag_id: int) -> None:
	"""
	Set status='delivered' for all pending orders for this tag_id.
	Called when fill level goes back above the reorder threshold.
	"""
	conn = sqlite3.connect(DB_PATH)
	conn.execute(
		"UPDATE orders SET status = 'delivered' WHERE tag_id = ? AND status = 'pending'",
		(tag_id,),
	)
	conn.commit()
	conn.close()


def get_all_orders() -> list[dict]:
	"""
	Return all orders as a list of dicts, ordered by created_at descending.
	Used by the API for the dashboard.
	"""
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	cursor = conn.execute("SELECT * FROM orders ORDER BY created_at DESC")
	rows = [dict(row) for row in cursor.fetchall()]
	conn.close()
	return rows


def get_latest_fill_levels() -> list[dict]:
	"""
	Read the latest fill level per tag_id from Person 1's fill_levels table.
	Return a list of dicts: [{"tag_id": 0, "fill_level": 25, "timestamp": "..."}, ...]
	"""
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	try:
		cursor = conn.execute(
			"""
			SELECT tag_id, fill_level, timestamp
			FROM fill_levels
			WHERE id IN (
				SELECT MAX(id) FROM fill_levels GROUP BY tag_id
			)
			"""
		)
		rows = [dict(row) for row in cursor.fetchall()]
		return rows
	except sqlite3.OperationalError as e:
		if "no such table: fill_levels" in str(e):
			return []
		raise
	finally:
		conn.close()


def ensure_fill_levels_table() -> None:
	"""Create fill_levels table if it does not exist."""
	conn = sqlite3.connect(DB_PATH)
	conn.execute(
		"""
		CREATE TABLE IF NOT EXISTS fill_levels (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			tag_id INTEGER NOT NULL,
			fill_level INTEGER NOT NULL,
			timestamp TEXT NOT NULL
		)
		"""
	)
	conn.commit()
	conn.close()


def insert_fill_level(tag_id: int, fill_level: int, timestamp: str | None = None) -> None:
	"""Insert one fill-level sample. Used by simulation mode and manual tests."""
	ensure_fill_levels_table()
	conn = sqlite3.connect(DB_PATH)
	conn.execute(
		"INSERT INTO fill_levels (tag_id, fill_level, timestamp) VALUES (?, ?, ?)",
		(tag_id, fill_level, timestamp or datetime.now().isoformat()),
	)
	conn.commit()
	conn.close()


init_orders_table()
