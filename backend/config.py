import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

ENV_PATH = "../.env"
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shelf.db"))
load_dotenv(ENV_PATH)

PRODUCT_ENV_SUFFIXES = {
	"TAG_ID",
	"ID",
	"NAME",
	"SUPPLIER_NAME",
	"SUPPLIER_EMAIL",
	"THRESHOLD",
	"REORDER_THRESHOLD",
	"REORDER_QTY",
	"REORDER_QUANTITY",
	"UNIT",
}

PRODUCT_ENV_INT_SUFFIXES = {
	"TAG_ID",
	"THRESHOLD",
	"REORDER_THRESHOLD",
	"REORDER_QTY",
	"REORDER_QUANTITY",
}

# API keys
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")


def _as_bool(value: str | None, default: bool = False) -> bool:
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
	try:
		return int(value) if value is not None else default
	except ValueError:
		return default


def _validate_tag_id(tag_id: int) -> None:
	if tag_id not in (0, 1):
		raise ValueError("tag_id must be 0 or 1")


def _env_product_defaults(tag_id: int) -> dict[str, str]:
	prefix = f"PRODUCT_{tag_id}_"
	threshold = os.getenv(f"{prefix}THRESHOLD", os.getenv(f"{prefix}REORDER_THRESHOLD", "20"))
	reorder_qty = os.getenv(f"{prefix}REORDER_QTY", os.getenv(f"{prefix}REORDER_QUANTITY", "100"))

	return {
		"TAG_ID": str(tag_id),
		"ID": os.getenv(f"{prefix}ID", f"MAT-00{tag_id + 1}"),
		"NAME": os.getenv(f"{prefix}NAME", f"Product {tag_id + 1}"),
		"SUPPLIER_NAME": os.getenv(f"{prefix}SUPPLIER_NAME", "Demo Supplier AG"),
		"SUPPLIER_EMAIL": os.getenv(f"{prefix}SUPPLIER_EMAIL", "demo@example.com"),
		"THRESHOLD": str(_as_int(threshold, 20)),
		"REORDER_THRESHOLD": str(_as_int(threshold, 20)),
		"REORDER_QTY": str(_as_int(reorder_qty, 100)),
		"REORDER_QUANTITY": str(_as_int(reorder_qty, 100)),
		"UNIT": os.getenv(f"{prefix}UNIT", "Stuck"),
	}


def init_products_table() -> None:
	"""Create products table and seed tag 0/1 from env defaults if missing."""
	conn = sqlite3.connect(DB_PATH)
	conn.execute(
		"""
		CREATE TABLE IF NOT EXISTS products (
			tag_id INTEGER PRIMARY KEY,
			product_id TEXT NOT NULL,
			product_name TEXT NOT NULL,
			supplier_name TEXT NOT NULL,
			supplier_email TEXT NOT NULL,
			reorder_threshold INTEGER NOT NULL,
			reorder_quantity INTEGER NOT NULL,
			unit TEXT NOT NULL,
			updated_at TEXT NOT NULL
		)
		"""
	)

	now = datetime.now().isoformat()
	for tag_id in (0, 1):
		defaults = _env_product_defaults(tag_id)
		conn.execute(
			"""
			INSERT OR IGNORE INTO products
			(tag_id, product_id, product_name, supplier_name, supplier_email,
			 reorder_threshold, reorder_quantity, unit, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				tag_id,
				defaults["ID"],
				defaults["NAME"],
				defaults["SUPPLIER_NAME"],
				defaults["SUPPLIER_EMAIL"],
				int(defaults["THRESHOLD"]),
				int(defaults["REORDER_QTY"]),
				defaults["UNIT"],
				now,
			),
		)

	conn.commit()
	conn.close()


# Simulation mode for deterministic end-to-end testing without camera input.
SIMULATION_MODE = _as_bool(os.getenv("SIMULATION_MODE"), False)
SIMULATION_INTERVAL_SECONDS = _as_int(os.getenv("SIMULATION_INTERVAL_SECONDS"), 10)
SIMULATION_LOW_FILL = _as_int(os.getenv("SIMULATION_LOW_FILL"), 5)
SIMULATION_HIGH_FILL = _as_int(os.getenv("SIMULATION_HIGH_FILL"), 95)
SIMULATION_TAG_ID = _as_int(os.getenv("SIMULATION_TAG_ID"), 0)


def load_products() -> dict:
	"""
	Load product configuration from SQLite products table.
	Returns a dict mapping tag_id (int) to product dict.
	Exactly 2 products: tag_id 0 and tag_id 1.
	"""
	init_products_table()
	conn = sqlite3.connect(DB_PATH)
	conn.row_factory = sqlite3.Row
	cursor = conn.execute("SELECT * FROM products ORDER BY tag_id")
	rows = cursor.fetchall()
	conn.close()

	products: dict[int, dict] = {}
	for row in rows:
		tag_id = int(row["tag_id"])
		products[tag_id] = {
			"tag_id": tag_id,
			"product_id": row["product_id"],
			"product_name": row["product_name"],
			"supplier_name": row["supplier_name"],
			"supplier_email": row["supplier_email"],
			"reorder_threshold": int(row["reorder_threshold"]),
			"reorder_quantity": int(row["reorder_quantity"]),
			"unit": row["unit"],
		}

	return products


def get_product_env(tag_id: int) -> dict[str, str]:
	"""Return product config as legacy suffix-key dict for dashboard compatibility."""
	_validate_tag_id(tag_id)
	products = load_products()
	product = products.get(tag_id)
	if product is None:
		return _env_product_defaults(tag_id)

	threshold = str(product["reorder_threshold"])
	reorder_qty = str(product["reorder_quantity"])
	return {
		"TAG_ID": str(tag_id),
		"ID": str(product["product_id"]),
		"NAME": str(product["product_name"]),
		"SUPPLIER_NAME": str(product["supplier_name"]),
		"SUPPLIER_EMAIL": str(product["supplier_email"]),
		"THRESHOLD": threshold,
		"REORDER_THRESHOLD": threshold,
		"REORDER_QTY": reorder_qty,
		"REORDER_QUANTITY": reorder_qty,
		"UNIT": str(product["unit"]),
	}


def get_all_product_env() -> dict[int, dict[str, str]]:
	return {0: get_product_env(0), 1: get_product_env(1)}


def update_product_env(tag_id: int, updates: dict[str, str | int]) -> dict[str, str]:
	"""
	Persist product updates to SQLite products table.
	Accepts suffix keys only, e.g. ID, NAME, THRESHOLD, REORDER_QTY.
	"""
	_validate_tag_id(tag_id)

	if len(updates) == 0:
		raise ValueError("updates must include at least one field")

	cleaned: dict[str, str] = {}
	for raw_suffix, raw_value in updates.items():
		suffix = raw_suffix.strip().upper()
		if suffix not in PRODUCT_ENV_SUFFIXES:
			raise ValueError(f"Unsupported product field: {raw_suffix}")

		if suffix == "TAG_ID":
			if str(raw_value).strip() != str(tag_id):
				raise ValueError("TAG_ID cannot be changed")
			cleaned[suffix] = str(tag_id)
			continue

		if suffix in PRODUCT_ENV_INT_SUFFIXES:
			try:
				cleaned[suffix] = str(int(raw_value))
			except (TypeError, ValueError):
				raise ValueError(f"Field {suffix} must be an integer") from None
		else:
			cleaned[suffix] = str(raw_value).strip()

	# Keep legacy/synonym keys in sync for dashboard + backend compatibility.
	if "THRESHOLD" in cleaned and "REORDER_THRESHOLD" not in cleaned:
		cleaned["REORDER_THRESHOLD"] = cleaned["THRESHOLD"]
	if "REORDER_THRESHOLD" in cleaned and "THRESHOLD" not in cleaned:
		cleaned["THRESHOLD"] = cleaned["REORDER_THRESHOLD"]
	if "REORDER_QTY" in cleaned and "REORDER_QUANTITY" not in cleaned:
		cleaned["REORDER_QUANTITY"] = cleaned["REORDER_QTY"]
	if "REORDER_QUANTITY" in cleaned and "REORDER_QTY" not in cleaned:
		cleaned["REORDER_QTY"] = cleaned["REORDER_QUANTITY"]

	init_products_table()
	products = load_products()
	product = products.get(tag_id)
	if product is None:
		raise ValueError(f"Product with tag_id {tag_id} not found")

	new_product_id = cleaned.get("ID", str(product["product_id"]))
	new_name = cleaned.get("NAME", str(product["product_name"]))
	new_supplier_name = cleaned.get("SUPPLIER_NAME", str(product["supplier_name"]))
	new_supplier_email = cleaned.get("SUPPLIER_EMAIL", str(product["supplier_email"]))
	new_threshold = int(cleaned.get("THRESHOLD", str(product["reorder_threshold"])))
	new_reorder_qty = int(cleaned.get("REORDER_QTY", str(product["reorder_quantity"])))
	new_unit = cleaned.get("UNIT", str(product["unit"]))

	conn = sqlite3.connect(DB_PATH)
	conn.execute(
		"""
		UPDATE products
		SET product_id = ?,
			product_name = ?,
			supplier_name = ?,
			supplier_email = ?,
			reorder_threshold = ?,
			reorder_quantity = ?,
			unit = ?,
			updated_at = ?
		WHERE tag_id = ?
		""",
		(
			new_product_id,
			new_name,
			new_supplier_name,
			new_supplier_email,
			new_threshold,
			new_reorder_qty,
			new_unit,
			datetime.now().isoformat(),
			tag_id,
		),
	)
	conn.commit()
	conn.close()

	return get_product_env(tag_id)
