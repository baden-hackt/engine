import os
from dotenv import load_dotenv

load_dotenv("../.env")

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


# Simulation mode for deterministic end-to-end testing without camera input.
SIMULATION_MODE = _as_bool(os.getenv("SIMULATION_MODE"), False)
SIMULATION_INTERVAL_SECONDS = _as_int(os.getenv("SIMULATION_INTERVAL_SECONDS"), 10)
SIMULATION_LOW_FILL = _as_int(os.getenv("SIMULATION_LOW_FILL"), 5)
SIMULATION_HIGH_FILL = _as_int(os.getenv("SIMULATION_HIGH_FILL"), 95)
SIMULATION_TAG_ID = _as_int(os.getenv("SIMULATION_TAG_ID"), 0)


def load_products() -> dict:
	"""
	Load product configuration from environment variables.
	Returns a dict mapping tag_id (int) to product dict.
	Exactly 2 products: tag_id 0 and tag_id 1.
	"""
	products = {}

	for i in range(2):
		prefix = f"PRODUCT_{i}_"
		products[i] = {
			"tag_id": i,
			"product_id": os.getenv(f"{prefix}ID", f"MAT-00{i+1}"),
			"product_name": os.getenv(f"{prefix}NAME", f"Product {i+1}"),
			"supplier_name": os.getenv(f"{prefix}SUPPLIER_NAME", "Demo Supplier AG"),
			"supplier_email": os.getenv(f"{prefix}SUPPLIER_EMAIL", "demo@example.com"),
			"reorder_threshold": int(os.getenv(f"{prefix}THRESHOLD", "20")),
			"reorder_quantity": int(os.getenv(f"{prefix}REORDER_QTY", "100")),
			"unit": os.getenv(f"{prefix}UNIT", "Stuck"),
		}

	return products
