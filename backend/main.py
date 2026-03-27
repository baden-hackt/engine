import time
import threading
from datetime import datetime
import uvicorn

from config import load_products
from orders import (
	init_orders_table,
	has_pending_order,
	create_order,
	mark_delivered,
	get_latest_fill_levels,
)
from csv_gen import generate_order_csv
from mailer import send_order_email
from api import app

CHECK_INTERVAL = 10  # seconds


def reorder_loop(products: dict) -> None:
	"""
	Main reorder check loop. Runs forever in a background thread.
	"""
	print("Reorder loop started.")

	while True:
		try:
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

	reorder_thread = threading.Thread(target=reorder_loop, args=(products,), daemon=True)
	reorder_thread.start()

	print("Starting API server on http://localhost:8000")
	print("API docs available at http://localhost:8000/docs")
	uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
	main()
