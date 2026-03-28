import time
import threading
from datetime import datetime
import uvicorn

from config import (
	load_products,
	SIMULATION_MODE,
	SIMULATION_INTERVAL_SECONDS,
	SIMULATION_LOW_FILL,
	SIMULATION_HIGH_FILL,
	SIMULATION_TAG_ID,
)
from orders import (
	init_orders_table,
	has_pending_order,
	create_order,
	mark_delivered,
	get_latest_fill_levels,
	insert_fill_level,
)
from csv_gen import generate_order_csv
from mailer import send_order_email
from api import app

CHECK_INTERVAL = 10  # seconds


def simulation_loop(products: dict) -> None:
	"""
	Generate synthetic fill-level data so reorder flow can be tested without camera input.
	Pattern alternates low/high for one tag to exercise: order -> delivered -> order.
	"""
	print(
		"Simulation mode enabled "
		f"(tag={SIMULATION_TAG_ID}, low={SIMULATION_LOW_FILL}, high={SIMULATION_HIGH_FILL}, "
		f"interval={SIMULATION_INTERVAL_SECONDS}s)."
	)

	if SIMULATION_TAG_ID not in products:
		print(f"Simulation disabled: tag {SIMULATION_TAG_ID} not found in configured products.")
		return

	cycle = 0
	while True:
		try:
			fill = SIMULATION_LOW_FILL if cycle % 2 == 0 else SIMULATION_HIGH_FILL
			insert_fill_level(SIMULATION_TAG_ID, fill)
			print(f"[SIM] inserted tag={SIMULATION_TAG_ID}, fill={fill}%")
			cycle += 1
			time.sleep(SIMULATION_INTERVAL_SECONDS)
		except Exception as e:
			print(f"ERROR in simulation loop: {e}")
			time.sleep(SIMULATION_INTERVAL_SECONDS)


def reorder_loop(products: dict) -> None:
	"""
	Main reorder check loop. Runs forever in a background thread.
	"""
	print("Reorder loop started.")

	while True:
		try:
			products = load_products()
			fill_levels = get_latest_fill_levels()

			if len(fill_levels) == 0:
				print(f"[{datetime.now().isoformat()}] No fill level data yet. Waiting...")
				time.sleep(CHECK_INTERVAL)
				continue

			for fl in fill_levels:
				tag_id = fl["tag_id"]
				fill_level = fl["fill_level"]

				product = products.get(tag_id)
				if product is None:
					continue

				threshold = product["reorder_threshold"]

				if fill_level > threshold:
					mark_delivered(tag_id)
					continue

				if has_pending_order(tag_id):
					print(
						f"  Tag {tag_id} ({product['product_name']}): "
						f"fill={fill_level}%, already ordered, skipping."
					)
					continue

				print(
					f"  Tag {tag_id} ({product['product_name']}): "
					f"fill={fill_level}% <= threshold={threshold}%, ordering!"
				)

				csv_filename = generate_order_csv(product)
				order_id = create_order(tag_id, product, csv_filename)
				email_sent = send_order_email(product, csv_filename)

				print(
					f"  Order #{order_id} created. CSV: {csv_filename}. "
					f"Email: {'sent' if email_sent else 'FAILED'}"
				)

			time.sleep(CHECK_INTERVAL)

		except Exception as e:
			print(f"ERROR in reorder loop: {e}")
			time.sleep(CHECK_INTERVAL)
			continue


def main():
	init_orders_table()
	products = load_products()

	print(f"Loaded {len(products)} products from .env")

	if SIMULATION_MODE:
		sim_thread = threading.Thread(target=simulation_loop, args=(products,), daemon=True)
		sim_thread.start()

	reorder_thread = threading.Thread(target=reorder_loop, args=(products,), daemon=True)
	reorder_thread.start()

	print("Starting API server on http://localhost:8000")
	print("API docs available at http://localhost:8000/docs")
	uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
	main()
